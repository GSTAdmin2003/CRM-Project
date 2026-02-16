"""
Tests for Activities DRF API endpoints.

Note: We use api_client.force_login() instead of force_authenticate() because
the RoleBasedAccessMiddleware checks request.user.is_authenticated at the Django
middleware layer, before DRF's authentication runs.
"""

import pytest
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status

from apps.activities.models import Activity
from core.models import Role, UserRole

from .conftest import ActivityFactory, ActivityTypeFactory, LeadFactory, UserFactory


@pytest.mark.django_db
class TestActivityListAPI:
    def test_list_requires_auth(self, api_client):
        url = reverse("activities:activity-list")
        response = api_client.get(url)
        # Middleware redirects to login (302), not DRF 403
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_activities_personal(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        lead = LeadFactory(assigned_to=user)
        my_activity = ActivityFactory(lead=lead, scheduled_date=date.today())
        other_activity = ActivityFactory(scheduled_date=date.today())

        url = reverse("activities:activity-list")
        response = api_client.get(url, {"view": "personal", "filter": "today"})

        assert response.status_code == status.HTTP_200_OK
        ids = [a["id"] for a in response.data["results"]]
        assert my_activity.pk in ids
        assert other_activity.pk not in ids


@pytest.mark.django_db
class TestActivityCreateAPI:
    def test_create_activity(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        lead = LeadFactory(assigned_to=user)
        activity_type = ActivityTypeFactory()

        url = reverse("activities:activity-list")
        data = {
            "lead_id": lead.pk,
            "activity_type_id": activity_type.pk,
            "title": "API created activity",
            "scheduled_date": str(date.today() + timedelta(days=1)),
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "API created activity"
        assert Activity.objects.filter(title="API created activity").exists()

    def test_create_activity_invalid_lead(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        activity_type = ActivityTypeFactory()

        url = reverse("activities:activity-list")
        data = {
            "lead_id": 99999,
            "activity_type_id": activity_type.pk,
            "title": "Test",
            "scheduled_date": str(date.today()),
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestActivityDetailAPI:
    def test_retrieve_activity(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        lead = LeadFactory(assigned_to=user)
        activity = ActivityFactory(lead=lead, scheduled_date=date.today())

        url = reverse("activities:activity-detail", kwargs={"pk": activity.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == activity.pk
        assert response.data["title"] == activity.title


@pytest.mark.django_db
class TestActivityDeleteAPI:
    def test_delete_activity(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        activity = ActivityFactory(created_by=user, assigned_to=user)
        pk = activity.pk

        url = reverse("activities:activity-detail", kwargs={"pk": pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Activity.objects.filter(pk=pk).exists()

    def test_delete_activity_permission_denied(self, api_client):
        other_user = UserFactory()
        api_client.force_login(other_user)
        activity = ActivityFactory()

        url = reverse("activities:activity-detail", kwargs={"pk": activity.pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestActivityCompleteAPI:
    def test_complete_activity(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        activity = ActivityFactory(
            created_by=user, assigned_to=user, status="planned"
        )

        url = reverse("activities:activity-complete", kwargs={"pk": activity.pk})
        response = api_client.post(url, {"outcome": "Went great"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "completed"
        assert response.data["outcome"] == "Went great"
        assert response.data["completed_at"] is not None

    def test_complete_already_completed_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        activity = ActivityFactory(created_by=user, assigned_to=user, status="planned")
        # Complete it first
        Activity.objects.filter(pk=activity.pk).update(status="completed")
        activity.refresh_from_db()

        url = reverse("activities:activity-complete", kwargs={"pk": activity.pk})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestActivityTypeAPI:
    def test_list_activity_types(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        ActivityTypeFactory(name="Call")
        ActivityTypeFactory(name="Meeting")
        ActivityTypeFactory(name="Inactive Type", is_active=False)

        url = reverse("activities:activity-type-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        names = [t["name"] for t in response.data["results"]]
        assert "Call" in names
        assert "Meeting" in names
        assert "Inactive Type" not in names
