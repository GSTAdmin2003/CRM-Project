"""
CompanyService -- all business logic for Company CRUD.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import Q, QuerySet

from core.exceptions import NotFoundError, ValidationError

from ..models import Company


class CompanyService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_companies(*, search: str = "") -> QuerySet[Company]:
        """
        Return a queryset of companies, optionally filtered by search term.

        Args:
            search: Optional search string to filter by legal_name, brand_name,
                    legal_id, industry, or category.
        """
        qs = Company.objects.all()

        if search:
            qs = qs.filter(
                Q(legal_name__icontains=search)
                | Q(brand_name__icontains=search)
                | Q(legal_id__icontains=search)
                | Q(industry__icontains=search)
                | Q(category__icontains=search)
            )

        return qs.order_by("legal_name")

    @staticmethod
    def get_company_or_raise(*, pk: int) -> Company:
        """Fetch a company by PK or raise NotFoundError."""
        try:
            return Company.objects.get(pk=pk)
        except Company.DoesNotExist:
            raise NotFoundError(f"Company with id {pk} not found")

    @staticmethod
    def get_dashboard_context() -> dict:
        """Return summary statistics for the contacts dashboard."""
        from ..models import Contact

        return {
            "companies_count": Company.objects.count(),
            "contacts_count": Contact.objects.count(),
            "recent_companies": Company.objects.order_by("-created_at")[:5],
        }

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_company(
        *,
        legal_id: str,
        legal_name: str,
        created_by,
        brand_name: str = "",
        company_phone: str = "",
        company_mobile: str = "",
        company_email: str = "",
        industry: str = "",
        category: str = "",
    ) -> Company:
        """Create a new company."""
        if not legal_id or not legal_id.strip():
            raise ValidationError("Legal ID is required")
        if not legal_name or not legal_name.strip():
            raise ValidationError("Legal Name is required")

        if Company.objects.filter(legal_id=legal_id.strip()).exists():
            raise ValidationError(f"A company with Legal ID '{legal_id.strip()}' already exists")

        company = Company.objects.create(
            legal_id=legal_id.strip(),
            legal_name=legal_name.strip(),
            brand_name=brand_name,
            company_phone=company_phone,
            company_mobile=company_mobile,
            company_email=company_email,
            industry=industry,
            category=category,
            created_by=created_by,
            updated_by=created_by,
        )
        return company

    @staticmethod
    @transaction.atomic
    def update_company(*, pk: int, updated_by, **fields) -> Company:
        """
        Update an existing company. Only allowed fields are applied.

        Args:
            pk: Company primary key.
            updated_by: The user performing the update.
            **fields: Field name/value pairs to update.
        """
        company = CompanyService.get_company_or_raise(pk=pk)

        allowed_fields = {
            "legal_id",
            "legal_name",
            "brand_name",
            "company_phone",
            "company_mobile",
            "company_email",
            "industry",
            "category",
        }
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(company, key, value)

        company.updated_by = updated_by
        company.save()
        return company

    @staticmethod
    @transaction.atomic
    def delete_company(*, pk: int) -> str:
        """
        Delete a company and return its name for confirmation messaging.

        Returns:
            The legal_name of the deleted company.
        """
        company = CompanyService.get_company_or_raise(pk=pk)
        company_name = company.legal_name
        company.delete()
        return company_name
