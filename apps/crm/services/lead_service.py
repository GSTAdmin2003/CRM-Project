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

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError

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
        title: str = "",
        company_id: int | None = None,
        stage_id: int | None = None,
        assigned_to=None,
        created_by,
        **kwargs,
    ) -> Lead:
        """
        Create a new lead with activity logging.

        Args:
            title: Lead/opportunity title (optional — defaults to company_name or "New Lead").
            company_id: FK to contacts.Company (optional).
            stage_id: FK to LeadStage. If not provided, uses the default
                      stage for the assigned user's team. For status='new' leads,
                      a missing stage is acceptable (stage is nullable).
            assigned_to: User to assign the lead to (optional).
            created_by: User creating the lead (required).
            **kwargs: Optional fields — full_name, email, phone, position,
                      estimated_value, probability, expected_close_date,
                      source, status, notes, contact_id, sales_team_id.
        """
        # Derive a title if none provided
        if not title or not title.strip():
            title = (
                kwargs.get("company_name", "")
                or kwargs.get("full_name", "")
                or "New Lead"
            )

        # Resolve company
        company = None
        if company_id:
            from apps.contacts.models import Company

            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                raise NotFoundError(f"Company with id {company_id} not found")

        # Resolve stage
        lead_status = kwargs.get("status", "new")
        if stage_id:
            try:
                stage = LeadStage.objects.get(pk=stage_id, is_active=True)
            except LeadStage.DoesNotExist:
                raise NotFoundError(f"Stage with id {stage_id} not found")
        elif lead_status == "new":
            # Incoming leads don't require a stage
            stage = None
        else:
            # Opportunities need a stage — default to first available
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

        # Opportunities must always have a team
        if lead_status == "converted" and not sales_team:
            raise ValidationError("Opportunities must have a sales team assigned")

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
            "lost_reason",
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

        # Opportunities must always have a team
        if lead.status == "converted" and not lead.sales_team_id:
            raise ValidationError("Opportunities must have a sales team assigned")

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
    def convert_lead_to_opportunity(*, lead: Lead, user) -> Lead:
        """
        Convert a status='new' lead into a pipeline opportunity (status='converted').

        Assigns a default stage if none is set. Raises ConflictError if the lead
        is not in 'new' status.
        """
        if lead.status != "new":
            raise ConflictError("Only active leads (status=new) can be converted")

        # Opportunities must always have a team
        team = lead.sales_team or (user.sales_team if user else None)
        if not team:
            raise ValidationError(
                "Opportunities must have a sales team assigned. "
                "Please assign the lead to a team before converting."
            )

        # Ensure a stage is assigned — use the 'contacted' stage for converted leads
        if not lead.stage:
            stage = LeadStage.get_contacted_stage_for_team(team) or LeadStage.get_default_stage_for_team(team)
            if not stage:
                raise ValidationError("No active stages available for conversion")
            lead.stage = stage

        # Ensure a title
        if not lead.title or not lead.title.strip():
            lead.title = lead.company_name or lead.full_name or "Converted Lead"

        lead.status = "converted"
        lead.save()

        LeadActivity.objects.create(
            lead=lead,
            user=user,
            activity_type="converted",
            subject=f'Lead "{lead.title}" converted to opportunity',
            description="Lead converted to pipeline opportunity",
        )
        return lead

    @staticmethod
    @transaction.atomic
    def mark_won(*, lead: Lead, user) -> Lead:
        """Mark a converted opportunity as won."""
        if not lead.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to mark this opportunity as won"
            )
        if lead.status not in ("converted", "new"):
            raise ConflictError(
                f'Cannot mark as won — current status is "{lead.status}"'
            )

        lead.status = "won"
        lead.stage = None
        lead.save()

        LeadActivity.objects.create(
            lead=lead,
            user=user,
            activity_type="updated",
            subject=f'Opportunity "{lead.title}" marked as won',
            description="Opportunity marked as won",
        )
        return lead

    @staticmethod
    @transaction.atomic
    def mark_lost(*, lead: Lead, reason: str = "", user) -> Lead:
        """Mark a lead or opportunity as lost."""
        if not lead.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to mark this as lost"
            )
        if lead.status == "won":
            raise ConflictError('Cannot mark as lost — opportunity is already won')

        lead.status = "lost"
        lead.lost_reason = reason
        lead.stage = None
        lead.save()

        description = f"Reason: {reason}" if reason else "Marked as lost"
        LeadActivity.objects.create(
            lead=lead,
            user=user,
            activity_type="updated",
            subject=f'"{lead.title}" marked as lost',
            description=description,
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
