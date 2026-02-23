"""
Asterisk ARI Event Handler

Listens to real-time events from Asterisk and updates call records accordingly.
"""
import threading
import time
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class ARIEventHandler:
    """Handles real-time events from Asterisk ARI"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.reconnect_delay = 5  # seconds

    def start(self):
        """Start listening to ARI events in background thread"""
        if self.running:
            logger.warning("ARI event handler already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("ARI event handler started")

    def stop(self):
        """Stop the event handler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("ARI event handler stopped")

    def _run(self):
        """Main event loop"""
        from .ari_client import ari_client

        while self.running:
            try:
                client = ari_client.connect()

                # Register event handlers
                client.on_channel_event('StasisStart', self._on_stasis_start)
                client.on_channel_event('StasisEnd', self._on_stasis_end)
                client.on_channel_event('ChannelStateChange', self._on_state_change)
                client.on_channel_event('ChannelHangupRequest', self._on_hangup_request)
                client.on_channel_event('ChannelDestroyed', self._on_channel_destroyed)

                logger.info("Connected to ARI, listening for events...")
                client.run(apps='crm-app')

            except Exception as e:
                logger.error(f"ARI connection error: {e}")
                if self.running:
                    logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)

    def _on_stasis_start(self, channel, event):
        """Handle new call entering Stasis app"""
        from .models import Call, CallLog

        channel_id = channel.id
        channel_info = event.get('channel', {})
        caller = channel_info.get('caller', {})
        caller_id = caller.get('number', '')
        caller_name = caller.get('name', '')

        # Determine call direction
        args = event.get('args', [])
        direction = 'inbound'

        logger.info(f"StasisStart: channel={channel_id}, caller={caller_id}, args={args}")

        # Check if call already exists (for outbound calls we create before)
        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            # Update existing call
            call.status = 'ringing'
            call.save()
        except Call.DoesNotExist:
            # Create new call record for inbound calls
            call = Call.objects.create(
                asterisk_channel_id=channel_id,
                direction=direction,
                from_number=caller_id,
                to_number='',  # Will be set based on DID routing
                status='ringing',
                started_at=timezone.now()
            )

        CallLog.objects.create(
            call=call,
            event='stasis_start',
            data={
                'channel': channel_info,
                'args': args,
            }
        )

        logger.info(f"New {direction} call: {channel_id} from {caller_id}")

    def _on_stasis_end(self, channel, event):
        """Handle call leaving Stasis"""
        from .models import Call, CallLog

        channel_id = channel.id

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)

            # Only update if not already ended
            if call.status not in ['ended', 'failed']:
                call.status = 'ended'
                call.ended_at = timezone.now()

                if call.answered_at:
                    call.duration = int((call.ended_at - call.answered_at).total_seconds())

                call.save()

                # Sync to PhoneCallExtension
                try:
                    ext = call.extension
                    ext.call_status = call.status
                    ext.ended_at = call.ended_at
                    ext.duration = call.duration
                    ext.save(update_fields=["call_status", "ended_at", "duration", "updated_at"])
                except Exception:
                    pass

            CallLog.objects.create(
                call=call,
                event='stasis_end',
                data=event
            )

            logger.info(f"Call ended: {channel_id}, duration: {call.duration}s")

            # Trigger recording processing
            self._trigger_recording_processing(call)

        except Call.DoesNotExist:
            logger.warning(f"StasisEnd for unknown channel: {channel_id}")

    def _on_state_change(self, channel, event):
        """Handle channel state changes"""
        from .models import Call, CallLog

        channel_id = channel.id
        channel_info = event.get('channel', {})
        state = channel_info.get('state', '')

        logger.debug(f"ChannelStateChange: {channel_id} -> {state}")

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)

            if state == 'Up' and call.status != 'answered':
                call.status = 'answered'
                call.answered_at = timezone.now()
                call.save()
                logger.info(f"Call answered: {channel_id}")

                try:
                    ext = call.extension
                    ext.call_status = 'answered'
                    ext.answered_at = call.answered_at
                    ext.save(update_fields=["call_status", "answered_at", "updated_at"])
                except Exception:
                    pass

            elif state == 'Ringing' and call.status == 'initiated':
                call.status = 'ringing'
                call.save()

                try:
                    ext = call.extension
                    ext.call_status = 'ringing'
                    ext.save(update_fields=["call_status", "updated_at"])
                except Exception:
                    pass

            CallLog.objects.create(
                call=call,
                event='state_change',
                data={'state': state, 'channel': channel_info}
            )

        except Call.DoesNotExist:
            logger.debug(f"State change for untracked channel: {channel_id}")

    def _on_hangup_request(self, channel, event):
        """Handle hangup request"""
        from .models import Call, CallLog

        channel_id = channel.id
        cause = event.get('cause', {})

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)

            # Map hangup cause to status
            cause_code = cause.get('code', 0)
            if cause_code == 17:  # User busy
                call.status = 'busy'
            elif cause_code == 19:  # No answer
                call.status = 'no_answer'
            elif cause_code in [21, 38]:  # Call rejected / Network out of order
                call.status = 'failed'
            else:
                call.status = 'ended'

            call.ended_at = timezone.now()
            if call.answered_at:
                call.duration = int((call.ended_at - call.answered_at).total_seconds())
            call.save()

            # Sync to PhoneCallExtension
            try:
                ext = call.extension
                ext.call_status = call.status
                ext.ended_at = call.ended_at
                ext.duration = call.duration
                ext.save(update_fields=["call_status", "ended_at", "duration", "updated_at"])
            except Exception:
                pass

            CallLog.objects.create(
                call=call,
                event='hangup_request',
                data={'cause': cause}
            )

            logger.info(f"Hangup request: {channel_id}, cause: {cause_code}")

        except Call.DoesNotExist:
            logger.debug(f"Hangup request for untracked channel: {channel_id}")

    def _on_channel_destroyed(self, channel, event):
        """Handle channel destruction"""
        from .models import Call, CallLog

        channel_id = channel.id

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)

            if call.status not in ['ended', 'failed', 'busy', 'no_answer']:
                call.status = 'ended'
                call.ended_at = timezone.now()
                if call.answered_at:
                    call.duration = int((call.ended_at - call.answered_at).total_seconds())
                call.save()

                # Sync to PhoneCallExtension
                try:
                    ext = call.extension
                    ext.call_status = call.status
                    ext.ended_at = call.ended_at
                    ext.duration = call.duration
                    ext.save(update_fields=["call_status", "ended_at", "duration", "updated_at"])
                except Exception:
                    pass

            CallLog.objects.create(
                call=call,
                event='channel_destroyed',
                data=event
            )

            # Trigger recording processing
            self._trigger_recording_processing(call)

        except Call.DoesNotExist:
            logger.debug(f"Channel destroyed for untracked channel: {channel_id}")

    def _trigger_recording_processing(self, call):
        """Trigger async processing of call recording"""
        try:
            from .tasks import process_recording
            process_recording.delay(call.id)
            logger.info(f"Triggered recording processing for call {call.id}")
        except Exception as e:
            logger.error(f"Failed to trigger recording processing: {e}")


# Global singleton instance
ari_handler = ARIEventHandler()
