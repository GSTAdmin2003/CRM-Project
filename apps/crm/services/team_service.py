"""
TeamService -- all business logic for SalesTeam CRUD.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import QuerySet

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from core.models import User

from ..models import SalesTeam


class TeamService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_teams() -> QuerySet[SalesTeam]:
        """Return a queryset of all active sales teams."""
        return SalesTeam.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def get_team_or_raise(*, pk: int) -> SalesTeam:
        """Fetch a sales team by PK or raise NotFoundError."""
        try:
            return SalesTeam.objects.select_related("manager").get(pk=pk)
        except SalesTeam.DoesNotExist:
            raise NotFoundError(f"Sales team with id {pk} not found")

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_team(
        *,
        name: str,
        created_by,
        description: str = "",
        manager_id: int | None = None,
        is_active: bool = True,
    ) -> SalesTeam:
        """
        Create a new sales team.

        Args:
            name: Team name (required, must be unique).
            created_by: User creating the team (used for permission check).
            description: Optional team description.
            manager_id: Optional FK to User who manages the team.
            is_active: Whether the team is active (default True).
        """
        if not (created_by.is_sales_manager() or created_by.is_sales_executive()):
            raise PermissionDeniedError(
                "You do not have permission to create teams"
            )

        if not name or not name.strip():
            raise ValidationError("Team name is required")

        name = name.strip()

        if SalesTeam.objects.filter(name=name).exists():
            raise ValidationError(f'A team with name "{name}" already exists')

        # Resolve manager
        manager = None
        if manager_id:
            try:
                manager = User.objects.get(pk=manager_id)
            except User.DoesNotExist:
                raise NotFoundError("Selected manager not found")

        team = SalesTeam.objects.create(
            name=name,
            description=description,
            manager=manager,
            is_active=is_active,
        )

        return team

    @staticmethod
    @transaction.atomic
    def update_team(*, pk: int, user, **fields) -> SalesTeam:
        """
        Update a sales team. Only allowed fields are applied.

        Args:
            pk: SalesTeam primary key.
            user: The user performing the update (permission check).
            **fields: Field name/value pairs to update.
        """
        team = TeamService.get_team_or_raise(pk=pk)

        if not (user.is_sales_manager() or user.is_sales_executive()):
            raise PermissionDeniedError(
                "You do not have permission to edit teams"
            )

        # Handle name validation
        name = fields.get("name")
        if name is not None:
            if not name or not name.strip():
                raise ValidationError("Team name is required")
            name = name.strip()
            if SalesTeam.objects.filter(name=name).exclude(pk=pk).exists():
                raise ValidationError(f'A team with name "{name}" already exists')
            fields["name"] = name

        # Handle manager_id -> manager resolution
        manager_id = fields.pop("manager_id", None)
        if manager_id is not None:
            if manager_id:
                try:
                    fields["manager"] = User.objects.get(pk=manager_id)
                except User.DoesNotExist:
                    raise NotFoundError("Selected manager not found")
            else:
                fields["manager"] = None

        allowed_fields = {"name", "description", "manager", "is_active"}
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(team, key, value)

        team.save()
        return team
