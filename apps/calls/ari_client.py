"""
Asterisk ARI (Asterisk REST Interface) Client

Provides call control functionality through direct HTTP requests to the Asterisk REST API.
"""
import logging
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

logger = logging.getLogger(__name__)


class ARIClient:
    """Client for interacting with Asterisk ARI via HTTP"""

    def __init__(self):
        self.base_url = getattr(settings, 'ASTERISK_ARI_URL', 'http://asterisk:8088')
        self.username = getattr(settings, 'ASTERISK_ARI_USER', '')
        self.password = getattr(settings, 'ASTERISK_ARI_PASSWORD', '')
        self.app_name = 'crm-app'
        self.auth = HTTPBasicAuth(self.username, self.password)

    def _request(self, method, endpoint, **kwargs):
        """Make an authenticated request to ARI"""
        url = f"{self.base_url}/ari{endpoint}"
        kwargs['auth'] = self.auth

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"ARI request failed: {method} {endpoint} - {e}")
            raise

    def get_info(self):
        """Get Asterisk system info"""
        return self._request('GET', '/asterisk/info')

    def make_call(self, from_ext, to_number, variables=None):
        """
        Originate a click-to-call via the dialplan.

        Flow:
        1. ARI calls the agent's extension (from_ext).
        2. When the agent picks up, the dialplan's [from-internal] context
           dials PJSIP/{to_number}@sip-trunk-endpoint.
        3. Asterisk's Dial() bridges both legs automatically.
        4. MixMonitor records the call.

        Args:
            from_ext: The agent's local extension (e.g. '100').
            to_number: The destination phone number.
            variables: Optional dict of channel variables.

        Returns:
            An object with channel attributes (id, name, state, …).
        """
        from .models import SIPSettings

        trunk_caller_id = from_ext
        try:
            sip = SIPSettings.objects.filter(is_active=True).first()
            if sip:
                trunk_caller_id = sip.caller_id or sip.username
        except Exception:
            pass

        # Originate to the agent's phone; on answer the dialplan
        # sends the call out via the SIP trunk to `to_number`.
        params = {
            'endpoint': f'PJSIP/{from_ext}',
            'extension': to_number,
            'context': 'from-internal',
            'priority': 1,
            'callerId': trunk_caller_id,
            'timeout': 60,
        }

        if variables:
            for key, value in variables.items():
                params[f'variables[{key}]'] = str(value)

        channel = self._request('POST', '/channels', params=params)
        channel_id = channel.get('id', 'unknown')
        logger.info(
            f"Click-to-call: agent={from_ext}, dest={to_number}, "
            f"callerId={trunk_caller_id}, channel={channel_id}"
        )

        # Return an object with the channel data as attributes
        class ChannelObj:
            pass
        obj = ChannelObj()
        for k, v in channel.items():
            setattr(obj, k, v)
        return obj

    def answer_call(self, channel_id):
        """
        Answer a ringing channel.

        Args:
            channel_id: The Asterisk channel ID
        """
        self._request('POST', f'/channels/{channel_id}/answer')
        logger.info(f"Answered channel {channel_id}")

    def hangup_call(self, channel_id):
        """
        Hangup a channel.

        Args:
            channel_id: The Asterisk channel ID
        """
        try:
            self._request('DELETE', f'/channels/{channel_id}')
            logger.info(f"Hung up channel {channel_id}")
        except Exception as e:
            logger.warning(f"Could not hangup channel {channel_id}: {e}")

    def get_channel(self, channel_id):
        """
        Get channel information.

        Args:
            channel_id: The Asterisk channel ID

        Returns:
            Channel information dict
        """
        return self._request('GET', f'/channels/{channel_id}')

    def list_channels(self):
        """
        List all active channels.

        Returns:
            List of channel dicts
        """
        return self._request('GET', '/channels')

    def start_recording(self, channel_id, filename):
        """
        Start recording a channel.

        Args:
            channel_id: The Asterisk channel ID
            filename: Name for the recording file (without extension)

        Returns:
            Recording information
        """
        params = {
            'name': filename,
            'format': 'wav',
            'beep': 'false',
            'ifExists': 'overwrite'
        }
        recording = self._request('POST', f'/channels/{channel_id}/record', params=params)
        logger.info(f"Started recording for channel {channel_id}: {filename}")
        return recording

    def stop_recording(self, recording_name):
        """
        Stop an active recording.

        Args:
            recording_name: The name of the recording to stop
        """
        try:
            self._request('POST', f'/recordings/live/{recording_name}/stop')
            logger.info(f"Stopped recording: {recording_name}")
        except Exception as e:
            logger.warning(f"Could not stop recording {recording_name}: {e}")

    def play_sound(self, channel_id, sound_name):
        """
        Play a sound file on a channel.

        Args:
            channel_id: The Asterisk channel ID
            sound_name: The name of the sound to play

        Returns:
            Playback information
        """
        params = {'media': f'sound:{sound_name}'}
        return self._request('POST', f'/channels/{channel_id}/play', params=params)

    def send_dtmf(self, channel_id, dtmf):
        """
        Send DTMF tones to a channel.

        Args:
            channel_id: The Asterisk channel ID
            dtmf: String of DTMF digits to send
        """
        params = {'dtmf': dtmf}
        self._request('POST', f'/channels/{channel_id}/dtmf', params=params)
        logger.info(f"Sent DTMF '{dtmf}' to channel {channel_id}")

    def create_bridge(self, bridge_type='mixing'):
        """
        Create a bridge for connecting channels.

        Args:
            bridge_type: Type of bridge (mixing, holding, dtmf_events, proxy_media)

        Returns:
            Bridge information
        """
        params = {'type': bridge_type}
        return self._request('POST', '/bridges', params=params)

    def add_channel_to_bridge(self, bridge_id, channel_id):
        """
        Add a channel to a bridge.

        Args:
            bridge_id: The bridge ID
            channel_id: The channel ID to add
        """
        params = {'channel': channel_id}
        self._request('POST', f'/bridges/{bridge_id}/addChannel', params=params)

    def list_bridges(self):
        """
        List all active bridges.

        Returns:
            List of bridge dicts, each with 'id', 'channels', 'bridge_type', etc.
        """
        return self._request('GET', '/bridges')

    def get_channel_variable(self, channel_id, variable_name):
        """
        Get a channel variable.

        Args:
            channel_id: The Asterisk channel ID
            variable_name: Name of the channel variable (e.g. 'BRIDGEPEER')

        Returns:
            Dict with 'value' key containing the variable's value.
        """
        return self._request(
            'GET', f'/channels/{channel_id}/variable',
            params={'variable': variable_name},
        )

    def get_recordings_path(self):
        """Get path to Asterisk recordings directory"""
        return getattr(settings, 'ASTERISK_RECORDINGS_PATH', '/var/spool/asterisk/recording')


# Global singleton instance
ari_client = ARIClient()
