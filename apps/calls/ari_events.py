"""
Asterisk ARI Event Handler

Opens a WebSocket to the ARI /events endpoint and dispatches real-time
call events (StasisStart, ChannelStateChange, etc.) to Django handlers.

The handler runs in a dedicated thread started by `manage.py run_ari_handler`
(or by the `ari-handler` Docker service).  It reconnects automatically on
disconnect or error.
"""
import asyncio
import json
import logging
import threading
import time

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class _Channel:
    """Minimal channel proxy so handler methods can access channel.id."""

    def __init__(self, channel_id: str):
        self.id = channel_id


class ARIEventHandler:
    """Handles real-time events from Asterisk ARI via WebSocket."""

    def __init__(self):
        self.running = False
        self.thread = None
        self.reconnect_delay = 5  # seconds between reconnect attempts

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the event loop in a background daemon thread."""
        if self.running:
            logger.warning("ARI event handler already running")
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("ARI event handler started")

    def stop(self):
        """Signal the loop to stop and wait for the thread to exit."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("ARI event handler stopped")

    # ------------------------------------------------------------------
    # Connection loop
    # ------------------------------------------------------------------

    def _run(self):
        """Thread target — runs the asyncio event loop, reconnects on failure."""
        while self.running:
            try:
                asyncio.run(self._listen())
            except Exception as exc:
                logger.error(f"ARI WebSocket error: {exc}")
                if self.running:
                    logger.info(f"Reconnecting in {self.reconnect_delay}s…")
                    time.sleep(self.reconnect_delay)

    async def _listen(self):
        """
        Open the ARI WebSocket and consume events until disconnected.

        URL format:  ws://<host>:<port>/ari/events?app=<app>&api_key=<user>:<pass>
        """
        from websockets.asyncio.client import connect as ws_connect

        ari_url = getattr(settings, "ASTERISK_ARI_URL", "http://asterisk:8088")
        ari_user = getattr(settings, "ASTERISK_ARI_USER", "")
        ari_pass = getattr(settings, "ASTERISK_ARI_PASSWORD", "")

        ws_base = ari_url.replace("http://", "ws://").replace("https://", "wss://")
        # subscribeAll=true: receive ChannelCreated/ChannelDestroyed for ALL channels,
        # not just those that enter a Stasis() dialplan application.  This lets us
        # track inbound calls that arrive via the normal dialplan (Dial(PJSIP/100))
        # without needing Stasis(crm-app) in the extensions.conf.
        uri = f"{ws_base}/ari/events?app=crm-app&api_key={ari_user}:{ari_pass}&subscribeAll=true"

        logger.info(f"Connecting to ARI WebSocket at {ari_url}/ari/events …")

        async with ws_connect(uri, ping_interval=30, ping_timeout=10) as ws:
            logger.info("Connected to ARI — listening for events")
            async for raw_message in ws:
                if not self.running:
                    break
                try:
                    event = json.loads(raw_message)
                    # Run _dispatch in a thread so that synchronous Django ORM
                    # calls inside the handlers are allowed.  Calling sync ORM
                    # directly from an async coroutine raises
                    # "SynchronousOnlyOperation: You cannot call this from an
                    # async context".
                    await asyncio.to_thread(self._dispatch, event)
                except Exception as exc:
                    logger.error(f"Error processing ARI event: {exc}")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, event: dict):
        event_type = event.get("type", "")
        channel_data = event.get("channel", {})
        channel = _Channel(channel_data.get("id", ""))

        _handlers = {
            # ChannelCreated fires for ALL channels when subscribeAll=true.
            # We use it to create Call records for inbound trunk channels before
            # the agent answers — giving us the real asterisk_channel_id that
            # matches the MixMonitor recording filename.
            "ChannelCreated": self._on_channel_created,
            "StasisStart": self._on_stasis_start,
            "StasisEnd": self._on_stasis_end,
            "ChannelStateChange": self._on_state_change,
            "ChannelHangupRequest": self._on_hangup_request,
            "ChannelDestroyed": self._on_channel_destroyed,
            # Bridge events: used to detect when outbound destination answers
            "ChannelEnteredBridge": self._on_channel_entered_bridge,
        }

        handler = _handlers.get(event_type)
        if handler:
            try:
                handler(channel, event)
            except Exception as exc:
                logger.error(f"Error in ARI handler for {event_type}: {exc}")
        else:
            logger.debug(f"Unhandled ARI event type: {event_type}")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_channel_created(self, channel, event):
        """Create a Call record as soon as an inbound trunk channel appears.

        With subscribeAll=true this fires for every new channel.  We only act
        on channels whose dialplan context starts with 'from-trunk' — those are
        inbound calls arriving from the SIP trunk before the agent answers.

        This ensures the Call record uses the real Asterisk channel id (= the
        UNIQUEID used by MixMonitor when naming the recording file) rather than
        the fake 'inbound-{uuid}' fallback created by register_inbound_call.
        """
        from .models import Call

        channel_info = event.get("channel", {})
        dialplan = channel_info.get("dialplan", {})
        context = dialplan.get("context", "")
        caller = channel_info.get("caller", {})
        caller_id = caller.get("number", "")

        # Only track inbound trunk channels
        if not context.startswith("from-trunk"):
            return
        if not caller_id:
            return

        channel_id = channel.id
        try:
            Call.objects.get(asterisk_channel_id=channel_id)
            logger.debug(f"ChannelCreated: Call already exists for channel {channel_id}")
        except Call.DoesNotExist:
            Call.objects.create(
                asterisk_channel_id=channel_id,
                direction="inbound",
                from_number=caller_id,
                to_number="",
                status="ringing",
                started_at=timezone.now(),
            )
            logger.info(f"ChannelCreated: recorded inbound call {channel_id} from {caller_id}")

    def _on_stasis_start(self, channel, event):
        """Handle new call entering Stasis app."""
        from .models import Call, CallLog

        channel_id = channel.id
        channel_info = event.get("channel", {})
        caller = channel_info.get("caller", {})
        caller_id = caller.get("number", "")
        args = event.get("args", [])
        direction = "inbound"

        logger.info(f"StasisStart: channel={channel_id}, caller={caller_id}, args={args}")

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            call.status = "ringing"
            call.save()
        except Call.DoesNotExist:
            call = Call.objects.create(
                asterisk_channel_id=channel_id,
                direction=direction,
                from_number=caller_id,
                to_number="",
                status="ringing",
                started_at=timezone.now(),
            )

        CallLog.objects.create(
            call=call,
            event="stasis_start",
            data={"channel": channel_info, "args": args},
        )
        logger.info(f"New {direction} call: {channel_id} from {caller_id}")

    def _on_stasis_end(self, channel, event):
        """Handle call leaving Stasis."""
        from .models import Call, CallLog

        channel_id = channel.id
        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            if call.status not in ["ended", "failed"]:
                call.status = "ended"
                call.ended_at = timezone.now()
                if call.answered_at:
                    call.duration = int((call.ended_at - call.answered_at).total_seconds())
                call.save()
            CallLog.objects.create(call=call, event="stasis_end", data=event)
            logger.info(f"Call ended: {channel_id}, duration: {call.duration}s")
            # Recording is triggered by _on_channel_destroyed (fires after this,
            # giving MixMonitor more time to flush the WAV file to disk).
        except Call.DoesNotExist:
            logger.warning(f"StasisEnd for unknown channel: {channel_id}")

    def _on_state_change(self, channel, event):
        """Handle channel state changes."""
        from .models import Call, CallLog

        channel_id = channel.id
        channel_info = event.get("channel", {})
        state = channel_info.get("state", "")

        logger.debug(f"ChannelStateChange: {channel_id} → {state}")

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            if state == "Up":
                if call.direction == "outbound":
                    # For outbound calls the tracked channel is the agent's SIP phone.
                    # When it goes Up it means the agent answered — Asterisk now dials
                    # the destination.  Transition to "ringing" here; the call only
                    # becomes "answered" once ChannelEnteredBridge fires with both legs
                    # (or the polling bridge-check in get_call_status detects it).
                    if call.status == "initiated":
                        call.status = "ringing"
                        call.save()
                        logger.info(f"Outbound call ringing (agent answered, dialling dest): {channel_id}")
                elif call.status != "answered":
                    # Inbound call: agent picking up = call is connected.
                    call.status = "answered"
                    call.answered_at = timezone.now()
                    call.save()
                    logger.info(f"Call answered: {channel_id}")
            elif state == "Ringing" and call.status == "initiated":
                call.status = "ringing"
                call.save()
            CallLog.objects.create(
                call=call,
                event="state_change",
                data={"state": state, "channel": channel_info},
            )
        except Call.DoesNotExist:
            # This channel is not our agent's channel.  It could be the destination
            # channel created by Dial() when the agent's phone answered.
            if state == "Up":
                call = None

                # Primary: match via linkedid — destination channel's linkedid equals
                # the originating agent channel's id (Asterisk call-chain linkage).
                channel_linked = channel_info.get("linkedid", "")
                if channel_linked:
                    call = Call.objects.filter(
                        asterisk_channel_id=channel_linked,
                        direction="outbound",
                        status__in=("initiated", "ringing"),
                    ).first()

                # Fallback: if linkedid is absent or unmatched, check BRIDGEPEER on
                # all ringing outbound calls.  When Dial() bridges both legs Asterisk
                # sets BRIDGEPEER to the peer channel's name, which contains channel_id.
                if not call:
                    from .ari_client import ari_client
                    ringing = Call.objects.filter(
                        direction="outbound",
                        status__in=("initiated", "ringing"),
                    )
                    for candidate in ringing:
                        try:
                            peer_var = ari_client.get_channel_variable(
                                candidate.asterisk_channel_id, "BRIDGEPEER"
                            )
                            bridgepeer = peer_var.get("value", "")
                            # BRIDGEPEER contains the full channel name; channel_id is
                            # the uniqueid embedded in that name (e.g. PJSIP/foo-<id>).
                            if bridgepeer and (channel_id in bridgepeer or bridgepeer in channel_id):
                                call = candidate
                                logger.info(
                                    f"Outbound call {candidate.id} matched via BRIDGEPEER={bridgepeer}"
                                )
                                break
                        except Exception:
                            pass

                if call:
                    call.status = "answered"
                    call.answered_at = timezone.now()
                    call.save()
                    CallLog.objects.create(
                        call=call,
                        event="answered",
                        data={"reason": "dest_channel_up", "dest_channel_id": channel_id},
                    )
                    logger.info(
                        f"Outbound call {call.id} answered — dest channel {channel_id} Up"
                    )
                    return
            logger.debug(f"State change for untracked channel: {channel_id}")

    def _on_channel_entered_bridge(self, channel, event):
        """Detect when an outbound call's destination has answered.

        Asterisk fires ChannelEnteredBridge once per channel as each leg joins
        the bridge.  The event that carries both legs may fire for the DESTINATION
        channel (not the agent's channel we stored).  So we check ALL channels in
        the bridge against our tracked outbound calls rather than only the channel
        that triggered the event.
        """
        from .models import Call, CallLog

        bridge = event.get("bridge", {})
        bridge_channels = bridge.get("channels", [])

        # Need at least 2 legs before the call is truly answered
        if len(bridge_channels) < 2:
            return

        # Find an outbound call whose agent channel is one of the bridge channels
        call = Call.objects.filter(
            asterisk_channel_id__in=bridge_channels,
            direction="outbound",
            status__in=("initiated", "ringing"),
        ).first()

        if call:
            call.status = "answered"
            call.answered_at = timezone.now()
            call.save()
            CallLog.objects.create(
                call=call,
                event="answered",
                data={"bridge_id": bridge.get("id"), "channels": bridge_channels},
            )
            logger.info(
                f"Outbound call answered (bridge established): {call.asterisk_channel_id}, "
                f"bridge={bridge.get('id')}"
            )

    def _on_hangup_request(self, channel, event):
        """Handle hangup request."""
        from .models import Call, CallLog

        channel_id = channel.id
        cause = event.get("cause", {})

        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            cause_code = cause.get("code", 0)
            if cause_code == 17:
                call.status = "busy"
            elif cause_code == 19:
                call.status = "no_answer"
            elif cause_code in [21, 38]:
                call.status = "failed"
            else:
                call.status = "ended"
            call.ended_at = timezone.now()
            if call.answered_at:
                call.duration = int((call.ended_at - call.answered_at).total_seconds())
            call.save()
            CallLog.objects.create(call=call, event="hangup_request", data={"cause": cause})
            logger.info(f"Hangup request: {channel_id}, cause: {cause_code}")
        except Call.DoesNotExist:
            logger.debug(f"Hangup request for untracked channel: {channel_id}")

    def _on_channel_destroyed(self, channel, event):
        """Handle channel destruction."""
        from .models import Call, CallLog

        channel_id = channel.id
        try:
            call = Call.objects.get(asterisk_channel_id=channel_id)
            if call.status not in ["ended", "failed", "busy", "no_answer"]:
                call.status = "ended"
                call.ended_at = timezone.now()
                if call.answered_at:
                    call.duration = int((call.ended_at - call.answered_at).total_seconds())
                call.save()
            CallLog.objects.create(call=call, event="channel_destroyed", data=event)
            self._trigger_recording_processing(call)
        except Call.DoesNotExist:
            logger.debug(f"Channel destroyed for untracked channel: {channel_id}")

    def _trigger_recording_processing(self, call):
        """Queue async processing of the call recording.

        Only triggered for calls that were actually answered — MixMonitor uses
        the `b` option so no file is written for unanswered calls (busy, no_answer,
        failed).  Skipping those avoids 5 spurious retries per missed call.
        """
        if not call.answered_at:
            logger.debug(f"Skipping recording for unanswered call {call.id} (status={call.status})")
            return
        try:
            from .tasks import process_recording
            # 10-second countdown gives MixMonitor enough time to flush the WAV
            # to disk before the task reads it.  The task retries anyway on
            # "file not found", but starting later reduces unnecessary retries.
            process_recording.apply_async(args=[call.id], countdown=10)
            logger.info(f"Queued recording processing for call {call.id} (countdown=10)")
        except Exception as exc:
            logger.error(f"Failed to queue recording processing: {exc}")


# Global singleton — imported by run_ari_handler management command
ari_handler = ARIEventHandler()
