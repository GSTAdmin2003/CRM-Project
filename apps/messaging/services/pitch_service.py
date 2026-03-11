"""Template messaging and sales pitch delivery."""
import datetime
import logging
import os
import tempfile

from django.db import transaction
from django.utils.timezone import now

from apps.messaging.meta_client import send_template_message as _send_template_api
from apps.messaging.meta_client import upload_media
from apps.messaging.models import WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate

from .helpers import normalize_phone, notify_conversation

log = logging.getLogger("apps.messaging")


class PitchService:
    @staticmethod
    @transaction.atomic
    def send_template_message(
        *, conversation_id: int, template_id: int, variables: list, sent_by
    ) -> WhatsAppMessage:
        conv = WhatsAppConversation.objects.get(id=conversation_id)
        template = WhatsAppTemplate.objects.get(id=template_id)
        rendered_body = template.render_body(variables)
        send_locale = template.meta_locale or template.language
        result = _send_template_api(
            conv.phone_number, template.name, send_locale, variables
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
        transaction.on_commit(lambda: notify_conversation(conv_id))
        return msg

    @staticmethod
    @transaction.atomic
    def send_hi_for_lead(*, lead_id: int, language: str, sent_by) -> tuple:
        """Get-or-create a conversation for the lead's phone, then send the 'hello_how_are_you'
        template in the given language.

        Returns (WhatsAppConversation, WhatsAppMessage).
        Raises: core.exceptions.NotFoundError, core.exceptions.ValidationError
        """
        from core.exceptions import NotFoundError, ValidationError
        from apps.crm.models import Lead
        from .conversation_service import ConversationService

        try:
            lead = Lead.objects.select_related("contact").get(id=lead_id)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Lead {lead_id} not found.")

        contact = lead.contact
        phone = (contact.mobile or contact.phone) if contact else ""
        phone = phone or lead.phone
        if not phone:
            raise ValidationError(
                "This lead has no phone number. Add a phone number before sending a message."
            )

        template = (
            WhatsAppTemplate.objects.filter(
                name=f"hello_how_are_you_{language}",
                language=language,
                is_active=True,
                approval_status="approved",
            ).first()
            or WhatsAppTemplate.objects.filter(
                name="hello_how_are_you",
                language=language,
                is_active=True,
                approval_status="approved",
            ).first()
        )
        if not template:
            raise ValidationError(
                f"No approved 'hello_how_are_you' template for language '{language}'. "
                "Submit the template for Meta approval first."
            )

        conv = ConversationService.get_or_create_conversation_for_phone(phone=phone)
        if contact:
            ConversationService.link_to_contact(conversation_id=conv.id, contact_id=contact.id)
        ConversationService.link_to_lead(conversation_id=conv.id, lead_id=lead.id)

        message = PitchService.send_template_message(
            conversation_id=conv.id,
            template_id=template.id,
            variables=[],
            sent_by=sent_by,
        )

        try:
            from apps.activities.models import Activity, ActivityType
            wa_type, _ = ActivityType.objects.get_or_create(
                name="WhatsApp",
                defaults={"icon": "fab fa-whatsapp", "color": "#25D366"},
            )
            recipient_name = lead.contact_full_name or lead.title
            Activity.objects.create(
                lead=lead,
                activity_type=wa_type,
                title="WhatsApp greeting sent",
                description=f"Sent 'hello_how_are_you' template to {recipient_name} ({phone})",
                scheduled_date=datetime.date.today(),
                status="completed",
                completed_at=now(),
                created_by=sent_by,
                assigned_to=sent_by,
            )
        except Exception:
            pass

        return conv, message

    @staticmethod
    @transaction.atomic
    def send_sales_pitch(*, lead_id: int, sent_by) -> WhatsAppMessage:
        """Send the approved sales_pitch template with the team's pitch PDF to the lead's contact.

        Raises:
            core.exceptions.NotFoundError  — lead not found
            core.exceptions.ValidationError — any prerequisite missing
        """
        from core.exceptions import NotFoundError, ValidationError
        from apps.crm.models import Lead
        from apps.messaging.meta_client import send_template_message as _send_tpl
        from .conversation_service import ConversationService

        try:
            lead = Lead.objects.select_related(
                "contact__company", "sales_team"
            ).get(id=lead_id)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Lead {lead_id} not found.")

        contact = lead.contact
        recipient_name = lead.contact_full_name or lead.title

        contact_phone = (contact.mobile or contact.phone) if contact else ""
        phone = contact_phone or lead.phone
        if not phone:
            raise ValidationError(
                "This lead has no phone number. Add a phone number before sending a pitch."
            )

        if contact and contact.effective_language:
            lang = contact.effective_language
        else:
            conv_for_lang = (
                WhatsAppConversation.objects.filter(phone_number=normalize_phone(phone))
                .select_related("contact")
                .first()
            )
            lang = (
                conv_for_lang.contact.effective_language
                if conv_for_lang and conv_for_lang.contact
                else "en"
            )

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

        conv = ConversationService.get_or_create_conversation_for_phone(phone=phone)
        if contact:
            ConversationService.link_to_contact(conversation_id=conv.id, contact_id=contact.id)
        ConversationService.link_to_lead(conversation_id=conv.id, lead_id=lead.id)

        rendered_body = template.render_body([recipient_name])
        send_locale = template.meta_locale or template.language
        result = _send_tpl(
            normalize_phone(phone),
            template.name,
            send_locale,
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
        transaction.on_commit(lambda: notify_conversation(conv_id))

        try:
            from apps.activities.models import Activity, ActivityType
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
                completed_at=now(),
                created_by=sent_by,
                assigned_to=sent_by,
            )
        except Exception:
            pass

        return msg

    @staticmethod
    def upload_team_pitch_pdf(
        *, sales_team_id: int, file, filename: str, language: str = "en"
    ) -> None:
        """Upload PDF to Meta media and save the media_id on SalesTeam for the given language."""
        from core.exceptions import NotFoundError, ValidationError
        from apps.crm.models import SalesTeam

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
        if language == "ka":
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
    def upload_default_pitch_pdf(*, file, filename: str, language: str = "en") -> None:
        """Upload PDF to Meta media and save the media_id as the system-wide default pitch."""
        from core.exceptions import ValidationError
        from apps.messaging.models import WhatsAppConfig

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
        if language == "ka":
            config.default_pitch_media_id_ka = media_id
            config.default_pitch_filename_ka = filename
            config.save(update_fields=["default_pitch_media_id_ka", "default_pitch_filename_ka"])
        else:
            config.default_pitch_media_id = media_id
            config.default_pitch_filename = filename
            config.save(update_fields=["default_pitch_media_id", "default_pitch_filename"])
