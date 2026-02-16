"""
Tests for Activity and ActivityType models.
"""

import pytest
from datetime import date, timedelta

from apps.activities.models import Activity, ActivityType
from core.models import Role, UserRole

from .conftest import ActivityFactory, ActivityTypeFactory, LeadFactory, SalesTeamFactory, UserFactory


@pytest.mark.django_db
class TestActivityType:
    def test_create_activity_type(self):
        at = ActivityTypeFactory(name="Phone Call", icon="fas fa-phone", color="#3b82f6")
        assert at.name == "Phone Call"
        assert at.icon == "fas fa-phone"
        assert at.color == "#3b82f6"
        assert at.is_active is True
        assert at.created_at is not None

    def test_str_representation(self):
        at = ActivityTypeFactory(name="Meeting")
        assert str(at) == "Meeting"

    def test_ordering_by_name(self):
        ActivityTypeFactory(name="Zoom Call")
        ActivityTypeFactory(name="Email")
        ActivityTypeFactory(name="Meeting")
        types = list(ActivityType.objects.values_list("name", flat=True))
        assert types == sorted(types)


@pytest.mark.django_db
class TestActivity:
    def test_create_activity(self):
        activity = ActivityFactory(title="Follow up call")
        assert activity.title == "Follow up call"
        assert activity.status == "planned"
        assert activity.lead is not None
        assert activity.activity_type is not None
        assert activity.assigned_to is not None
        assert activity.created_by is not None

    def test_str_representation(self):
        activity = ActivityFactory(title="Demo meeting")
        expected = f"{activity.activity_type.name}: Demo meeting ({activity.lead.title})"
        assert str(activity) == expected

    def test_is_overdue_past_date_planned(self):
        activity = ActivityFactory(
            scheduled_date=date.today() - timedelta(days=1), status="planned"
        )
        assert activity.is_overdue() is True

    def test_is_not_overdue_future_date(self):
        activity = ActivityFactory(
            scheduled_date=date.today() + timedelta(days=1), status="planned"
        )
        assert activity.is_overdue() is False

    def test_is_not_overdue_completed(self):
        activity = ActivityFactory(
            scheduled_date=date.today() - timedelta(days=1), status="completed"
        )
        assert activity.is_overdue() is False

    def test_can_be_viewed_by_executive(self, role_sales_executive):
        activity = ActivityFactory()
        exec_user = UserFactory()
        UserRole.objects.create(user=exec_user, role=role_sales_executive)
        assert activity.can_be_viewed_by(exec_user) is True

    def test_can_be_viewed_by_assigned_user(self):
        user = UserFactory()
        lead = LeadFactory(assigned_to=user)
        activity = ActivityFactory(lead=lead)
        assert activity.can_be_viewed_by(user) is True

    def test_cannot_be_viewed_by_other_user(self):
        activity = ActivityFactory()
        other_user = UserFactory()
        assert activity.can_be_viewed_by(other_user) is False

    def test_can_be_viewed_by_creator(self):
        creator = UserFactory()
        activity = ActivityFactory(created_by=creator)
        assert activity.can_be_viewed_by(creator) is True

    def test_can_be_viewed_by_manager_same_team(self, role_sales_manager):
        team = SalesTeamFactory()
        manager = UserFactory(sales_team=team)
        UserRole.objects.create(user=manager, role=role_sales_manager)
        member = UserFactory(sales_team=team)
        lead = LeadFactory(assigned_to=member, sales_team=team)
        activity = ActivityFactory(lead=lead)
        assert activity.can_be_viewed_by(manager) is True

    def test_can_be_edited_by_executive(self, role_sales_executive):
        activity = ActivityFactory()
        exec_user = UserFactory()
        UserRole.objects.create(user=exec_user, role=role_sales_executive)
        assert activity.can_be_edited_by(exec_user) is True

    def test_can_be_edited_by_assigned_to(self):
        user = UserFactory()
        activity = ActivityFactory(assigned_to=user)
        assert activity.can_be_edited_by(user) is True

    def test_can_be_edited_by_creator(self):
        creator = UserFactory()
        activity = ActivityFactory(created_by=creator)
        assert activity.can_be_edited_by(creator) is True

    def test_cannot_be_edited_by_other_user(self):
        activity = ActivityFactory()
        other_user = UserFactory()
        assert activity.can_be_edited_by(other_user) is False
