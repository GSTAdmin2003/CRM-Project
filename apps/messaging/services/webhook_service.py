"""Handles incoming Meta webhook payloads."""
import logging

from django.db import models, transaction
from django.utils.timezone import now

from apps.messaging.models import WhatsAppConversation, WhatsAppMessage

from .helpers import normalize_phone, notify_conversation, notify_kanban_card

log = logging.getLogger("apps.messaging")


class WebhookService:
    @staticmethod
    @transaction.atomic
    def handle_webhook_payload(payload: dict) -> None:
        """Parse Meta webhook event and persist inbound messages + status updates."""
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # Inbound messages
                for msg in value.get("messages", []):
                    from_number = normalize_phone(msg["from"])
                    conv, _ = WhatsAppConversation.objects.get_or_create(
                        phone_number=from_number
                    )
                    if not WhatsAppMessage.objects.filter(
                        wa_message_id=msg["id"]
                    ).exists():
                        WhatsAppMessage.objects.create(
                            conversation=conv,
                            wa_message_id=msg["id"],
                            direction="inbound",
                            body=msg.get("text", {}).get("body", ""),
                            status="received",
                            timestamp=now(),
                        )
                        conv.unread_count = models.F("unread_count") + 1
                        conv.last_message_at = now()
                        conv.save(
                            update_fields=["unread_count", "last_message_at", "updated_at"]
                        )
                        conv_id = conv.id
                        transaction.on_commit(lambda: notify_conversation(conv_id))
                        if conv.lead_id:
                            _msg_body = msg.get("text", {}).get("body", "")
                            transaction.on_commit(
                                lambda lid=conv.lead_id, body=_msg_body: notify_kanban_card(lid, body)
                            )
                # Status updates (delivered/read/failed)
                for status in value.get("statuses", []):
                    msg_status = status.get("status", "")
                    update_fields = {"status": msg_status}
                    if msg_status == "failed":
                        errors = status.get("errors", [])
                        log.warning(
                            "WhatsApp delivery failed for wamid=%r recipient=%r errors=%s",
                            status.get("id"),
                            status.get("recipient_id"),
                            errors,
                        )
                        if errors:
                            first = errors[0]
                            update_fields["meta_error_code"] = first.get("code")
                            update_fields["meta_error_message"] = (
                                first.get("title") or first.get("message") or ""
                            )
                    updated = WhatsAppMessage.objects.filter(
                        wa_message_id=status["id"]
                    ).update(**update_fields)
                    if updated:
                        msg_obj = (
                            WhatsAppMessage.objects.filter(wa_message_id=status["id"])
                            .select_related("conversation")
                            .first()
                        )
                        if msg_obj:
                            conv_id = msg_obj.conversation_id
                            transaction.on_commit(lambda: notify_conversation(conv_id))
