from django.conf import settings
from django.db import models


class WhatsAppConversation(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)  # E.164 format
    contact = models.ForeignKey(
        "contacts.Contact",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="whatsapp_conversations",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="whatsapp_conversations",
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "messaging"
        ordering = ["-last_message_at"]

    def __str__(self):
        if self.contact:
            return f"{self.contact.name} ({self.phone_number})"
        return self.phone_number

    @property
    def display_name(self):
        if self.contact:
            return self.contact.name
        if self.lead:
            return self.lead.full_name
        return self.phone_number

    @property
    def last_message_preview(self):
        msg = self.messages.order_by("-timestamp").first()
        if msg:
            return msg.body[:60] + ("…" if len(msg.body) > 60 else "")
        return ""


class WhatsAppMessage(models.Model):
    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    ]
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
        ("received", "Received"),
    ]

    conversation = models.ForeignKey(
        WhatsAppConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    wa_message_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )  # Meta's message ID
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    timestamp = models.DateTimeField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "messaging"
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.direction}] {self.body[:40]}"
