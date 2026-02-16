"""
Tests for CallService business logic.

All ARI-dependent methods are tested with the mock_ari_client fixture,
which patches apps.calls.services.call_service.ari_client.
"""

from unittest.mock import MagicMock

import pytest

from django.utils import timezone

from apps.calls.models import Call, CallLog
from apps.calls.services import CallService
from core.exceptions import NotFoundError, ValidationError

from .conftest import (
    CallFactory,
    ContactFactory,
    LeadFactory,
    UserFactory,
)


# =============================================================================
# list_calls_for_user
# =============================================================================


@pytest.mark.django_db
class TestCallServiceListCallsForUser:
    def test_list_calls_returns_all(self):
        user = UserFactory()
        CallFactory()
        CallFactory()
        CallFactory()
        qs = CallService.list_calls_for_user(user=user)
        assert qs.count() == 3

    def test_list_calls_filter_by_direction_inbound(self):
        user = UserFactory()
        CallFactory(direction="inbound")
        CallFactory(direction="outbound")
        qs = CallService.list_calls_for_user(user=user, direction="inbound")
        assert qs.count() == 1
        assert qs.first().direction == "inbound"

    def test_list_calls_filter_by_direction_outbound(self):
        user = UserFactory()
        CallFactory(direction="inbound")
        CallFactory(direction="outbound")
        qs = CallService.list_calls_for_user(user=user, direction="outbound")
        assert qs.count() == 1
        assert qs.first().direction == "outbound"

    def test_list_calls_filter_by_status(self):
        user = UserFactory()
        CallFactory(status="answered")
        CallFactory(status="ended")
        CallFactory(status="ended")
        qs = CallService.list_calls_for_user(user=user, status="ended")
        assert qs.count() == 2

    def test_list_calls_filter_user_me(self):
        user = UserFactory()
        other_user = UserFactory()
        CallFactory(user=user)
        CallFactory(user=other_user)
        qs = CallService.list_calls_for_user(user=user, user_filter="me")
        assert qs.count() == 1
        assert qs.first().user == user

    def test_list_calls_search_by_from_number(self):
        user = UserFactory()
        CallFactory(from_number="+15551112222")
        CallFactory(from_number="+15553334444")
        qs = CallService.list_calls_for_user(user=user, search="111")
        assert qs.count() == 1

    def test_list_calls_search_by_to_number(self):
        user = UserFactory()
        CallFactory(to_number="+15551112222")
        CallFactory(to_number="+15553334444")
        qs = CallService.list_calls_for_user(user=user, search="333")
        assert qs.count() == 1

    def test_list_calls_search_by_contact_name(self):
        user = UserFactory()
        contact = ContactFactory(name="John Smith")
        CallFactory(contact=contact)
        CallFactory()
        qs = CallService.list_calls_for_user(user=user, search="John")
        assert qs.count() == 1

    def test_list_calls_search_by_opportunity_title(self):
        user = UserFactory()
        lead = LeadFactory(title="Big Deal Opportunity")
        CallFactory(opportunity=lead)
        CallFactory()
        qs = CallService.list_calls_for_user(user=user, search="Big Deal")
        assert qs.count() == 1

    def test_list_calls_empty_search_returns_all(self):
        user = UserFactory()
        CallFactory()
        CallFactory()
        qs = CallService.list_calls_for_user(user=user, search="")
        assert qs.count() == 2

    def test_list_calls_whitespace_search_returns_all(self):
        user = UserFactory()
        CallFactory()
        qs = CallService.list_calls_for_user(user=user, search="   ")
        assert qs.count() == 1

    def test_list_calls_invalid_direction_ignored(self):
        user = UserFactory()
        CallFactory(direction="inbound")
        CallFactory(direction="outbound")
        qs = CallService.list_calls_for_user(user=user, direction="invalid")
        assert qs.count() == 2


# =============================================================================
# get_call_or_raise
# =============================================================================


@pytest.mark.django_db
class TestCallServiceGetCallOrRaise:
    def test_get_call_success(self):
        call = CallFactory()
        result = CallService.get_call_or_raise(pk=call.pk)
        assert result.pk == call.pk

    def test_get_call_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            CallService.get_call_or_raise(pk=99999)


# =============================================================================
# get_active_calls
# =============================================================================


@pytest.mark.django_db
class TestCallServiceGetActiveCalls:
    def test_get_active_calls_returns_active_statuses(self):
        user = UserFactory()
        CallFactory(status="initiated", user=user)
        CallFactory(status="ringing", user=user)
        CallFactory(status="answered", user=user)
        CallFactory(status="ended", user=user)
        CallFactory(status="failed", user=user)

        result = CallService.get_active_calls(user=user)
        assert len(result) == 3

    def test_get_active_calls_returns_correct_fields(self):
        user = UserFactory(username="activeuser")
        contact = ContactFactory(name="Active Contact")
        call = CallFactory(
            status="answered",
            direction="outbound",
            from_number="100",
            to_number="+15551234567",
            user=user,
            contact=contact,
            started_at=timezone.now(),
        )

        result = CallService.get_active_calls(user=user)
        assert len(result) == 1
        active = result[0]
        assert active["id"] == call.pk
        assert active["direction"] == "outbound"
        assert active["status"] == "answered"
        assert active["from_number"] == "100"
        assert active["to_number"] == "+15551234567"
        assert active["user"] == "activeuser"
        assert active["contact_name"] == "Active Contact"
        assert active["started_at"] is not None

    def test_get_active_calls_empty(self):
        user = UserFactory()
        CallFactory(status="ended")
        result = CallService.get_active_calls(user=user)
        assert len(result) == 0

    def test_get_active_calls_no_contact(self):
        user = UserFactory()
        CallFactory(status="initiated", user=user, contact=None)
        result = CallService.get_active_calls(user=user)
        assert len(result) == 1
        assert result[0]["contact_name"] is None

    def test_get_active_calls_no_user(self):
        user = UserFactory()
        CallFactory(status="initiated", user=None)
        result = CallService.get_active_calls(user=user)
        assert len(result) == 1
        assert result[0]["user"] is None


# =============================================================================
# initiate_call
# =============================================================================


@pytest.mark.django_db
class TestCallServiceInitiateCall:
    def test_initiate_call_success(self, mock_ari_client):
        user = UserFactory()
        mock_channel = MagicMock()
        mock_channel.id = "channel-abc-123"
        mock_ari_client.make_call.return_value = mock_channel

        call = CallService.initiate_call(
            user=user,
            phone_number="+15551234567",
        )

        assert call.pk is not None
        assert call.direction == "outbound"
        assert call.status == "initiated"
        assert call.to_number == "+15551234567"
        assert call.user == user
        assert call.asterisk_channel_id == "channel-abc-123"
        assert call.started_at is not None

        mock_ari_client.make_call.assert_called_once()

    def test_initiate_call_creates_call_log(self, mock_ari_client):
        user = UserFactory()
        mock_channel = MagicMock()
        mock_channel.id = "channel-log-test"
        mock_ari_client.make_call.return_value = mock_channel

        call = CallService.initiate_call(
            user=user,
            phone_number="+15551234567",
        )

        logs = CallLog.objects.filter(call=call)
        assert logs.count() == 1
        log = logs.first()
        assert log.event == "initiated"
        assert log.data["channel_id"] == "channel-log-test"

    def test_initiate_call_with_contact(self, mock_ari_client):
        user = UserFactory()
        contact = ContactFactory()
        mock_channel = MagicMock()
        mock_channel.id = "channel-contact-test"
        mock_ari_client.make_call.return_value = mock_channel

        call = CallService.initiate_call(
            user=user,
            phone_number="+15551234567",
            contact_id=contact.pk,
        )

        assert call.contact_id == contact.pk

    def test_initiate_call_with_lead(self, mock_ari_client):
        user = UserFactory()
        lead = LeadFactory()
        mock_channel = MagicMock()
        mock_channel.id = "channel-lead-test"
        mock_ari_client.make_call.return_value = mock_channel

        call = CallService.initiate_call(
            user=user,
            phone_number="+15551234567",
            lead_id=lead.pk,
        )

        assert call.opportunity_id == lead.pk

    def test_initiate_call_empty_phone_raises_validation(self, mock_ari_client):
        user = UserFactory()
        with pytest.raises(ValidationError, match="Phone number is required"):
            CallService.initiate_call(user=user, phone_number="")

    def test_initiate_call_invalid_phone_raises_validation(self, mock_ari_client):
        user = UserFactory()
        with pytest.raises(ValidationError, match="Phone number is invalid"):
            CallService.initiate_call(user=user, phone_number="---")

    def test_initiate_call_cleans_phone_number(self, mock_ari_client):
        user = UserFactory()
        mock_channel = MagicMock()
        mock_channel.id = "channel-clean-test"
        mock_ari_client.make_call.return_value = mock_channel

        call = CallService.initiate_call(
            user=user,
            phone_number="+1 (555) 123-4567",
        )

        assert call.to_number == "+15551234567"

    def test_initiate_call_ari_failure_raises(self, mock_ari_client):
        user = UserFactory()
        mock_ari_client.make_call.side_effect = Exception("ARI connection refused")

        with pytest.raises(Exception, match="ARI connection refused"):
            CallService.initiate_call(user=user, phone_number="+15551234567")

        # No call record should have been created due to atomic rollback
        assert Call.objects.count() == 0


# =============================================================================
# hangup_call
# =============================================================================


@pytest.mark.django_db
class TestCallServiceHangupCall:
    def test_hangup_call_success(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(
            status="answered",
            user=user,
            answered_at=timezone.now(),
        )

        result = CallService.hangup_call(call_pk=call.pk, user=user)

        assert result.status == "ended"
        assert result.ended_at is not None
        assert result.duration is not None
        mock_ari_client.hangup_call.assert_called_once_with(call.asterisk_channel_id)

    def test_hangup_call_creates_log(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="answered", user=user)

        CallService.hangup_call(call_pk=call.pk, user=user)

        log = CallLog.objects.filter(call=call, event="hangup_requested").first()
        assert log is not None
        assert log.data["user_id"] == user.pk

    def test_hangup_call_not_answered_no_duration(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="initiated", user=user, answered_at=None)

        result = CallService.hangup_call(call_pk=call.pk, user=user)

        assert result.status == "ended"
        assert result.duration is None

    def test_hangup_call_not_found_raises(self, mock_ari_client):
        user = UserFactory()
        with pytest.raises(NotFoundError, match="not found"):
            CallService.hangup_call(call_pk=99999, user=user)

    def test_hangup_call_ari_failure_raises(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="answered", user=user)
        mock_ari_client.hangup_call.side_effect = Exception("ARI timeout")

        with pytest.raises(Exception, match="ARI timeout"):
            CallService.hangup_call(call_pk=call.pk, user=user)


# =============================================================================
# answer_call
# =============================================================================


@pytest.mark.django_db
class TestCallServiceAnswerCall:
    def test_answer_call_success(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="ringing")

        result = CallService.answer_call(call_pk=call.pk, user=user)

        assert result.status == "answered"
        assert result.answered_at is not None
        assert result.user == user
        mock_ari_client.answer_call.assert_called_once_with(call.asterisk_channel_id)

    def test_answer_call_creates_log(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="ringing")

        CallService.answer_call(call_pk=call.pk, user=user)

        log = CallLog.objects.filter(call=call, event="answered").first()
        assert log is not None
        assert log.data["user_id"] == user.pk

    def test_answer_call_not_ringing_raises_validation(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="initiated")

        with pytest.raises(ValidationError, match="Call is not ringing"):
            CallService.answer_call(call_pk=call.pk, user=user)

    def test_answer_call_ended_raises_validation(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="ended")

        with pytest.raises(ValidationError, match="Call is not ringing"):
            CallService.answer_call(call_pk=call.pk, user=user)

    def test_answer_call_not_found_raises(self, mock_ari_client):
        user = UserFactory()
        with pytest.raises(NotFoundError, match="not found"):
            CallService.answer_call(call_pk=99999, user=user)

    def test_answer_call_ari_failure_raises(self, mock_ari_client):
        user = UserFactory()
        call = CallFactory(status="ringing")
        mock_ari_client.answer_call.side_effect = Exception("ARI error")

        with pytest.raises(Exception, match="ARI error"):
            CallService.answer_call(call_pk=call.pk, user=user)


# =============================================================================
# get_call_status
# =============================================================================


@pytest.mark.django_db
class TestCallServiceGetCallStatus:
    def test_get_call_status_ended_call_returns_status(self, mock_ari_client):
        call = CallFactory(status="ended", duration=120)
        result = CallService.get_call_status(call_pk=call.pk)
        assert result["status"] == "ended"
        assert result["duration"] == 120

    def test_get_call_status_active_call_channel_up(self, mock_ari_client):
        call = CallFactory(status="initiated")
        mock_ari_client.get_channel.return_value = {"state": "Up"}

        result = CallService.get_call_status(call_pk=call.pk)

        assert result["status"] == "answered"
        assert result["answered_at"] is not None

    def test_get_call_status_active_call_channel_ringing(self, mock_ari_client):
        call = CallFactory(status="initiated")
        mock_ari_client.get_channel.return_value = {"state": "Ringing"}

        result = CallService.get_call_status(call_pk=call.pk)

        assert result["status"] == "ringing"

    def test_get_call_status_channel_not_found_marks_ended(self, mock_ari_client):
        call = CallFactory(status="answered", answered_at=timezone.now())
        mock_ari_client.get_channel.side_effect = Exception("Channel not found")

        result = CallService.get_call_status(call_pk=call.pk)

        assert result["status"] == "ended"
        assert result["ended_at"] is not None
        assert result["duration"] is not None

    def test_get_call_status_creates_log_on_state_change(self, mock_ari_client):
        call = CallFactory(status="initiated")
        mock_ari_client.get_channel.return_value = {"state": "Ringing"}

        CallService.get_call_status(call_pk=call.pk)

        log = CallLog.objects.filter(call=call, event="ringing").first()
        assert log is not None

    def test_get_call_status_creates_log_on_channel_not_found(self, mock_ari_client):
        call = CallFactory(status="answered", answered_at=timezone.now())
        mock_ari_client.get_channel.side_effect = Exception("Channel gone")

        CallService.get_call_status(call_pk=call.pk)

        log = CallLog.objects.filter(call=call, event="ended").first()
        assert log is not None
        assert log.data["reason"] == "channel_not_found"

    def test_get_call_status_not_found_raises(self, mock_ari_client):
        with pytest.raises(NotFoundError, match="not found"):
            CallService.get_call_status(call_pk=99999)

    def test_get_call_status_already_answered_no_double_log(self, mock_ari_client):
        call = CallFactory(status="answered", answered_at=timezone.now())
        mock_ari_client.get_channel.return_value = {"state": "Up"}

        result = CallService.get_call_status(call_pk=call.pk)

        assert result["status"] == "answered"
        # No new "answered" log should be created since status was already answered
        assert CallLog.objects.filter(call=call, event="answered").count() == 0

    def test_get_call_status_already_ended_no_re_mark(self, mock_ari_client):
        call = CallFactory(status="ended", ended_at=timezone.now())
        mock_ari_client.get_channel.side_effect = Exception("Channel not found")

        # Should not try to get channel since status is already ended
        result = CallService.get_call_status(call_pk=call.pk)
        assert result["status"] == "ended"
        # get_channel should not have been called since status is not active
        mock_ari_client.get_channel.assert_not_called()


# =============================================================================
# update_call_notes
# =============================================================================


@pytest.mark.django_db
class TestCallServiceUpdateCallNotes:
    def test_update_notes_success(self):
        user = UserFactory()
        call = CallFactory()

        result = CallService.update_call_notes(
            call_pk=call.pk, user=user, notes="Great conversation"
        )

        assert result.notes == "Great conversation"

    def test_update_notes_empty_string(self):
        user = UserFactory()
        call = CallFactory(notes="Previous notes")

        result = CallService.update_call_notes(
            call_pk=call.pk, user=user, notes=""
        )

        assert result.notes == ""

    def test_update_notes_not_found_raises(self):
        user = UserFactory()
        with pytest.raises(NotFoundError, match="not found"):
            CallService.update_call_notes(call_pk=99999, user=user, notes="test")


# =============================================================================
# link_call_to_contact
# =============================================================================


@pytest.mark.django_db
class TestCallServiceLinkCallToContact:
    def test_link_to_contact_success(self):
        call = CallFactory(contact=None)
        contact = ContactFactory()

        result = CallService.link_call_to_contact(
            call_pk=call.pk, contact_id=contact.pk
        )

        assert result.contact == contact

    def test_link_to_contact_call_not_found_raises(self):
        contact = ContactFactory()
        with pytest.raises(NotFoundError, match="Call with id"):
            CallService.link_call_to_contact(call_pk=99999, contact_id=contact.pk)

    def test_link_to_contact_contact_not_found_raises(self):
        call = CallFactory()
        with pytest.raises(NotFoundError, match="Contact with id"):
            CallService.link_call_to_contact(call_pk=call.pk, contact_id=99999)

    def test_link_to_contact_replaces_existing(self):
        contact1 = ContactFactory()
        contact2 = ContactFactory()
        call = CallFactory(contact=contact1)

        result = CallService.link_call_to_contact(
            call_pk=call.pk, contact_id=contact2.pk
        )

        assert result.contact == contact2


# =============================================================================
# link_call_to_opportunity
# =============================================================================


@pytest.mark.django_db
class TestCallServiceLinkCallToOpportunity:
    def test_link_to_opportunity_success(self):
        call = CallFactory(opportunity=None)
        lead = LeadFactory()

        result = CallService.link_call_to_opportunity(
            call_pk=call.pk, lead_id=lead.pk
        )

        assert result.opportunity == lead

    def test_link_to_opportunity_call_not_found_raises(self):
        lead = LeadFactory()
        with pytest.raises(NotFoundError, match="Call with id"):
            CallService.link_call_to_opportunity(call_pk=99999, lead_id=lead.pk)

    def test_link_to_opportunity_lead_not_found_raises(self):
        call = CallFactory()
        with pytest.raises(NotFoundError, match="Opportunity with id"):
            CallService.link_call_to_opportunity(call_pk=call.pk, lead_id=99999)

    def test_link_to_opportunity_replaces_existing(self):
        lead1 = LeadFactory()
        lead2 = LeadFactory()
        call = CallFactory(opportunity=lead1)

        result = CallService.link_call_to_opportunity(
            call_pk=call.pk, lead_id=lead2.pk
        )

        assert result.opportunity == lead2
