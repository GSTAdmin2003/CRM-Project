"""Conversation-level WhatsApp operations."""
import logging

from django.db import transaction
from django.utils.timezone import now

from apps.messaging.meta_client import send_text_message
from apps.messaging.models import WhatsAppConversation, WhatsAppMessage

from .helpers import normalize_phone, notify_conversation

log = logging.getLogger("apps.messaging")


class ConversationService:
    @staticmethod
    @transaction.atomic
    def send_message(*, conversation_id: int, body: str, sent_by) -> WhatsAppMessage:
        conv = WhatsAppConversation.objects.get(id=conversation_id)
        result = send_text_message(conv.phone_number, body)
        wa_id = result.get("messages", [{}])[0].get("id")
        msg = WhatsAppMessage.objects.create(
            conversation=conv,
            wa_message_id=wa_id,
            direction="outbound",
            body=body,
            status="sent",
            timestamp=now(),
            sent_by=sent_by,
        )
        conv.last_message_at = msg.timestamp
        conv.save(update_fields=["last_message_at", "updated_at"])
        return msg

    @staticmethod
    def mark_conversation_read(*, conversation_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(unread_count=0)

    @staticmethod
    def get_or_create_conversation_for_phone(*, phone: str) -> WhatsAppConversation:
        conv, _ = WhatsAppConversation.objects.get_or_create(
            phone_number=normalize_phone(phone)
        )
        return conv

    @staticmethod
    def link_to_contact(*, conversation_id: int, contact_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(
            contact_id=contact_id
        )

    @staticmethod
    def link_to_lead(*, conversation_id: int, lead_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(lead_id=lead_id)
