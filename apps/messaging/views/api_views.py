from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from core.exceptions import NotFoundError, ValidationError

from ..models import WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate
from ..serializers import (
    WhatsAppConversationSerializer,
    WhatsAppMessageSerializer,
    WhatsAppTemplateSerializer,
)
from ..services.whatsapp_service import WhatsAppService


class TemplateViewSet(ReadOnlyModelViewSet):
    """List approved WhatsApp templates available for sending."""

    serializer_class = WhatsAppTemplateSerializer

    def get_queryset(self):
        return WhatsAppTemplate.objects.filter(
            is_active=True, approval_status="approved"
        ).order_by("display_name")


class ConversationViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    list:   GET /messaging/api/conversations/         — ordered by -last_message_at
    retrieve: GET /messaging/api/conversations/{id}/  — marks conversation as read
    messages: GET  /messaging/api/conversations/{id}/messages/  — paginated
              POST /messaging/api/conversations/{id}/messages/  — send message
    """

    serializer_class = WhatsAppConversationSerializer

    def get_queryset(self):
        qs = WhatsAppConversation.objects.select_related("contact", "lead").order_by(
            "-last_message_at"
        )
        phone = self.request.query_params.get("phone")
        if phone:
            normalized = phone.lstrip("+").strip()
            qs = qs.filter(phone_number=normalized)
        lead_id = self.request.query_params.get("lead_id")
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Mark as read when opening conversation
        try:
            WhatsAppService.mark_conversation_read(conversation_id=instance.id)
            instance.refresh_from_db()
        except Exception:
            pass
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == "GET":
            # No pagination — chat UIs need all messages; conversations are bounded in size.
            msgs = conversation.messages.select_related("sent_by").order_by("timestamp")
            serializer = WhatsAppMessageSerializer(msgs, many=True)
            return Response(serializer.data)

        # POST — send a new message
        body = request.data.get("body", "").strip()
        if not body:
            return Response({"body": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            message = WhatsAppService.send_message(
                conversation_id=conversation.id,
                body=body,
                sent_by=request.user,
            )
        except (NotFoundError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = WhatsAppMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send_template")
    def send_template(self, request, pk=None):
        conversation = self.get_object()
        template_id = request.data.get("template_id")
        variables = request.data.get("variables", [])
        if not template_id:
            return Response(
                {"detail": "template_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            message = WhatsAppService.send_template_message(
                conversation_id=conversation.id,
                template_id=int(template_id),
                variables=variables,
                sent_by=request.user,
            )
        except (NotFoundError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = WhatsAppMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="for_lead")
    def for_lead(self, request):
        """Resolve conversation for a lead: FK lookup first, then phone fallback."""
        lead_id = request.query_params.get("lead_id")
        if not lead_id:
            return Response({"detail": "lead_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from apps.crm.models import Lead

            lead = Lead.objects.select_related("contact").get(id=int(lead_id))
        except (Lead.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)

        conv = WhatsAppConversation.objects.filter(lead_id=lead.id).first()
        if not conv:
            from apps.messaging.services.helpers import normalize_phone

            contact = lead.contact
            phone = (contact.mobile or contact.phone) if contact else ""
            phone = phone or lead.phone
            if phone:
                conv = WhatsAppConversation.objects.filter(
                    phone_number=normalize_phone(phone)
                ).first()

        if not conv:
            return Response({"detail": "No conversation found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(conv)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="send_hi_for_lead")
    def send_hi_for_lead(self, request):
        """Create/find a conversation for the lead's phone and send the greeting template."""
        from core.exceptions import NotFoundError, ValidationError

        lead_id = request.data.get("lead_id")
        language = (request.data.get("language") or "en").strip()
        if not lead_id:
            return Response({"detail": "lead_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            conv, message = WhatsAppService.send_hi_for_lead(
                lead_id=int(lead_id), language=language, sent_by=request.user
            )
        except (NotFoundError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "conversation_id": conv.id,
                "message": WhatsAppMessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="send_named_template")
    def send_named_template(self, request, pk=None):
        """Send a template by name, auto-resolving language from the conversation's contact."""
        conversation = self.get_object()
        template_name = request.data.get("template_name", "").strip()
        if not template_name:
            return Response(
                {"detail": "template_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sales pitch has its own service: handles contact-name variable + PDF attachment.
        if template_name == "sales_pitch":
            # Prefer lead_id from request body (caller knows which lead they're on),
            # fall back to the conversation's linked lead.
            lead_id = request.data.get("lead_id") or conversation.lead_id
            if not lead_id:
                return Response(
                    {"detail": "No lead linked to this conversation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                message = WhatsAppService.send_sales_pitch(
                    lead_id=int(lead_id),
                    sent_by=request.user,
                )
            except (NotFoundError, ValidationError) as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
            serializer = WhatsAppMessageSerializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Generic template: resolve language — body override > contact > default.
        language = request.data.get("language", "").strip()
        if not language:
            contact = conversation.contact
            language = contact.effective_language if contact else "en"

        # Try language-suffixed name first (e.g. hello_how_are_you_ka),
        # then the plain name (e.g. hello_how_are_you for en).
        template = WhatsAppTemplate.objects.filter(
            name=f"{template_name}_{language}",
            language=language,
            is_active=True,
            approval_status="approved",
        ).first() or WhatsAppTemplate.objects.filter(
            name=template_name,
            language=language,
            is_active=True,
            approval_status="approved",
        ).first()

        if not template:
            return Response(
                {
                    "detail": (
                        f"No approved '{template_name}' template for language '{language}'. "
                        "Submit the template for Meta approval first."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            message = WhatsAppService.send_template_message(
                conversation_id=conversation.id,
                template_id=template.id,
                variables=[],
                sent_by=request.user,
            )
        except (NotFoundError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = WhatsAppMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
