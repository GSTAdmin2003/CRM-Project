"""Internal helpers shared across messaging services."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_conversation(conv_id: int) -> None:
    """Push a 'chat_update' event to all WebSocket clients watching this conversation."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{conv_id}',
            {'type': 'chat.update'},
        )
    except Exception:
        pass


def notify_kanban_card(lead_id: int, last_message_body: str) -> None:
    """Push a card_update event to all kanban board viewers."""
    try:
        from apps.messaging.models import WhatsAppConversation
        conv = WhatsAppConversation.objects.only("unread_count").get(lead_id=lead_id)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "kanban_board",
            {
                "type": "kanban.card.update",
                "data": {
                    "type": "card_update",
                    "lead_id": lead_id,
                    "unread_message_count": conv.unread_count,
                    "last_message_preview": last_message_body[:80],
                },
            },
        )
    except Exception:
        pass


def normalize_phone(phone: str) -> str:
    """Strip leading + so all numbers are stored as digits only (e.g. 995571535389)."""
    return phone.lstrip("+").strip()
