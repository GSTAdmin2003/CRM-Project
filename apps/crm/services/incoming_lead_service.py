"""
IncomingLeadService -- business logic for IncomingLead CRUD and conversion.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import QuerySet

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError

from ..models import IncomingLead, Lead, LeadActivity, LeadStage, SalesTeam


class IncomingLeadService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_incoming_leads(
        *,
        user,
        status_filter: str = "all",
        team_filter: str = "all",
    ) -> QuerySet[IncomingLead]:
        """
        Return a permission-scoped, filtered queryset of incoming leads.

        Executives see all leads. Managers see their team's leads.
        Sales reps see only their own assigned leads.

        Args:
            user: The requesting user.
            status_filter: One of 'all', 'new', 'contacted', 'converted', 'rejected'.
            team_filter: Team ID string or 'all' (executives only).
        """
        # Base queryset based on user permissions
        if user.is_sales_executive():
            qs = IncomingLead.objects.all()
        elif user.is_sales_manager() and user.sales_team:
            qs = IncomingLead.objects.filter(sales_team=user.sales_team)
        else:
            qs = IncomingLead.objects.filter(assigned_to=user)

        # Apply status filter
        if status_filter != "all":
            qs = qs.filter(status=status_filter)

        # Apply team filter (executives only)
        if user.is_sales_executive() and team_filter != "all":
            try:
                team = SalesTeam.objects.get(id=team_filter)
                qs = qs.filter(sales_team=team)
            except (SalesTeam.DoesNotExist, ValueError):
                pass

        return qs.select_related(
            "company", "contact", "sales_team", "assigned_to", "created_by"
        ).order_by("-created_at")

    @staticmethod
    def get_incoming_lead_or_raise(*, pk: int) -> IncomingLead:
        """Fetch an incoming lead by PK or raise NotFoundError."""
        try:
            return IncomingLead.objects.select_related(
                "company", "contact", "sales_team", "assigned_to",
                "created_by", "converted_opportunity",
            ).get(pk=pk)
        except IncomingLead.DoesNotExist:
            raise NotFoundError(f"Lead with id {pk} not found")

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_incoming_lead(
        *,
        created_by,
        company_id: int | None = None,
        contact_id: int | None = None,
        message: str = "",
        sales_team_id: int | None = None,
        assigned_to=None,
        **kwargs,
    ) -> IncomingLead:
        """
        Create a new incoming lead.

        Args:
            created_by: User creating the lead (required).
            company_id: FK to contacts.Company (optional).
            contact_id: FK to contacts.Contact (optional).
            message: Lead message or inquiry text.
            sales_team_id: FK to SalesTeam (optional).
            assigned_to: User to assign the lead to (optional).
            **kwargs: Optional fields — status, notes.
        """
        # Resolve company
        company = None
        if company_id:
            from apps.contacts.models import Company

            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                raise NotFoundError(f"Company with id {company_id} not found")

        # Resolve contact
        contact = None
        if contact_id:
            from apps.contacts.models import Contact

            try:
                contact = Contact.objects.get(pk=contact_id)
            except Contact.DoesNotExist:
                raise NotFoundError(f"Contact with id {contact_id} not found")

        # Resolve sales_team
        sales_team = None
        if sales_team_id:
            try:
                sales_team = SalesTeam.objects.get(pk=sales_team_id)
            except SalesTeam.DoesNotExist:
                raise NotFoundError(f"Sales team with id {sales_team_id} not found")

        # Auto-assign sales team from assigned user if not specified
        if not sales_team and assigned_to and assigned_to.sales_team:
            sales_team = assigned_to.sales_team

        allowed_fields = {"status", "notes"}
        create_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}

        lead = IncomingLead.objects.create(
            company=company,
            contact=contact,
            message=message,
            sales_team=sales_team,
            assigned_to=assigned_to,
            created_by=created_by,
            **create_kwargs,
        )

        return lead

    @staticmethod
    @transaction.atomic
    def convert_to_opportunity(*, pk: int, user) -> Lead:
        """
        Convert an incoming lead into a full opportunity (Lead).

        Creates the opportunity, updates the incoming lead status to
        'converted', and links the two records.

        Args:
            pk: IncomingLead primary key.
            user: The user performing the conversion.

        Returns:
            The newly created Lead (opportunity).
        """
        incoming_lead = IncomingLeadService.get_incoming_lead_or_raise(pk=pk)

        if not incoming_lead.can_be_edited_by(user):
            raise PermissionDeniedError(
                "You do not have permission to convert this lead"
            )

        if incoming_lead.status == "converted":
            raise ConflictError("This lead has already been converted")

        # Get default stage for the team
        default_stage = LeadStage.get_default_stage_for_team(incoming_lead.sales_team)
        if not default_stage:
            raise ValidationError("No active stages available for conversion")

        # Prepare opportunity fields from contact or company
        if incoming_lead.contact:
            title = f"Opportunity from {incoming_lead.contact.name}"
            full_name = incoming_lead.contact.name
            email = incoming_lead.contact.email
            phone = incoming_lead.contact.phone or incoming_lead.contact.mobile
            position = incoming_lead.contact.position
        elif incoming_lead.company:
            title = f"Opportunity from {incoming_lead.company.display_name}"
            full_name = ""
            email = incoming_lead.company.company_email or ""
            phone = incoming_lead.company.company_phone or ""
            position = ""
        else:
            title = "Opportunity from Lead"
            full_name = ""
            email = ""
            phone = ""
            position = ""

        # Build notes from the original lead
        notes_parts = ["Converted from incoming lead.", ""]
        notes_parts.append(f"Original Message:\n{incoming_lead.message}")
        if incoming_lead.notes:
            notes_parts.append("")
            notes_parts.append(incoming_lead.notes)
        notes = "\n".join(notes_parts)

        # Create opportunity
        opportunity = Lead.objects.create(
            title=title,
            full_name=full_name,
            email=email,
            phone=phone,
            position=position,
            company=incoming_lead.company,
            company_name=(
                incoming_lead.company.legal_name if incoming_lead.company else ""
            ),
            contact=incoming_lead.contact,
            stage=default_stage,
            assigned_to=incoming_lead.assigned_to or user,
            sales_team=incoming_lead.sales_team,
            created_by=user,
            notes=notes,
        )

        # Update incoming lead status
        incoming_lead.status = "converted"
        incoming_lead.converted_opportunity = opportunity
        incoming_lead.save()

        return opportunity
