"""
StageService -- business logic for LeadStage (kanban stage) management.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import models, transaction
from django.db.models import QuerySet

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError

from ..models import LeadStage, SalesTeam


class StageService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def get_stages_for_team(*, team) -> QuerySet[LeadStage]:
        """
        Return the stages for a given team, falling back to global stages
        if the team has no custom stages.

        Args:
            team: SalesTeam instance or None for global stages.
        """
        return LeadStage.get_stages_for_team(team)

    @staticmethod
    def get_stage_or_raise(*, pk: int) -> LeadStage:
        """Fetch a stage by PK or raise NotFoundError."""
        try:
            return LeadStage.objects.select_related("sales_team", "created_by").get(pk=pk)
        except LeadStage.DoesNotExist:
            raise NotFoundError(f"Stage with id {pk} not found")

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_stage(
        *,
        name: str,
        team_pk: int,
        user,
        description: str = "",
        color: str = "#6B7280",
        probability: int = 0,
        is_closed_stage: bool = False,
    ) -> LeadStage:
        """
        Create a new stage for a specific team.

        Args:
            name: Stage name (required).
            team_pk: SalesTeam primary key (required).
            user: The user creating the stage (permission check).
            description: Optional stage description.
            color: Hex color code (default grey).
            probability: Default probability percentage 0-100.
            is_closed_stage: Whether this is a closed (won/lost) stage.
        """
        try:
            team = SalesTeam.objects.get(pk=team_pk)
        except SalesTeam.DoesNotExist:
            raise NotFoundError(f"Sales team with id {team_pk} not found")

        # Check permissions: directors can manage any stage; managers only their own team
        if not (
            user.is_sales_director()
            or (user.is_sales_manager() and team.manager == user)
        ):
            raise PermissionDeniedError(
                "You do not have permission to manage stages for this team"
            )

        if not name or not name.strip():
            raise ValidationError("Stage name is required")
        name = name.strip()

        # Validate probability
        if not isinstance(probability, int) or probability < 0 or probability > 100:
            raise ValidationError("Probability must be a number between 0 and 100")

        # Check for duplicate name in the same team
        if LeadStage.objects.filter(name=name, sales_team=team).exists():
            raise ValidationError(
                f'A stage named "{name}" already exists for this team'
            )

        # Calculate next order number for this team
        existing_stages = LeadStage.objects.filter(sales_team=team)
        next_order = (existing_stages.aggregate(models.Max("order"))["order__max"] or 0) + 1

        stage = LeadStage.objects.create(
            name=name,
            description=description,
            color=color,
            probability=probability,
            is_closed_stage=is_closed_stage,
            sales_team=team,
            order=next_order,
            created_by=user,
        )

        return stage

    @staticmethod
    @transaction.atomic
    def update_stage(*, pk: int, user, **fields) -> LeadStage:
        """
        Update a stage. Only allowed fields are applied.

        Args:
            pk: LeadStage primary key.
            user: The user performing the update (permission check).
            **fields: Field name/value pairs to update.
        """
        stage = StageService.get_stage_or_raise(pk=pk)

        if not stage.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to edit this stage"
            )

        # Validate name if being updated
        name = fields.get("name")
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("Stage name is required")
            name = name.strip()
            # Check uniqueness within the team
            if (
                LeadStage.objects.filter(name=name, sales_team=stage.sales_team)
                .exclude(pk=pk)
                .exists()
            ):
                raise ValidationError(
                    f'A stage named "{name}" already exists for this team'
                )
            fields["name"] = name

        # Validate probability if being updated
        probability = fields.get("probability")
        if probability is not None:
            if not isinstance(probability, int) or probability < 0 or probability > 100:
                raise ValidationError(
                    "Probability must be a number between 0 and 100"
                )

        allowed_fields = {
            "name",
            "description",
            "color",
            "probability",
            "is_closed_stage",
        }
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(stage, key, value)

        stage.save()
        return stage

    @staticmethod
    @transaction.atomic
    def delete_stage(*, pk: int, user) -> str:
        """
        Delete a stage, but only if it has no leads.

        Args:
            pk: LeadStage primary key.
            user: The user requesting deletion (permission check).

        Returns:
            The name of the deleted stage for confirmation messaging.
        """
        stage = StageService.get_stage_or_raise(pk=pk)

        if not stage.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to delete this stage"
            )

        if stage.leads.exists():
            raise ConflictError(
                f'Cannot delete stage "{stage.name}" because it contains leads. '
                "Move the leads to another stage first."
            )

        stage_name = stage.name
        stage.delete()
        return stage_name
