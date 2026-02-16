"""
ActivityService — all business logic for the activities app.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from datetime import date, timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..models import Activity, ActivityType


class ActivityService:
    # ── Queries ──────────────────────────────────────────────────────────

    @staticmethod
    def get_activities_for_user(
        *,
        user,
        view_context: str = "personal",
        team_id: str | None = None,
        date_filter: str = "week",
        custom_date: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> QuerySet[Activity]:
        """
        Return a filtered, permission-scoped queryset of activities.

        Args:
            user: The requesting user.
            view_context: 'personal' or 'team'.
            team_id: Team ID for team view (or 'all').
            date_filter: One of 'today', 'week', 'next_week', 'future', 'past',
                         'custom', 'range'.
            custom_date: Date string for 'custom' filter.
            start_date: Start date string for 'range' filter.
            end_date: End date string for 'range' filter.
        """
        qs = ActivityService._scope_by_permission(user, view_context, team_id)
        qs = ActivityService._apply_date_filter(qs, date_filter, custom_date, start_date, end_date)
        return qs.select_related("lead", "activity_type", "assigned_to").order_by(
            "scheduled_date", "created_at"
        )

    @staticmethod
    def get_activity_or_raise(*, pk: int) -> Activity:
        """Fetch an activity by PK or raise NotFoundError."""
        try:
            return Activity.objects.select_related(
                "lead", "activity_type", "assigned_to", "created_by"
            ).get(pk=pk)
        except Activity.DoesNotExist:
            raise NotFoundError(f"Activity with id {pk} not found")

    # ── Commands ─────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_activity(
        *,
        lead_id: int,
        activity_type_id: int,
        title: str,
        scheduled_date,
        created_by,
        assigned_to=None,
        description: str = "",
        status: str = "planned",
    ) -> Activity:
        """Create a new activity linked to an opportunity."""
        from apps.crm.models import Lead

        try:
            lead = Lead.objects.get(pk=lead_id)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Opportunity with id {lead_id} not found")

        try:
            activity_type = ActivityType.objects.get(pk=activity_type_id, is_active=True)
        except ActivityType.DoesNotExist:
            raise ValidationError("Invalid or inactive activity type")

        if not title.strip():
            raise ValidationError("Title is required")

        activity = Activity.objects.create(
            lead=lead,
            activity_type=activity_type,
            title=title.strip(),
            description=description,
            scheduled_date=scheduled_date,
            status=status,
            assigned_to=assigned_to or created_by,
            created_by=created_by,
        )
        return activity

    @staticmethod
    @transaction.atomic
    def update_activity(
        *,
        pk: int,
        user,
        **fields,
    ) -> Activity:
        """Update an activity. Only allowed fields are applied."""
        activity = ActivityService.get_activity_or_raise(pk=pk)

        if not activity.can_be_edited_by(user):
            raise PermissionDeniedError("You do not have permission to edit this activity")

        allowed_fields = {
            "title",
            "description",
            "scheduled_date",
            "status",
            "outcome",
            "assigned_to",
            "activity_type_id",
        }
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(activity, key, value)

        if activity.status == "completed" and not activity.completed_at:
            activity.completed_at = timezone.now()

        activity.save()
        return activity

    @staticmethod
    @transaction.atomic
    def complete_activity(*, pk: int, user, outcome: str = "") -> Activity:
        """Mark an activity as completed with optional outcome."""
        activity = ActivityService.get_activity_or_raise(pk=pk)

        if not activity.can_be_edited_by(user):
            raise PermissionDeniedError("You do not have permission to complete this activity")

        if activity.status == "completed":
            raise ValidationError("Activity is already completed")

        activity.status = "completed"
        activity.outcome = outcome
        activity.completed_at = timezone.now()
        activity.save()
        return activity

    @staticmethod
    @transaction.atomic
    def delete_activity(*, pk: int, user) -> None:
        """Delete an activity."""
        activity = ActivityService.get_activity_or_raise(pk=pk)

        if not activity.can_be_edited_by(user):
            raise PermissionDeniedError("You do not have permission to delete this activity")

        activity.delete()

    # ── Private helpers ──────────────────────────────────────────────────

    @staticmethod
    def _scope_by_permission(user, view_context: str, team_id: str | None) -> QuerySet[Activity]:
        """Build a queryset scoped to user permissions."""
        if view_context == "team" and (user.is_sales_manager() or user.is_sales_executive()):
            return ActivityService._team_queryset(user, team_id)

        # Personal view
        return Activity.objects.filter(lead__assigned_to=user)

    @staticmethod
    def _team_queryset(user, team_id: str | None) -> QuerySet[Activity]:
        """Build queryset for team view."""
        from apps.crm.models import SalesTeam

        if user.is_sales_executive():
            if not team_id or team_id == "all":
                return Activity.objects.all()
            try:
                target_team = SalesTeam.objects.get(id=team_id)
                team_members = target_team.get_team_members()
                return Activity.objects.filter(lead__assigned_to__in=team_members)
            except (SalesTeam.DoesNotExist, ValueError):
                return Activity.objects.none()

        # Manager — their own team only
        if user.sales_team:
            team_members = user.sales_team.get_team_members()
            return Activity.objects.filter(lead__assigned_to__in=team_members)

        return Activity.objects.none()

    @staticmethod
    def _apply_date_filter(
        qs: QuerySet[Activity],
        date_filter: str,
        custom_date: str,
        start_date: str,
        end_date: str,
    ) -> QuerySet[Activity]:
        """Apply date-based filtering to the queryset."""
        today = date.today()

        if date_filter == "today":
            return qs.filter(scheduled_date=today)
        elif date_filter == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return qs.filter(scheduled_date__range=[start_week, end_week])
        elif date_filter == "next_week":
            start_week = today - timedelta(days=today.weekday())
            start_next = start_week + timedelta(days=7)
            end_next = start_next + timedelta(days=6)
            return qs.filter(scheduled_date__range=[start_next, end_next])
        elif date_filter == "future":
            return qs.filter(scheduled_date__gt=today)
        elif date_filter == "past":
            return qs.filter(scheduled_date__lt=today)
        elif date_filter == "custom" and custom_date:
            return qs.filter(scheduled_date=custom_date)
        elif date_filter == "range" and start_date and end_date:
            return qs.filter(scheduled_date__range=[start_date, end_date])

        return qs
