"""
ContactService -- all business logic for Contact CRUD and favorite toggling.

Rules:
- Stateless (static methods only)
- No request/response objects
- Raises core.exceptions (never HTTP exceptions)
- Uses @transaction.atomic for multi-step operations
"""

from django.db import transaction
from django.db.models import QuerySet

from core.exceptions import NotFoundError, ValidationError

from ..models import Company, Contact


class ContactService:
    # -- Queries ---------------------------------------------------------------

    @staticmethod
    def list_contacts_for_company(*, company_pk: int) -> QuerySet[Contact]:
        """Return all contacts belonging to a company."""
        try:
            company = Company.objects.get(pk=company_pk)
        except Company.DoesNotExist:
            raise NotFoundError(f"Company with id {company_pk} not found")

        return company.contacts.all()

    @staticmethod
    def get_contact_or_raise(*, pk: int) -> Contact:
        """Fetch a contact by PK or raise NotFoundError."""
        try:
            return Contact.objects.select_related("company").get(pk=pk)
        except Contact.DoesNotExist:
            raise NotFoundError(f"Contact with id {pk} not found")

    # -- Commands --------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_contact(
        *,
        company_pk: int,
        name: str,
        position: str,
        email: str = "",
        phone: str = "",
        mobile: str = "",
        preferred_language: str = "",
    ) -> Contact:
        """Create a new contact for the given company."""
        try:
            company = Company.objects.get(pk=company_pk)
        except Company.DoesNotExist:
            raise NotFoundError(f"Company with id {company_pk} not found")

        if not name or not name.strip():
            raise ValidationError("Contact name is required")
        if not position or not position.strip():
            raise ValidationError("Contact position is required")

        contact = Contact.objects.create(
            company=company,
            name=name.strip(),
            position=position.strip(),
            email=email,
            phone=phone,
            mobile=mobile,
            preferred_language=preferred_language,
        )
        return contact

    @staticmethod
    @transaction.atomic
    def update_contact(*, pk: int, **fields) -> Contact:
        """
        Update an existing contact. Only allowed fields are applied.

        Args:
            pk: Contact primary key.
            **fields: Field name/value pairs to update.
        """
        contact = ContactService.get_contact_or_raise(pk=pk)

        allowed_fields = {"name", "position", "email", "phone", "mobile", "preferred_language"}
        for key, value in fields.items():
            if key in allowed_fields:
                setattr(contact, key, value)

        contact.save()
        return contact

    @staticmethod
    @transaction.atomic
    def delete_contact(*, pk: int) -> dict:
        """
        Delete a contact. If it was the company's favorite, reassign favorite.

        Returns:
            dict with 'contact_name', 'company_pk', and optional 'new_favorite_name'.
        """
        contact = ContactService.get_contact_or_raise(pk=pk)
        company = contact.company
        contact_name = contact.name
        result = {
            "contact_name": contact_name,
            "company_pk": company.pk,
            "new_favorite_name": None,
        }

        is_favorite = company.favorite_contact == contact

        if is_favorite:
            other_contacts = company.contacts.exclude(pk=contact.pk)
            if other_contacts.exists():
                new_favorite = other_contacts.first()
                company.favorite_contact = new_favorite
                company.save(update_fields=["favorite_contact"])
                result["new_favorite_name"] = new_favorite.name

        contact.delete()
        return result

    @staticmethod
    @transaction.atomic
    def toggle_favorite(*, company_pk: int, contact_pk: int) -> dict:
        """
        Toggle favorite contact for a company.

        Returns:
            dict with 'is_favorite' (bool) and 'message' (str).
        """
        try:
            company = Company.objects.get(pk=company_pk)
        except Company.DoesNotExist:
            raise NotFoundError(f"Company with id {company_pk} not found")

        try:
            contact = Contact.objects.get(pk=contact_pk, company=company)
        except Contact.DoesNotExist:
            raise NotFoundError(
                f"Contact with id {contact_pk} not found for company {company_pk}"
            )

        if company.favorite_contact == contact:
            # Try to set another contact as favorite
            other_contacts = company.contacts.exclude(pk=contact.pk)
            if other_contacts.exists():
                new_fav = other_contacts.first()
                company.favorite_contact = new_fav
                message = f"Set {new_fav.name} as favorite contact"
            else:
                # Only contact -- stays favorite
                message = f"{contact.name} remains favorite as it's the only contact"
        else:
            company.favorite_contact = contact
            message = f"Set {contact.name} as favorite contact"

        company.save(update_fields=["favorite_contact"])

        return {
            "is_favorite": company.favorite_contact == contact,
            "message": message,
        }
