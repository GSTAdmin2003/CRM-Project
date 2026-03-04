from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models, transaction
from django.utils.timezone import now

from apps.messaging.meta_client import send_template_message as _send_template_api
from apps.messaging.meta_client import send_text_message
from apps.messaging.models import WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate


def _notify_conversation(conv_id: int) -> None:
    """Push a 'chat_update' event to all WebSocket clients watching this conversation."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{conv_id}',
            {'type': 'chat.update'},
        )
    except Exception:
        pass  # Never break the main flow if WebSocket notify fails


def _notify_kanban_card(lead_id: int, last_message_body: str) -> None:
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


def _normalize_phone(phone: str) -> str:
    """Strip leading + so all numbers are stored as digits only (e.g. 995571535389)."""
    return phone.lstrip("+").strip()


class WhatsAppService:
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
    @transaction.atomic
    def handle_webhook_payload(payload: dict) -> None:
        """Parse Meta webhook event and persist inbound messages + status updates."""
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # Inbound messages
                for msg in value.get("messages", []):
                    from_number = _normalize_phone(msg["from"])
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
                        transaction.on_commit(lambda: _notify_conversation(conv_id))
                        if conv.lead_id:
                            _msg_body = msg.get("text", {}).get("body", "")
                            transaction.on_commit(
                                lambda lid=conv.lead_id, body=_msg_body: _notify_kanban_card(lid, body)
                            )
                # Status updates (delivered/read)
                for status in value.get("statuses", []):
                    import logging as _logging
                    _log = _logging.getLogger('apps.messaging')
                    msg_status = status.get("status", "")
                    update_fields = {"status": msg_status}
                    if msg_status == "failed":
                        errors = status.get("errors", [])
                        _log.warning(
                            f"WhatsApp delivery failed for wamid={status.get('id')!r} "
                            f"recipient={status.get('recipient_id')!r} "
                            f"errors={errors}"
                        )
                        if errors:
                            first = errors[0]
                            update_fields["meta_error_code"] = first.get("code")
                            # Prefer 'title' (short), fall back to 'message'
                            update_fields["meta_error_message"] = (
                                first.get("title") or first.get("message") or ""
                            )
                    updated = WhatsAppMessage.objects.filter(
                        wa_message_id=status["id"]
                    ).update(**update_fields)
                    if updated:
                        # Notify so read/delivered ticks update in real time
                        msg_obj = WhatsAppMessage.objects.filter(
                            wa_message_id=status["id"]
                        ).select_related('conversation').first()
                        if msg_obj:
                            conv_id = msg_obj.conversation_id
                            transaction.on_commit(lambda: _notify_conversation(conv_id))

    @staticmethod
    @transaction.atomic
    def send_template_message(
        *, conversation_id: int, template_id: int, variables: list, sent_by
    ) -> WhatsAppMessage:
        conv = WhatsAppConversation.objects.get(id=conversation_id)
        template = WhatsAppTemplate.objects.get(id=template_id)
        rendered_body = template.render_body(variables)
        result = _send_template_api(
            conv.phone_number, template.name, template.language, variables
        )
        wa_id = result.get("messages", [{}])[0].get("id")
        msg = WhatsAppMessage.objects.create(
            conversation=conv,
            wa_message_id=wa_id,
            direction="outbound",
            body=rendered_body,
            status="sent",
            timestamp=now(),
            sent_by=sent_by,
        )
        conv.last_message_at = msg.timestamp
        conv.save(update_fields=["last_message_at", "updated_at"])
        conv_id = conv.id
        transaction.on_commit(lambda: _notify_conversation(conv_id))
        return msg

    @staticmethod
    def mark_conversation_read(*, conversation_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(unread_count=0)

    @staticmethod
    def get_or_create_conversation_for_phone(*, phone: str) -> WhatsAppConversation:
        conv, _ = WhatsAppConversation.objects.get_or_create(phone_number=_normalize_phone(phone))
        return conv

    @staticmethod
    def link_to_contact(*, conversation_id: int, contact_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(
            contact_id=contact_id
        )

    @staticmethod
    def link_to_lead(*, conversation_id: int, lead_id: int) -> None:
        WhatsAppConversation.objects.filter(id=conversation_id).update(lead_id=lead_id)

    @staticmethod
    @transaction.atomic
    def send_sales_pitch(*, lead_id: int, sent_by) -> WhatsAppMessage:
        """Send the approved sales_pitch template with the team's pitch PDF to the lead's contact.

        Raises:
            core.exceptions.NotFoundError  — lead not found
            core.exceptions.ValidationError — any prerequisite missing
        """
        import os
        from core.exceptions import NotFoundError, ValidationError
        from apps.crm.models import Lead
        from apps.messaging.meta_client import send_template_message as _send_tpl

        try:
            lead = Lead.objects.select_related(
                "contact__company", "sales_team"
            ).get(id=lead_id)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Lead {lead_id} not found.")

        contact = lead.contact

        # Representative name always comes from the lead's own fields (synced when a rep is picked).
        recipient_name = lead.contact_full_name or lead.title

        # Phone: prefer contact's mobile → contact's phone → lead's direct phone.
        contact_phone = (contact.mobile or contact.phone) if contact else ""
        phone = contact_phone or lead.phone
        if not phone:
            raise ValidationError(
                "This lead has no phone number. Add a phone number before sending a pitch."
            )

        # Language: resolve from contact or existing conversation, fall back to 'en'.
        if contact and contact.effective_language:
            lang = contact.effective_language
        else:
            conv_for_lang = WhatsAppConversation.objects.filter(
                phone_number=_normalize_phone(phone)
            ).select_related("contact").first()
            lang = (conv_for_lang.contact.effective_language
                    if conv_for_lang and conv_for_lang.contact else "en")

        try:
            template = WhatsAppTemplate.objects.get(
                name=f"sales_pitch_{lang}", language=lang, approval_status="approved"
            )
        except WhatsAppTemplate.DoesNotExist:
            raise ValidationError(
                f"No approved 'sales_pitch_{lang}' template for language '{lang}'. "
                "Submit the template for Meta approval first."
            )

        sales_team = lead.sales_team
        if not sales_team:
            raise ValidationError(
                "This lead has no sales team assigned. Assign a team before sending a pitch."
            )
        media_id, pdf_filename = sales_team.get_pitch_for_language(lang)
        if not media_id:
            # Fall back to system-wide default pitch
            from apps.messaging.models import WhatsAppConfig
            config = WhatsAppConfig.get_config()
            if config:
                media_id, pdf_filename = config.get_default_pitch_for_language(lang)
        if not media_id:
            raise ValidationError(
                f"The lead's sales team has no {lang.upper()} pitch PDF uploaded, "
                "and no default pitch PDF is set. "
                "Go to Settings → CRM → Sales Pitch to upload one."
            )

        conv = WhatsAppService.get_or_create_conversation_for_phone(phone=phone)
        if contact:
            WhatsAppService.link_to_contact(conversation_id=conv.id, contact_id=contact.id)
        WhatsAppService.link_to_lead(conversation_id=conv.id, lead_id=lead.id)

        rendered_body = template.render_body([recipient_name])
        result = _send_tpl(
            _normalize_phone(phone),
            template.name,
            lang,
            [recipient_name],
            document_media_id=media_id,
            document_filename=pdf_filename,
        )
        wa_id = result.get("messages", [{}])[0].get("id")
        msg = WhatsAppMessage.objects.create(
            conversation=conv,
            wa_message_id=wa_id,
            direction="outbound",
            body=rendered_body,
            status="sent",
            timestamp=now(),
            sent_by=sent_by,
        )
        conv.last_message_at = msg.timestamp
        conv.save(update_fields=["last_message_at", "updated_at"])
        conv_id = conv.id
        transaction.on_commit(lambda: _notify_conversation(conv_id))

        # Log a completed activity on the opportunity
        try:
            from apps.activities.models import Activity, ActivityType
            from django.utils.timezone import now as _now
            import datetime
            pitch_type, _ = ActivityType.objects.get_or_create(
                name="WhatsApp Pitch",
                defaults={"icon": "fab fa-whatsapp", "color": "#25D366"},
            )
            Activity.objects.create(
                lead=lead,
                activity_type=pitch_type,
                title="Sales pitch sent via WhatsApp",
                description=f"Pitch PDF sent to {recipient_name} ({phone})",
                scheduled_date=datetime.date.today(),
                status="completed",
                completed_at=_now(),
                created_by=sent_by,
                assigned_to=sent_by,
            )
        except Exception:
            pass  # Never fail the pitch send because of activity logging

        return msg

    @staticmethod
    def upload_team_pitch_pdf(*, sales_team_id: int, file, filename: str, language: str = 'en') -> None:
        """Upload PDF to Meta media and save the media_id on SalesTeam for the given language.

        Raises:
            core.exceptions.NotFoundError   — team not found
            core.exceptions.ValidationError — Meta upload failed
        """
        import tempfile
        import os
        from core.exceptions import NotFoundError, ValidationError
        from apps.crm.models import SalesTeam
        from apps.messaging.meta_client import upload_media

        try:
            team = SalesTeam.objects.get(id=sales_team_id)
        except SalesTeam.DoesNotExist:
            raise NotFoundError(f"SalesTeam {sales_team_id} not found.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            media_id = upload_media(tmp_path, "application/pdf", filename)
        except Exception as exc:
            raise ValidationError(f"Meta media upload failed: {exc}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        file.seek(0)
        if language == 'ka':
            team.pitch_pdf_ka = file
            team.pitch_pdf_media_id_ka = media_id
            team.pitch_pdf_filename_ka = filename
            team.save(update_fields=["pitch_pdf_ka", "pitch_pdf_media_id_ka", "pitch_pdf_filename_ka"])
        else:
            team.pitch_pdf = file
            team.pitch_pdf_media_id = media_id
            team.pitch_pdf_filename = filename
            team.save(update_fields=["pitch_pdf", "pitch_pdf_media_id", "pitch_pdf_filename"])

    @staticmethod
    def upload_default_pitch_pdf(*, file, filename: str, language: str = 'en') -> None:
        """Upload PDF to Meta media and save the media_id as the system-wide default pitch.

        Raises:
            core.exceptions.ValidationError — Meta upload failed
        """
        import tempfile
        import os
        from core.exceptions import ValidationError
        from apps.messaging.models import WhatsAppConfig
        from apps.messaging.meta_client import upload_media

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            media_id = upload_media(tmp_path, "application/pdf", filename)
        except Exception as exc:
            raise ValidationError(f"Meta media upload failed: {exc}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        config = WhatsAppConfig.get_or_create_config()
        if language == 'ka':
            config.default_pitch_media_id_ka = media_id
            config.default_pitch_filename_ka = filename
            config.save(update_fields=["default_pitch_media_id_ka", "default_pitch_filename_ka"])
        else:
            config.default_pitch_media_id = media_id
            config.default_pitch_filename = filename
            config.save(update_fields=["default_pitch_media_id", "default_pitch_filename"])
