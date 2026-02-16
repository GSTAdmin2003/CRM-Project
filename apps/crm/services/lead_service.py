"""
LeadService -- all business logic for Lead (Opportunity) CRUD.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import QuerySet

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..models import Lead, LeadActivity, LeadStage


class LeadService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_leads_for_user(*, user) -> QuerySet[Lead]:
        """
        Return a permission-scoped queryset of leads for the given user.

        Executives see all leads, managers see their team's leads,
        sales reps see only their own.
        """
        return user.get_accessible_leads_queryset()

    @staticmethod
    def get_lead_or_raise(*, pk: int) -> Lead:
        """Fetch a lead by PK or raise NotFoundError."""
        try:
            return Lead.objects.select_related(
                "stage", "assigned_to", "sales_team", "company", "contact", "created_by"
            ).get(pk=pk)
        except Lead.DoesNotExist:
            raise NotFoundError(f"Opportunity with id {pk} not found")

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_lead(
        *,
        title: str,
        company_id: int | None = None,
        stage_id: int | None = None,
        assigned_to=None,
        created_by,
        **kwargs,
    ) -> Lead:
        """
        Create a new lead with activity logging.

        Args:
            title: Opportunity title (required).
            company_id: FK to contacts.Company (optional).
            stage_id: FK to LeadStage. If not provided, uses the default
                      stage for the assigned user's team.
            assigned_to: User to assign the lead to (optional).
            created_by: User creating the lead (required).
            **kwargs: Optional fields — full_name, email, phone, position,
                      estimated_value, probability, expected_close_date,
                      source, status, notes, contact_id, sales_team_id.
        """
        if not title or not title.strip():
            raise ValidationError("Opportunity title is required")

        # Resolve company
        company = None
        if company_id:
            from apps.contacts.models import Company

            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                raise NotFoundError(f"Company with id {company_id} not found")

        # Resolve stage
        if stage_id:
            try:
                stage = LeadStage.objects.get(pk=stage_id, is_active=True)
            except LeadStage.DoesNotExist:
                raise NotFoundError(f"Stage with id {stage_id} not found")
        else:
            # Default to the first stage for the user's team
            user_team = created_by.sales_team if created_by else None
            stage = LeadStage.get_default_stage_for_team(user_team)
            if not stage:
                raise ValidationError("No active stages available")

        # Resolve contact
        contact = None
        contact_id = kwargs.pop("contact_id", None)
        if contact_id:
            from apps.contacts.models import Contact

            try:
                contact = Contact.objects.get(pk=contact_id)
            except Contact.DoesNotExist:
                raise NotFoundError(f"Contact with id {contact_id} not found")

        # Resolve sales_team
        sales_team = None
        sales_team_id = kwargs.pop("sales_team_id", None)
        if sales_team_id:
            from ..models import SalesTeam

            try:
                sales_team = SalesTeam.objects.get(pk=sales_team_id)
            except SalesTeam.DoesNotExist:
                raise NotFoundError(f"Sales team with id {sales_team_id} not found")

        # Build allowed kwargs
        allowed_fields = {
            "full_name",
            "email",
            "phone",
            "position",
            "estimated_value",
            "probability",
            "expected_close_date",
            "source",
            "status",
            "notes",
            "company_name",
        }
        create_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}

        lead = Lead.objects.create(
            title=title.strip(),
            stage=stage,
            company=company,
            contact=contact,
            assigned_to=assigned_to,
            sales_team=sales_team,
            created_by=created_by,
            **create_kwargs,
        )

        # Log creation activity
        company_display = company.legal_name if company else "unknown company"
        LeadActivity.objects.create(
            lead=lead,
            user=created_by,
            activity_type="created",
            subject=f'Opportunity "{lead.title}" created',
            description=f"New opportunity created for {company_display}",
        )

        return lead

    @staticmethod
    @transaction.atomic
    def update_lead(*, pk: int, user, **fields) -> Lead:
        """
        Update a lead. Only allowed fields are applied.

        Logs a stage-change activity when the stage changes, plus a
        general 'updated' activity entry.

        Args:
            pk: Lead primary key.
            user: The user performing the update.
            **fields: Field name/value pairs to update.
        """
        lead = LeadService.get_lead_or_raise(pk=pk)

        if not lead.can_be_edited_by(user):
            raise PermissionDeniedError("You do not have permission to edit this opportunity")

        old_stage = lead.stage

        allowed_fields = {
            "title",
            "full_name",
            "email",
            "phone",
            "position",
            "company_name",
            "estimated_value",
            "probability",
            "expected_close_date",
            "source",
            "status",
            "notes",
            "stage_id",
            "assigned_to_id",
            "company_id",
            "contact_id",
            "sales_team_id",
        }
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(lead, key, value)

        lead.save()

        # Log stage change if it occurred
        if lead.stage != old_stage:
            LeadActivity.objects.create(
                lead=lead,
                user=user,
                activity_type="stage_change",
                subject=f"Stage changed from {old_stage.name} to {lead.stage.name}",
                description=(
                    f"Opportunity stage updated from {old_stage.name} to {lead.stage.name}"
                ),
            )

        # Log general update
        LeadActivity.objects.create(
            lead=lead,
            user=user,
            activity_type="updated",
            subject=f'Opportunity "{lead.title}" updated',
            description="Opportunity information was updated",
        )

        return lead

    @staticmethod
    @transaction.atomic
    def delete_lead(*, pk: int, user) -> str:
        """
        Delete a lead after permission check.

        Args:
            pk: Lead primary key.
            user: The user requesting deletion.

        Returns:
            The title of the deleted lead for confirmation messaging.
        """
        lead = LeadService.get_lead_or_raise(pk=pk)

        if not lead.can_be_edited_by(user):
            raise PermissionDeniedError("You do not have permission to delete this opportunity")

        lead_title = lead.title
        lead.delete()
        return lead_title
