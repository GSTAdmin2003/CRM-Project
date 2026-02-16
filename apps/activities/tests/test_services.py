"""
Tests for ActivityService business logic.
"""

import pytest
from datetime import date, timedelta

from django.utils import timezone

from apps.activities.models import Activity
from apps.activities.services import ActivityService
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from core.models import Role, UserRole

from .conftest import (
    ActivityFactory,
    ActivityTypeFactory,
    LeadFactory,
    SalesTeamFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestActivityServiceCreate:
    def test_create_activity_success(self):
        lead = LeadFactory()
        activity_type = ActivityTypeFactory()
        user = lead.assigned_to

        activity = ActivityService.create_activity(
            lead_id=lead.pk,
            activity_type_id=activity_type.pk,
            title="Follow up call",
            scheduled_date=date.today() + timedelta(days=1),
            created_by=user,
        )

        assert activity.pk is not None
        assert activity.title == "Follow up call"
        assert activity.lead == lead
        assert activity.activity_type == activity_type
        assert activity.created_by == user
        assert activity.assigned_to == user  # defaults to created_by
        assert activity.status == "planned"

    def test_create_activity_with_assigned_to(self):
        lead = LeadFactory()
        activity_type = ActivityTypeFactory()
        assignee = UserFactory()

        activity = ActivityService.create_activity(
            lead_id=lead.pk,
            activity_type_id=activity_type.pk,
            title="Team meeting",
            scheduled_date=date.today(),
            created_by=lead.assigned_to,
            assigned_to=assignee,
        )

        assert activity.assigned_to == assignee

    def test_create_activity_invalid_lead_raises_not_found(self):
        activity_type = ActivityTypeFactory()
        user = UserFactory()

        with pytest.raises(NotFoundError):
            ActivityService.create_activity(
                lead_id=99999,
                activity_type_id=activity_type.pk,
                title="Test",
                scheduled_date=date.today(),
                created_by=user,
            )

    def test_create_activity_invalid_type_raises_validation(self):
        lead = LeadFactory()
        user = lead.assigned_to

        with pytest.raises(ValidationError):
            ActivityService.create_activity(
                lead_id=lead.pk,
                activity_type_id=99999,
                title="Test",
                scheduled_date=date.today(),
                created_by=user,
            )

    def test_create_activity_inactive_type_raises_validation(self):
        lead = LeadFactory()
        inactive_type = ActivityTypeFactory(is_active=False)
        user = lead.assigned_to

        with pytest.raises(ValidationError):
            ActivityService.create_activity(
                lead_id=lead.pk,
                activity_type_id=inactive_type.pk,
                title="Test",
                scheduled_date=date.today(),
                created_by=user,
            )

    def test_create_activity_empty_title_raises_validation(self):
        lead = LeadFactory()
        activity_type = ActivityTypeFactory()
        user = lead.assigned_to

        with pytest.raises(ValidationError):
            ActivityService.create_activity(
                lead_id=lead.pk,
                activity_type_id=activity_type.pk,
                title="   ",
                scheduled_date=date.today(),
                created_by=user,
            )


@pytest.mark.django_db
class TestActivityServiceUpdate:
    def test_update_activity_title(self):
        activity = ActivityFactory()

        updated = ActivityService.update_activity(
            pk=activity.pk, user=activity.created_by, title="Updated title"
        )

        assert updated.title == "Updated title"

    def test_update_activity_permission_denied(self):
        activity = ActivityFactory()
        other_user = UserFactory()

        with pytest.raises(PermissionDeniedError):
            ActivityService.update_activity(
                pk=activity.pk, user=other_user, title="Nope"
            )

    def test_update_activity_not_found(self):
        user = UserFactory()

        with pytest.raises(NotFoundError):
            ActivityService.update_activity(pk=99999, user=user, title="Nope")

    def test_update_activity_sets_completed_at_on_status_change(self):
        activity = ActivityFactory(status="planned")

        updated = ActivityService.update_activity(
            pk=activity.pk, user=activity.created_by, status="completed"
        )

        assert updated.status == "completed"
        assert updated.completed_at is not None


@pytest.mark.django_db
class TestActivityServiceComplete:
    def test_complete_activity_success(self):
        activity = ActivityFactory(status="planned")

        completed = ActivityService.complete_activity(
            pk=activity.pk, user=activity.created_by, outcome="Went well"
        )

        assert completed.status == "completed"
        assert completed.outcome == "Went well"
        assert completed.completed_at is not None

    def test_complete_already_completed_raises_validation(self):
        activity = ActivityFactory(status="completed", completed_at=timezone.now())

        with pytest.raises(ValidationError):
            ActivityService.complete_activity(
                pk=activity.pk, user=activity.created_by
            )

    def test_complete_activity_permission_denied(self):
        activity = ActivityFactory()
        other_user = UserFactory()

        with pytest.raises(PermissionDeniedError):
            ActivityService.complete_activity(pk=activity.pk, user=other_user)


@pytest.mark.django_db
class TestActivityServiceDelete:
    def test_delete_activity_success(self):
        activity = ActivityFactory()
        pk = activity.pk

        ActivityService.delete_activity(pk=pk, user=activity.created_by)

        assert not Activity.objects.filter(pk=pk).exists()

    def test_delete_activity_permission_denied(self):
        activity = ActivityFactory()
        other_user = UserFactory()

        with pytest.raises(PermissionDeniedError):
            ActivityService.delete_activity(pk=activity.pk, user=other_user)

    def test_delete_activity_not_found(self):
        user = UserFactory()

        with pytest.raises(NotFoundError):
            ActivityService.delete_activity(pk=99999, user=user)


@pytest.mark.django_db
class TestActivityServiceQueries:
    def test_get_activity_or_raise_success(self):
        activity = ActivityFactory()
        result = ActivityService.get_activity_or_raise(pk=activity.pk)
        assert result.pk == activity.pk

    def test_get_activity_or_raise_not_found(self):
        with pytest.raises(NotFoundError):
            ActivityService.get_activity_or_raise(pk=99999)

    def test_get_activities_personal_view(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        my_activity = ActivityFactory(lead=lead, scheduled_date=date.today())
        other_activity = ActivityFactory(scheduled_date=date.today())

        result = ActivityService.get_activities_for_user(
            user=user, view_context="personal", date_filter="today"
        )

        assert my_activity in result
        assert other_activity not in result

    def test_get_activities_team_view_executive(self, role_sales_executive):
        exec_user = UserFactory()
        UserRole.objects.create(user=exec_user, role=role_sales_executive)

        activity = ActivityFactory(scheduled_date=date.today())

        result = ActivityService.get_activities_for_user(
            user=exec_user, view_context="team", team_id="all", date_filter="today"
        )

        assert activity in result

    def test_get_activities_date_filter_today(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        today_activity = ActivityFactory(lead=lead, scheduled_date=date.today())
        tomorrow_activity = ActivityFactory(
            lead=lead, scheduled_date=date.today() + timedelta(days=1)
        )

        result = ActivityService.get_activities_for_user(
            user=user, view_context="personal", date_filter="today"
        )

        assert today_activity in result
        assert tomorrow_activity not in result

    def test_get_activities_date_filter_future(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        past_activity = ActivityFactory(
            lead=lead, scheduled_date=date.today() - timedelta(days=1)
        )
        future_activity = ActivityFactory(
            lead=lead, scheduled_date=date.today() + timedelta(days=5)
        )

        result = ActivityService.get_activities_for_user(
            user=user, view_context="personal", date_filter="future"
        )

        assert future_activity in result
        assert past_activity not in result
