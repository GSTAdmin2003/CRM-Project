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
        Originate an outbound call.

        Args:
            from_ext: The extension/caller ID to use (ignored, uses trunk ID)
            to_number: The destination phone number
            variables: Optional dict of channel variables

        Returns:
            The created channel data
        """
        # Get caller ID from user's SIP settings in the database
        from .models import SIPSettings
        trunk_caller_id = from_ext
        try:
            sip = SIPSettings.objects.filter(is_active=True).first()
            if sip:
                trunk_caller_id = sip.caller_id or sip.username
        except Exception:
            pass

        # Originate call directly to the SIP trunk endpoint
        params = {
            'endpoint': f'PJSIP/{to_number}@sip-trunk-endpoint',
            'callerId': trunk_caller_id,
            'app': self.app_name,  # Track in Stasis for status updates
            'timeout': 60,
        }

        channel = self._request('POST', '/channels', params=params)
        channel_id = channel.get('id', 'unknown')
        logger.info(f"Originated call to {to_number} from {trunk_caller_id}, channel: {channel_id}")

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

    def get_recordings_path(self):
        """Get path to Asterisk recordings directory"""
        return getattr(settings, 'ASTERISK_RECORDINGS_PATH', '/var/spool/asterisk/recording')


# Global singleton instance
ari_client = ARIClient()
