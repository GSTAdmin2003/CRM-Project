"""
Tests for Calls DRF API endpoints (CallViewSet).

Note: We use api_client.force_login() instead of force_authenticate() because
the RoleBasedAccessMiddleware checks request.user.is_authenticated at the Django
middleware layer, before DRF's authentication runs.

All ARI-dependent endpoints are tested with the mock_ari_client fixture.
"""

from unittest.mock import MagicMock, patch

import pytest

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.calls.models import Call, CallLog

from .conftest import (
    CallFactory,
    ContactFactory,
    LeadFactory,
    UserFactory,
)


# =============================================================================
# List Calls API
# =============================================================================


@pytest.mark.django_db
class TestCallListAPI:
    def test_list_requires_auth(self, api_client):
        url = reverse("calls:call-api-list")
        response = api_client.get(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_returns_calls(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(from_number="100", to_number="+15551111111")
        CallFactory(from_number="100", to_number="+15552222222")

        url = reverse("calls:call-api-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 2

    def test_list_filter_by_direction(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(direction="inbound")
        CallFactory(direction="outbound")

        url = reverse("calls:call-api-list")
        response = api_client.get(url, {"direction": "inbound"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["direction"] == "inbound"

    def test_list_filter_by_status(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(status="ended")
        CallFactory(status="answered")
        CallFactory(status="ended")

        url = reverse("calls:call-api-list")
        response = api_client.get(url, {"status": "ended"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 2

    def test_list_filter_by_user_me(self, api_client):
        user = UserFactory()
        other_user = UserFactory()
        api_client.force_login(user)
        CallFactory(user=user)
        CallFactory(user=other_user)

        url = reverse("calls:call-api-list")
        response = api_client.get(url, {"user": "me"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1

    def test_list_search_by_phone_number(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(to_number="+15559998888")
        CallFactory(to_number="+15551112222")

        url = reverse("calls:call-api-list")
        response = api_client.get(url, {"search": "999"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1


# =============================================================================
# Retrieve Call API
# =============================================================================


@pytest.mark.django_db
class TestCallRetrieveAPI:
    def test_retrieve_call_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(
            direction="outbound",
            from_number="100",
            to_number="+15551234567",
        )

        url = reverse("calls:call-api-detail", kwargs={"pk": call.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == call.pk
        assert response.data["direction"] == "outbound"
        assert response.data["to_number"] == "+15551234567"

    def test_retrieve_call_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-detail", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_requires_auth(self, api_client):
        call = CallFactory()
        url = reverse("calls:call-api-detail", kwargs={"pk": call.pk})
        response = api_client.get(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Initiate Call API
# =============================================================================


@pytest.mark.django_db
class TestCallInitiateAPI:
    def test_initiate_call_success(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)

        mock_channel = MagicMock()
        mock_channel.id = "api-channel-123"
        mock_ari_client.make_call.return_value = mock_channel

        url = reverse("calls:call-api-initiate")
        data = {"phone_number": "+15551234567"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["direction"] == "outbound"
        assert response.data["status"] == "initiated"
        assert response.data["asterisk_channel_id"] == "api-channel-123"

    def test_initiate_call_with_contact_and_lead(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        contact = ContactFactory()
        lead = LeadFactory()

        mock_channel = MagicMock()
        mock_channel.id = "api-channel-456"
        mock_ari_client.make_call.return_value = mock_channel

        url = reverse("calls:call-api-initiate")
        data = {
            "phone_number": "+15551234567",
            "contact_id": contact.pk,
            "lead_id": lead.pk,
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["contact_id"] == contact.pk
        assert response.data["opportunity_id"] == lead.pk

    def test_initiate_call_missing_phone_returns_400(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-initiate")
        data = {}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_initiate_call_requires_auth(self, api_client, mock_ari_client):
        url = reverse("calls:call-api-initiate")
        data = {"phone_number": "+15551234567"}
        response = api_client.post(url, data, format="json")
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_initiate_call_ari_failure_returns_500(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        mock_ari_client.make_call.side_effect = Exception("ARI down")

        url = reverse("calls:call-api-initiate")
        data = {"phone_number": "+15551234567"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_default_create_disabled(self, api_client):
        """Direct POST to the list endpoint should return 405."""
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-list")
        data = {"direction": "outbound", "from_number": "100", "to_number": "+15551234567"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# =============================================================================
# Hangup Call API
# =============================================================================


@pytest.mark.django_db
class TestCallHangupAPI:
    def test_hangup_call_success(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="answered", user=user, answered_at=timezone.now())

        url = reverse("calls:call-api-hangup", kwargs={"pk": call.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ended"
        mock_ari_client.hangup_call.assert_called_once()

    def test_hangup_call_not_found_returns_404(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-hangup", kwargs={"pk": 99999})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_hangup_call_ari_failure_returns_500(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="answered", user=user)
        mock_ari_client.hangup_call.side_effect = Exception("ARI timeout")

        url = reverse("calls:call-api-hangup", kwargs={"pk": call.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_hangup_requires_auth(self, api_client, mock_ari_client):
        call = CallFactory()
        url = reverse("calls:call-api-hangup", kwargs={"pk": call.pk})
        response = api_client.post(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Answer Call API
# =============================================================================


@pytest.mark.django_db
class TestCallAnswerAPI:
    def test_answer_call_success(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="ringing")

        url = reverse("calls:call-api-answer", kwargs={"pk": call.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "answered"

    def test_answer_call_not_ringing_returns_400(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="initiated")

        url = reverse("calls:call-api-answer", kwargs={"pk": call.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_answer_call_not_found_returns_404(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-answer", kwargs={"pk": 99999})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_answer_call_ari_failure_returns_500(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="ringing")
        mock_ari_client.answer_call.side_effect = Exception("ARI error")

        url = reverse("calls:call-api-answer", kwargs={"pk": call.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_answer_requires_auth(self, api_client, mock_ari_client):
        call = CallFactory(status="ringing")
        url = reverse("calls:call-api-answer", kwargs={"pk": call.pk})
        response = api_client.post(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Call Status API
# =============================================================================


@pytest.mark.django_db
class TestCallStatusAPI:
    def test_call_status_success(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="answered", answered_at=timezone.now())
        mock_ari_client.get_channel.return_value = {"state": "Up"}

        url = reverse("calls:call-api-call-status", kwargs={"pk": call.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "answered"

    def test_call_status_not_found_returns_404(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-call-status", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_call_status_ended_call(self, api_client, mock_ari_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(status="ended", duration=300)

        url = reverse("calls:call-api-call-status", kwargs={"pk": call.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ended"
        assert response.data["duration"] == 300

    def test_call_status_requires_auth(self, api_client, mock_ari_client):
        call = CallFactory()
        url = reverse("calls:call-api-call-status", kwargs={"pk": call.pk})
        response = api_client.get(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Update Call Notes API
# =============================================================================


@pytest.mark.django_db
class TestCallNotesAPI:
    def test_update_notes_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-notes", kwargs={"pk": call.pk})
        data = {"notes": "Follow up needed"}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "Follow up needed"

    def test_update_notes_empty_string(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(notes="Previous notes")

        url = reverse("calls:call-api-notes", kwargs={"pk": call.pk})
        data = {"notes": ""}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == ""

    def test_update_notes_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("calls:call-api-notes", kwargs={"pk": 99999})
        data = {"notes": "test"}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_notes_requires_auth(self, api_client):
        call = CallFactory()
        url = reverse("calls:call-api-notes", kwargs={"pk": call.pk})
        data = {"notes": "test"}
        response = api_client.patch(url, data, format="json")
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Active Calls API
# =============================================================================


@pytest.mark.django_db
class TestActiveCallsAPI:
    def test_active_calls_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(status="initiated", user=user)
        CallFactory(status="answered", user=user)
        CallFactory(status="ended", user=user)

        url = reverse("calls:call-api-active")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "calls" in response.data
        assert len(response.data["calls"]) == 2

    def test_active_calls_empty(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CallFactory(status="ended")

        url = reverse("calls:call-api-active")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["calls"]) == 0

    def test_active_calls_requires_auth(self, api_client):
        url = reverse("calls:call-api-active")
        response = api_client.get(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Link Contact API
# =============================================================================


@pytest.mark.django_db
class TestLinkContactAPI:
    def test_link_contact_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(contact=None)
        contact = ContactFactory()

        url = reverse("calls:call-api-link-contact", kwargs={"pk": call.pk})
        data = {"contact_id": contact.pk}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["contact_id"] == contact.pk

    def test_link_contact_missing_contact_id_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-link-contact", kwargs={"pk": call.pk})
        data = {}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_link_contact_call_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        contact = ContactFactory()

        url = reverse("calls:call-api-link-contact", kwargs={"pk": 99999})
        data = {"contact_id": contact.pk}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_link_contact_contact_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-link-contact", kwargs={"pk": call.pk})
        data = {"contact_id": 99999}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_link_contact_requires_auth(self, api_client):
        call = CallFactory()
        contact = ContactFactory()
        url = reverse("calls:call-api-link-contact", kwargs={"pk": call.pk})
        data = {"contact_id": contact.pk}
        response = api_client.post(url, data, format="json")
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Link Opportunity API
# =============================================================================


@pytest.mark.django_db
class TestLinkOpportunityAPI:
    def test_link_opportunity_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory(opportunity=None)
        lead = LeadFactory()

        url = reverse("calls:call-api-link-opportunity", kwargs={"pk": call.pk})
        data = {"lead_id": lead.pk}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["opportunity_id"] == lead.pk

    def test_link_opportunity_missing_lead_id_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-link-opportunity", kwargs={"pk": call.pk})
        data = {}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_link_opportunity_call_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        lead = LeadFactory()

        url = reverse("calls:call-api-link-opportunity", kwargs={"pk": 99999})
        data = {"lead_id": lead.pk}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_link_opportunity_lead_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-link-opportunity", kwargs={"pk": call.pk})
        data = {"lead_id": 99999}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_link_opportunity_requires_auth(self, api_client):
        call = CallFactory()
        lead = LeadFactory()
        url = reverse("calls:call-api-link-opportunity", kwargs={"pk": call.pk})
        data = {"lead_id": lead.pk}
        response = api_client.post(url, data, format="json")
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )


# =============================================================================
# Disabled Endpoints
# =============================================================================


@pytest.mark.django_db
class TestDisabledEndpoints:
    def test_put_returns_405(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-detail", kwargs={"pk": call.pk})
        response = api_client.put(url, {}, format="json")

        # http_method_names does not include 'put', so should be 405
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_returns_405(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        call = CallFactory()

        url = reverse("calls:call-api-detail", kwargs={"pk": call.pk})
        response = api_client.delete(url)

        # http_method_names does not include 'delete', so should be 405
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
