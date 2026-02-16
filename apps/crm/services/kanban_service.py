"""
KanbanService -- business logic for the kanban board.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import QuerySet

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..models import Lead, LeadActivity, LeadStage, SalesTeam


class KanbanService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def get_kanban_data(
        *,
        user,
        view_context: str = "personal",
        team_id: str = "all",
    ) -> dict:
        """
        Build the complete kanban board data structure.

        Returns a dict with:
            - stages: list of dicts, each containing stage info, leads, totals.
            - available_teams: queryset of teams (for executives).
            - selected_team_id: resolved team selection.
            - target_team: resolved SalesTeam instance or None.

        Args:
            user: The requesting user.
            view_context: 'personal' or 'team'.
            team_id: Team ID string or 'all' for executives.
        """
        # Validate view context based on user permissions
        if view_context == "team" and not (
            user.is_sales_manager() or user.is_sales_executive()
        ):
            view_context = "personal"

        target_team, selected_team_id = KanbanService._resolve_team(
            user=user, view_context=view_context, team_id=team_id
        )

        stages = KanbanService._get_stages(
            view_context=view_context,
            selected_team_id=selected_team_id,
            target_team=target_team,
        )

        leads = KanbanService._get_leads(
            user=user,
            view_context=view_context,
            selected_team_id=selected_team_id,
            target_team=target_team,
        )

        # Build kanban data per stage
        kanban_stages = []
        for stage in stages:
            stage_leads = leads.filter(stage=stage)
            lead_list = []

            for lead in stage_leads:
                lead_list.append({
                    "id": lead.id,
                    "title": lead.title,
                    "full_name": lead.full_name,
                    "company_name": lead.company_name,
                    "estimated_value": str(lead.estimated_value),
                    "probability": lead.probability,
                    "assigned_to": (
                        lead.assigned_to.get_full_name() if lead.assigned_to else ""
                    ),
                    "created_at": lead.created_at.isoformat(),
                    "last_activity": lead.last_activity.isoformat(),
                })

            kanban_stages.append({
                "stage": {
                    "id": stage.id,
                    "name": stage.name,
                    "color": stage.color,
                    "probability": stage.probability,
                },
                "leads": lead_list,
                "total_value": sum(
                    float(lead.estimated_value) for lead in stage_leads
                ),
                "count": len(lead_list),
            })

        # Available teams for the team selector (executives only)
        available_teams = []
        if user.is_sales_executive():
            available_teams = SalesTeam.objects.filter(is_active=True).order_by("name")

        return {
            "stages": kanban_stages,
            "available_teams": available_teams,
            "selected_team_id": selected_team_id,
            "target_team": target_team,
            "view_context": view_context,
        }

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def update_lead_stage(*, lead_pk: int, new_stage_pk: int, user) -> Lead:
        """
        Move a lead to a new stage (e.g. drag-and-drop on the kanban board).

        Updates the lead's probability to match the new stage default and
        logs a stage-change activity.

        Args:
            lead_pk: Lead primary key.
            new_stage_pk: Target LeadStage primary key.
            user: The user performing the move.

        Returns:
            The updated Lead instance.
        """
        try:
            lead = Lead.objects.select_related("stage").get(pk=lead_pk)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Opportunity with id {lead_pk} not found")

        if not lead.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to edit this opportunity"
            )

        try:
            new_stage = LeadStage.objects.get(pk=new_stage_pk, is_active=True)
        except LeadStage.DoesNotExist:
            raise NotFoundError(f"Stage with id {new_stage_pk} not found")

        old_stage = lead.stage

        # Update lead stage and probability
        lead.stage = new_stage
        lead.probability = new_stage.probability
        lead.save()

        # Log activity
        LeadActivity.objects.create(
            lead=lead,
            user=user,
            activity_type="stage_change",
            subject=f"Stage changed from {old_stage.name} to {new_stage.name}",
            description=f"Opportunity moved from {old_stage.name} to {new_stage.name}",
        )

        return lead

    # -- Private helpers -------------------------------------------------------

    @staticmethod
    def _resolve_team(
        *, user, view_context: str, team_id: str
    ) -> tuple["SalesTeam | None", str]:
        """
        Determine the target team and resolved team_id based on user
        permissions and selection.

        Returns:
            (target_team, selected_team_id)
        """
        target_team = None
        selected_team_id = team_id

        if view_context == "team":
            if user.is_sales_executive():
                # Executives can view any team or all teams
                if selected_team_id != "all":
                    try:
                        target_team = SalesTeam.objects.get(id=selected_team_id)
                    except (SalesTeam.DoesNotExist, ValueError):
                        selected_team_id = "all"
            else:
                # Managers can only view their own team
                target_team = user.sales_team
                selected_team_id = str(target_team.id) if target_team else "all"
        else:
            # For personal view, use user's team for stage selection
            target_team = user.sales_team

        return target_team, selected_team_id

    @staticmethod
    def _get_stages(
        *, view_context: str, selected_team_id: str, target_team
    ) -> QuerySet[LeadStage]:
        """Get the appropriate stages for the kanban view."""
        if view_context == "team" and selected_team_id == "all":
            # Show global stages when viewing all teams
            return LeadStage.objects.filter(
                sales_team=None, is_active=True
            ).order_by("order")

        # Use team-specific stages or fallback to global
        return LeadStage.get_stages_for_team(target_team)

    @staticmethod
    def _get_leads(
        *, user, view_context: str, selected_team_id: str, target_team
    ) -> QuerySet[Lead]:
        """Get the permission-scoped leads queryset for the kanban."""
        if view_context == "team":
            if selected_team_id == "all" and user.is_sales_executive():
                return Lead.objects.all()
            elif target_team:
                team_members = target_team.get_team_members()
                return Lead.objects.filter(assigned_to__in=team_members)
            else:
                return Lead.objects.filter(assigned_to=user)
        else:
            # Personal view — user's own leads
            return Lead.objects.filter(assigned_to=user)
