"""
CallService -- all business logic for the calls app.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

import logging

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from core.exceptions import NotFoundError, ValidationError

from ..ari_client import ari_client
from ..models import Call, CallLog

logger = logging.getLogger(__name__)


class CallService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_calls_for_user(
        *,
        user,
        direction: str | None = None,
        status: str | None = None,
        user_filter: str | None = None,
        search: str = "",
    ) -> QuerySet[Call]:
        """
        Return a filtered queryset of calls scoped by user role.

        Args:
            user: The requesting user.
            direction: Filter by 'inbound' or 'outbound'.
            status: Filter by call status.
            user_filter: 'me' to show only the user's calls.
            search: Search string for phone numbers, contact name, opportunity title.
        """
        qs = Call.objects.select_related(
            "contact", "opportunity", "user", "recording"
        ).prefetch_related("contact__company")

        if direction in ("inbound", "outbound"):
            qs = qs.filter(direction=direction)

        if status:
            qs = qs.filter(status=status)

        if user_filter == "me":
            qs = qs.filter(user=user)

        search = search.strip()
        if search:
            qs = qs.filter(
                Q(from_number__icontains=search)
                | Q(to_number__icontains=search)
                | Q(contact__name__icontains=search)
                | Q(opportunity__title__icontains=search)
            )

        return qs

    @staticmethod
    def get_call_or_raise(*, pk: int) -> Call:
        """Fetch a call by PK or raise NotFoundError."""
        try:
            return Call.objects.select_related(
                "contact", "opportunity", "user", "recording"
            ).get(pk=pk)
        except Call.DoesNotExist:
            raise NotFoundError(f"Call with id {pk} not found")

    @staticmethod
    def get_active_calls(*, user) -> list[dict]:
        """
        Return a list of currently active calls for dashboard widgets.

        Args:
            user: The requesting user (currently unused, returns all active).
        """
        active = Call.objects.filter(
            status__in=["initiated", "ringing", "answered"]
        ).select_related("user", "contact")

        return [
            {
                "id": call.id,
                "direction": call.direction,
                "status": call.status,
                "from_number": call.from_number,
                "to_number": call.to_number,
                "user": call.user.username if call.user else None,
                "contact_name": call.contact.name if call.contact else None,
                "started_at": call.started_at.isoformat() if call.started_at else None,
            }
            for call in active
        ]

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def initiate_call(
        *,
        user,
        phone_number: str,
        contact_id: int | None = None,
        lead_id: int | None = None,
    ) -> Call:
        """
        Initiate an outbound call via Asterisk ARI.

        Args:
            user: The user initiating the call.
            phone_number: Destination phone number.
            contact_id: Optional contact to link.
            lead_id: Optional opportunity (lead) to link.

        Returns:
            The created Call instance.

        Raises:
            ValidationError: If phone_number is empty.
            ServiceError: If ARI call fails.
        """
        if not phone_number:
            raise ValidationError("Phone number is required")

        # Clean phone number -- remove spaces, dashes, etc.
        cleaned_number = "".join(c for c in phone_number if c.isdigit() or c == "+")

        if not cleaned_number:
            raise ValidationError("Phone number is invalid")

        # Get user's extension (default to 100 if not set)
        from_ext = getattr(user, "extension", None) or "100"

        try:
            channel = ari_client.make_call(
                from_ext=from_ext,
                to_number=cleaned_number,
                variables={"CRM_USER_ID": str(user.id)},
            )
        except Exception as e:
            logger.error(f"Failed to initiate call: {e}")
            raise

        call = Call.objects.create(
            asterisk_channel_id=channel.id,
            direction="outbound",
            from_number=from_ext,
            to_number=cleaned_number,
            status="initiated",
            user=user,
            started_at=timezone.now(),
            contact_id=contact_id if contact_id else None,
            opportunity_id=lead_id if lead_id else None,
        )

        CallLog.objects.create(
            call=call,
            event="initiated",
            data={
                "from_ext": from_ext,
                "to_number": cleaned_number,
                "channel_id": channel.id,
            },
        )

        return call

    @staticmethod
    @transaction.atomic
    def hangup_call(*, call_pk: int, user) -> Call:
        """
        Hang up an active call.

        Args:
            call_pk: Primary key of the call to hang up.
            user: The user requesting the hangup.

        Returns:
            The updated Call instance.

        Raises:
            NotFoundError: If call does not exist.
        """
        call = CallService.get_call_or_raise(pk=call_pk)

        try:
            ari_client.hangup_call(call.asterisk_channel_id)
        except Exception as e:
            logger.error(f"Failed to hangup call {call_pk}: {e}")
            raise

        call.status = "ended"
        call.ended_at = timezone.now()
        if call.answered_at:
            call.duration = int((call.ended_at - call.answered_at).total_seconds())
        call.save()

        CallLog.objects.create(
            call=call,
            event="hangup_requested",
            data={"user_id": user.id},
        )

        return call

    @staticmethod
    @transaction.atomic
    def answer_call(*, call_pk: int, user) -> Call:
        """
        Answer a ringing call.

        Args:
            call_pk: Primary key of the call to answer.
            user: The user answering the call.

        Returns:
            The updated Call instance.

        Raises:
            NotFoundError: If call does not exist.
            ValidationError: If call is not in 'ringing' status.
        """
        call = CallService.get_call_or_raise(pk=call_pk)

        if call.status != "ringing":
            raise ValidationError("Call is not ringing")

        try:
            ari_client.answer_call(call.asterisk_channel_id)
        except Exception as e:
            logger.error(f"Failed to answer call {call_pk}: {e}")
            raise

        call.status = "answered"
        call.answered_at = timezone.now()
        call.user = user
        call.save()

        CallLog.objects.create(
            call=call,
            event="answered",
            data={"user_id": user.id},
        )

        return call

    @staticmethod
    def get_call_status(*, call_pk: int) -> dict:
        """
        Get current call status, checking Asterisk for live status updates.

        Args:
            call_pk: Primary key of the call.

        Returns:
            Dict with status, duration, timestamps.

        Raises:
            NotFoundError: If call does not exist.
        """
        call = CallService.get_call_or_raise(pk=call_pk)

        # If call is still active, check Asterisk for current status
        if call.status in ("initiated", "ringing", "answered"):
            try:
                channel = ari_client.get_channel(call.asterisk_channel_id)
                channel_state = channel.get("state", "")

                if channel_state == "Up":
                    if call.status != "answered":
                        call.status = "answered"
                        call.answered_at = timezone.now()
                        call.save()
                        CallLog.objects.create(
                            call=call,
                            event="answered",
                            data={"channel_state": channel_state},
                        )
                elif channel_state == "Ringing":
                    if call.status != "ringing":
                        call.status = "ringing"
                        call.save()
                        CallLog.objects.create(
                            call=call,
                            event="ringing",
                            data={"channel_state": channel_state},
                        )

                # Calculate live duration if answered
                if call.answered_at and call.status == "answered":
                    call.duration = int((timezone.now() - call.answered_at).total_seconds())

            except Exception as e:
                # Channel not found -- call has ended
                logger.info(
                    f"Channel {call.asterisk_channel_id} not found, "
                    f"marking call as ended: {e}"
                )
                if call.status not in ("ended", "failed", "busy", "no_answer"):
                    call.status = "ended"
                    call.ended_at = timezone.now()
                    if call.answered_at:
                        call.duration = int(
                            (call.ended_at - call.answered_at).total_seconds()
                        )
                    call.save()
                    CallLog.objects.create(
                        call=call,
                        event="ended",
                        data={"reason": "channel_not_found"},
                    )

        return {
            "status": call.status,
            "duration": call.duration,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "answered_at": call.answered_at.isoformat() if call.answered_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        }

    @staticmethod
    def update_call_notes(*, call_pk: int, user, notes: str) -> Call:
        """
        Update notes on a call.

        Args:
            call_pk: Primary key of the call.
            user: The user updating notes (for audit).
            notes: New notes text.

        Returns:
            The updated Call instance.

        Raises:
            NotFoundError: If call does not exist.
        """
        call = CallService.get_call_or_raise(pk=call_pk)
        call.notes = notes
        call.save(update_fields=["notes", "updated_at"])
        return call

    @staticmethod
    def link_call_to_contact(*, call_pk: int, contact_id: int) -> Call:
        """
        Link a call to a contact.

        Args:
            call_pk: Primary key of the call.
            contact_id: Primary key of the contact.

        Returns:
            The updated Call instance.

        Raises:
            NotFoundError: If call or contact does not exist.
        """
        from apps.contacts.models import Contact

        call = CallService.get_call_or_raise(pk=call_pk)

        try:
            contact = Contact.objects.get(pk=contact_id)
        except Contact.DoesNotExist:
            raise NotFoundError(f"Contact with id {contact_id} not found")

        call.contact = contact
        call.save(update_fields=["contact", "updated_at"])
        return call

    @staticmethod
    def link_call_to_opportunity(*, call_pk: int, lead_id: int) -> Call:
        """
        Link a call to an opportunity (lead).

        Args:
            call_pk: Primary key of the call.
            lead_id: Primary key of the lead/opportunity.

        Returns:
            The updated Call instance.

        Raises:
            NotFoundError: If call or lead does not exist.
        """
        from apps.crm.models import Lead

        call = CallService.get_call_or_raise(pk=call_pk)

        try:
            lead = Lead.objects.get(pk=lead_id)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Opportunity with id {lead_id} not found")

        call.opportunity = lead
        call.save(update_fields=["opportunity", "updated_at"])
        return call
