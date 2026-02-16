"""
Tests for Contacts app service layer (CompanyService and ContactService).
"""

import pytest

from apps.contacts.models import Company, Contact
from apps.contacts.services import CompanyService, ContactService
from core.exceptions import NotFoundError, ValidationError

from .conftest import CompanyFactory, ContactFactory, UserFactory


# =============================================================================
# CompanyService
# =============================================================================


@pytest.mark.django_db
class TestCompanyServiceListCompanies:
    def test_list_companies_returns_all(self):
        CompanyFactory(legal_name="Alpha")
        CompanyFactory(legal_name="Beta")
        CompanyFactory(legal_name="Gamma")
        qs = CompanyService.list_companies()
        assert qs.count() == 3

    def test_list_companies_ordered_by_legal_name(self):
        CompanyFactory(legal_name="Zeta")
        CompanyFactory(legal_name="Alpha")
        names = list(CompanyService.list_companies().values_list("legal_name", flat=True))
        assert names == ["Alpha", "Zeta"]

    def test_list_companies_with_search_by_legal_name(self):
        CompanyFactory(legal_name="Acme Corp")
        CompanyFactory(legal_name="Beta Inc")
        qs = CompanyService.list_companies(search="acme")
        assert qs.count() == 1
        assert qs.first().legal_name == "Acme Corp"

    def test_list_companies_with_search_by_brand_name(self):
        CompanyFactory(legal_name="Legal Co", brand_name="Cool Brand")
        CompanyFactory(legal_name="Other Co")
        qs = CompanyService.list_companies(search="Cool")
        assert qs.count() == 1

    def test_list_companies_with_search_by_legal_id(self):
        CompanyFactory(legal_id="SEARCH-ME")
        CompanyFactory(legal_id="DONT-FIND")
        qs = CompanyService.list_companies(search="SEARCH-ME")
        assert qs.count() == 1

    def test_list_companies_with_search_by_industry(self):
        CompanyFactory(industry="Technology")
        CompanyFactory(industry="Healthcare")
        qs = CompanyService.list_companies(search="Tech")
        assert qs.count() == 1

    def test_list_companies_with_search_by_category(self):
        CompanyFactory(category="Enterprise")
        CompanyFactory(category="SMB")
        qs = CompanyService.list_companies(search="Enterprise")
        assert qs.count() == 1

    def test_list_companies_empty_search_returns_all(self):
        CompanyFactory()
        CompanyFactory()
        qs = CompanyService.list_companies(search="")
        assert qs.count() == 2


@pytest.mark.django_db
class TestCompanyServiceGetCompanyOrRaise:
    def test_get_company_success(self):
        company = CompanyFactory()
        result = CompanyService.get_company_or_raise(pk=company.pk)
        assert result.pk == company.pk

    def test_get_company_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            CompanyService.get_company_or_raise(pk=99999)


@pytest.mark.django_db
class TestCompanyServiceCreateCompany:
    def test_create_company_success(self):
        user = UserFactory()
        company = CompanyService.create_company(
            legal_id="NEW-001",
            legal_name="New Company",
            created_by=user,
        )
        assert company.pk is not None
        assert company.legal_id == "NEW-001"
        assert company.legal_name == "New Company"
        assert company.created_by == user
        assert company.updated_by == user

    def test_create_company_with_optional_fields(self):
        user = UserFactory()
        company = CompanyService.create_company(
            legal_id="OPT-001",
            legal_name="Optional Fields Co",
            created_by=user,
            brand_name="The Brand",
            company_phone="555-0100",
            company_email="info@example.com",
            industry="Tech",
            category="Enterprise",
        )
        assert company.brand_name == "The Brand"
        assert company.company_phone == "555-0100"
        assert company.company_email == "info@example.com"
        assert company.industry == "Tech"
        assert company.category == "Enterprise"

    def test_create_company_missing_legal_id_raises(self):
        user = UserFactory()
        with pytest.raises(ValidationError, match="Legal ID is required"):
            CompanyService.create_company(
                legal_id="",
                legal_name="Some Company",
                created_by=user,
            )

    def test_create_company_whitespace_legal_id_raises(self):
        user = UserFactory()
        with pytest.raises(ValidationError, match="Legal ID is required"):
            CompanyService.create_company(
                legal_id="   ",
                legal_name="Some Company",
                created_by=user,
            )

    def test_create_company_missing_legal_name_raises(self):
        user = UserFactory()
        with pytest.raises(ValidationError, match="Legal Name is required"):
            CompanyService.create_company(
                legal_id="VALID-001",
                legal_name="",
                created_by=user,
            )

    def test_create_company_duplicate_legal_id_raises(self):
        user = UserFactory()
        CompanyFactory(legal_id="DUP-001")
        with pytest.raises(ValidationError, match="already exists"):
            CompanyService.create_company(
                legal_id="DUP-001",
                legal_name="Duplicate Co",
                created_by=user,
            )

    def test_create_company_strips_whitespace(self):
        user = UserFactory()
        company = CompanyService.create_company(
            legal_id="  STRIP-001  ",
            legal_name="  Stripped Name  ",
            created_by=user,
        )
        assert company.legal_id == "STRIP-001"
        assert company.legal_name == "Stripped Name"


@pytest.mark.django_db
class TestCompanyServiceUpdateCompany:
    def test_update_company_success(self):
        user = UserFactory()
        company = CompanyFactory()
        updated = CompanyService.update_company(
            pk=company.pk,
            updated_by=user,
            legal_name="Updated Name",
            brand_name="New Brand",
        )
        assert updated.legal_name == "Updated Name"
        assert updated.brand_name == "New Brand"
        assert updated.updated_by == user

    def test_update_company_ignores_disallowed_fields(self):
        user = UserFactory()
        company = CompanyFactory()
        original_created_by = company.created_by
        CompanyService.update_company(
            pk=company.pk,
            updated_by=user,
            created_by=user,  # disallowed field
        )
        company.refresh_from_db()
        assert company.created_by == original_created_by

    def test_update_company_not_found_raises(self):
        user = UserFactory()
        with pytest.raises(NotFoundError, match="not found"):
            CompanyService.update_company(pk=99999, updated_by=user, legal_name="X")


@pytest.mark.django_db
class TestCompanyServiceDeleteCompany:
    def test_delete_company_success(self):
        company = CompanyFactory(legal_name="To Delete")
        pk = company.pk
        name = CompanyService.delete_company(pk=pk)
        assert name == "To Delete"
        assert not Company.objects.filter(pk=pk).exists()

    def test_delete_company_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            CompanyService.delete_company(pk=99999)


@pytest.mark.django_db
class TestCompanyServiceGetDashboardContext:
    def test_get_dashboard_context(self):
        CompanyFactory()
        CompanyFactory()
        company = CompanyFactory()
        ContactFactory(company=company)

        ctx = CompanyService.get_dashboard_context()
        assert ctx["companies_count"] == 3
        assert ctx["contacts_count"] == 1
        assert len(ctx["recent_companies"]) <= 5

    def test_get_dashboard_context_empty(self):
        ctx = CompanyService.get_dashboard_context()
        assert ctx["companies_count"] == 0
        assert ctx["contacts_count"] == 0
        assert len(ctx["recent_companies"]) == 0


# =============================================================================
# ContactService
# =============================================================================


@pytest.mark.django_db
class TestContactServiceListContactsForCompany:
    def test_list_contacts_for_company_success(self):
        company = CompanyFactory()
        ContactFactory(company=company, name="Contact A")
        ContactFactory(company=company, name="Contact B")
        # Contact for another company
        ContactFactory()

        qs = ContactService.list_contacts_for_company(company_pk=company.pk)
        assert qs.count() == 2

    def test_list_contacts_for_company_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.list_contacts_for_company(company_pk=99999)


@pytest.mark.django_db
class TestContactServiceGetContactOrRaise:
    def test_get_contact_success(self):
        contact = ContactFactory()
        result = ContactService.get_contact_or_raise(pk=contact.pk)
        assert result.pk == contact.pk
        # Verify select_related loaded company
        assert result.company is not None

    def test_get_contact_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.get_contact_or_raise(pk=99999)


@pytest.mark.django_db
class TestContactServiceCreateContact:
    def test_create_contact_success(self):
        company = CompanyFactory()
        contact = ContactService.create_contact(
            company_pk=company.pk,
            name="Jane Doe",
            position="CTO",
            email="jane@example.com",
            phone="555-0101",
        )
        assert contact.pk is not None
        assert contact.name == "Jane Doe"
        assert contact.position == "CTO"
        assert contact.company == company

    def test_create_contact_missing_name_raises(self):
        company = CompanyFactory()
        with pytest.raises(ValidationError, match="name is required"):
            ContactService.create_contact(
                company_pk=company.pk,
                name="",
                position="CEO",
            )

    def test_create_contact_whitespace_name_raises(self):
        company = CompanyFactory()
        with pytest.raises(ValidationError, match="name is required"):
            ContactService.create_contact(
                company_pk=company.pk,
                name="   ",
                position="CEO",
            )

    def test_create_contact_missing_position_raises(self):
        company = CompanyFactory()
        with pytest.raises(ValidationError, match="position is required"):
            ContactService.create_contact(
                company_pk=company.pk,
                name="John Doe",
                position="",
            )

    def test_create_contact_company_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.create_contact(
                company_pk=99999,
                name="John Doe",
                position="CEO",
            )

    def test_create_contact_strips_whitespace(self):
        company = CompanyFactory()
        contact = ContactService.create_contact(
            company_pk=company.pk,
            name="  Spaced Name  ",
            position="  Spaced Position  ",
        )
        assert contact.name == "Spaced Name"
        assert contact.position == "Spaced Position"

    def test_create_first_contact_auto_sets_favorite(self):
        company = CompanyFactory()
        contact = ContactService.create_contact(
            company_pk=company.pk,
            name="First Contact",
            position="CEO",
        )
        company.refresh_from_db()
        assert company.favorite_contact == contact


@pytest.mark.django_db
class TestContactServiceUpdateContact:
    def test_update_contact_success(self):
        contact = ContactFactory(name="Old Name", position="Old Position")
        updated = ContactService.update_contact(
            pk=contact.pk,
            name="New Name",
            position="New Position",
            email="new@example.com",
        )
        assert updated.name == "New Name"
        assert updated.position == "New Position"
        assert updated.email == "new@example.com"

    def test_update_contact_ignores_disallowed_fields(self):
        company1 = CompanyFactory()
        company2 = CompanyFactory()
        contact = ContactFactory(company=company1)
        ContactService.update_contact(
            pk=contact.pk,
            company=company2,  # disallowed
        )
        contact.refresh_from_db()
        assert contact.company == company1

    def test_update_contact_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.update_contact(pk=99999, name="X")


@pytest.mark.django_db
class TestContactServiceDeleteContact:
    def test_delete_contact_success(self):
        contact = ContactFactory(name="Delete Me")
        pk = contact.pk
        result = ContactService.delete_contact(pk=pk)
        assert result["contact_name"] == "Delete Me"
        assert not Contact.objects.filter(pk=pk).exists()

    def test_delete_contact_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.delete_contact(pk=99999)

    def test_delete_favorite_contact_reassigns_favorite(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        c2 = ContactFactory(company=company, name="Beta")
        # Make c1 the favorite
        company.favorite_contact = c1
        company.save(update_fields=["favorite_contact"])

        result = ContactService.delete_contact(pk=c1.pk)
        company.refresh_from_db()
        assert company.favorite_contact == c2
        assert result["new_favorite_name"] == "Beta"

    def test_delete_only_contact_clears_favorite(self):
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        company.refresh_from_db()
        assert company.favorite_contact == contact

        result = ContactService.delete_contact(pk=contact.pk)
        company.refresh_from_db()
        # After deleting the only contact, favorite should be None.
        # The service does not explicitly clear favorite when it's the last contact,
        # but delete cascading behavior + ensure_favorite should handle it.
        assert result["new_favorite_name"] is None

    def test_delete_non_favorite_contact_keeps_favorite(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        c2 = ContactFactory(company=company, name="Beta")
        company.favorite_contact = c1
        company.save(update_fields=["favorite_contact"])

        result = ContactService.delete_contact(pk=c2.pk)
        company.refresh_from_db()
        assert company.favorite_contact == c1
        assert result["new_favorite_name"] is None


@pytest.mark.django_db
class TestContactServiceToggleFavorite:
    def test_toggle_favorite_set_new_favorite(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        c2 = ContactFactory(company=company, name="Beta")
        # c1 is favorite (first contact created)
        company.refresh_from_db()
        assert company.favorite_contact == c1

        result = ContactService.toggle_favorite(company_pk=company.pk, contact_pk=c2.pk)
        company.refresh_from_db()
        assert company.favorite_contact == c2
        assert result["is_favorite"] is True
        assert "Beta" in result["message"]

    def test_toggle_favorite_off_reassigns_to_other(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        c2 = ContactFactory(company=company, name="Beta")
        company.favorite_contact = c1
        company.save(update_fields=["favorite_contact"])

        # Toggle c1 off -- should reassign to c2
        result = ContactService.toggle_favorite(company_pk=company.pk, contact_pk=c1.pk)
        company.refresh_from_db()
        assert company.favorite_contact != c1
        assert result["is_favorite"] is False

    def test_toggle_favorite_only_contact_stays_favorite(self):
        company = CompanyFactory()
        contact = ContactFactory(company=company, name="Only One")
        company.refresh_from_db()
        assert company.favorite_contact == contact

        result = ContactService.toggle_favorite(
            company_pk=company.pk, contact_pk=contact.pk
        )
        company.refresh_from_db()
        assert company.favorite_contact == contact
        assert result["is_favorite"] is True
        assert "remains favorite" in result["message"]

    def test_toggle_favorite_company_not_found_raises(self):
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.toggle_favorite(company_pk=99999, contact_pk=1)

    def test_toggle_favorite_contact_not_found_raises(self):
        company = CompanyFactory()
        with pytest.raises(NotFoundError, match="not found"):
            ContactService.toggle_favorite(company_pk=company.pk, contact_pk=99999)
