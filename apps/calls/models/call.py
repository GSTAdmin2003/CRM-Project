from django.conf import settings
from django.db import models


class Call(models.Model):
    """Model for tracking VoIP calls"""

    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    ]

    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("ringing", "Ringing"),
        ("answered", "Answered"),
        ("ended", "Ended"),
        ("failed", "Failed"),
        ("busy", "Busy"),
        ("no_answer", "No Answer"),
    ]

    asterisk_channel_id = models.CharField(max_length=128, unique=True, db_index=True)
    asterisk_uniqueid = models.CharField(max_length=64, blank=True)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")

    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20)

    # Link to CRM entities
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls",
    )
    opportunity = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="calls",
    )

    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds")
    started_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Call"
        verbose_name_plural = "Calls"

    def __str__(self):
        return f"{self.get_direction_display()} call: {self.from_number} -> {self.to_number}"

    @property
    def duration_formatted(self):
        """Return duration in HH:MM:SS format"""
        if not self.duration:
            return "00:00"
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class CallRecording(models.Model):
    """Model for call recordings"""

    call = models.OneToOneField(
        Call,
        on_delete=models.CASCADE,
        related_name="recording",
    )

    # Recording stored locally from Asterisk
    file = models.FileField(upload_to="call_recordings/%Y/%m/")
    duration = models.PositiveIntegerField(null=True, help_text="Duration in seconds")
    file_size = models.PositiveIntegerField(null=True, help_text="File size in bytes")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Call Recording"
        verbose_name_plural = "Call Recordings"

    def __str__(self):
        return f"Recording for {self.call}"

    @property
    def file_size_formatted(self):
        """Return file size in human-readable format"""
        if not self.file_size:
            return "0 B"
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class CallLog(models.Model):
    """Event log for calls - tracks all state changes and events"""

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    event = models.CharField(max_length=50)
    data = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Call Log"
        verbose_name_plural = "Call Logs"

    def __str__(self):
        return f"{self.call} - {self.event} at {self.timestamp}"
