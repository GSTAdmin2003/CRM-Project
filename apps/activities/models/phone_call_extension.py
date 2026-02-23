from django.conf import settings
from django.db import models


class PhoneCallExtension(models.Model):
    """
    Activity type extension for Phone Call activities.

    One-to-one with an Activity whose activity_type.name == "Phone Call".
    Contains all call business data. The linked ari_call record (calls.Call)
    is kept purely for Asterisk channel tracking and gives access to
    CallRecording / CallTranscript via its reverse relations.
    """

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_CHOICES = [
        (DIRECTION_INBOUND, "Inbound"),
        (DIRECTION_OUTBOUND, "Outbound"),
    ]

    STATUS_INITIATED = "initiated"
    STATUS_RINGING = "ringing"
    STATUS_ANSWERED = "answered"
    STATUS_ENDED = "ended"
    STATUS_FAILED = "failed"
    STATUS_BUSY = "busy"
    STATUS_NO_ANSWER = "no_answer"
    STATUS_CHOICES = [
        (STATUS_INITIATED, "Initiated"),
        (STATUS_RINGING, "Ringing"),
        (STATUS_ANSWERED, "Answered"),
        (STATUS_ENDED, "Ended"),
        (STATUS_FAILED, "Failed"),
        (STATUS_BUSY, "Busy"),
        (STATUS_NO_ANSWER, "No Answer"),
    ]

    activity = models.OneToOneField(
        "Activity",
        on_delete=models.CASCADE,
        related_name="phone_call",
    )

    # ARI Call record — used only to access recording / transcript.
    # Business data is stored on this model, not on Call.
    ari_call = models.OneToOneField(
        "calls.Call",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extension",
    )

    # ── Call metadata ──────────────────────────────────────────────────────────
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, blank=True)
    call_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INITIATED)
    from_number = models.CharField(max_length=20, blank=True)
    to_number = models.CharField(max_length=20, blank=True)

    # Asterisk identifiers copied here for display and fast lookup
    asterisk_channel_id = models.CharField(max_length=128, blank=True, db_index=True)
    asterisk_uniqueid = models.CharField(max_length=64, blank=True)

    # ── CRM links ──────────────────────────────────────────────────────────────
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phone_call_activities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phone_call_activities",
    )

    # ── Timing ─────────────────────────────────────────────────────────────────
    duration = models.PositiveIntegerField(
        null=True, blank=True, help_text="Duration in seconds"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "activities"
        verbose_name = "Phone Call Extension"
        verbose_name_plural = "Phone Call Extensions"

    def __str__(self):
        return f"{self.get_direction_display()} call: {self.from_number} → {self.to_number}"

    @property
    def duration_formatted(self):
        """Return duration as MM:SS or HH:MM:SS."""
        if not self.duration:
            return "00:00"
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def recording(self):
        """Recording file associated with this call (via ARI call record)."""
        if self.ari_call_id:
            return getattr(self.ari_call, "recording", None)
        return None

    @property
    def transcript(self):
        """Transcription associated with this call (via ARI call record)."""
        if self.ari_call_id:
            return getattr(self.ari_call, "transcript", None)
        return None
