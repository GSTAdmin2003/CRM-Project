"""Facade that assembles all WhatsApp sub-services into a single WhatsAppService class.

Callers import `from apps.messaging.services import WhatsAppService` as before.
"""
from .conversation_service import ConversationService
from .pitch_service import PitchService
from .webhook_service import WebhookService


class WhatsAppService(ConversationService, PitchService, WebhookService):
    """Unified service — combines ConversationService, PitchService, WebhookService."""
