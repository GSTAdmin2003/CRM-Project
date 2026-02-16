"""
Tests for Contacts app models (Company and Contact).
"""

import pytest

from apps.contacts.models import Company, Contact

from .conftest import CompanyFactory, ContactFactory, UserFactory


@pytest.mark.django_db
class TestCompanyModel:
    def test_create_company_with_required_fields(self):
        user = UserFactory()
        company = CompanyFactory(
            legal_id="ABC-001",
            legal_name="Acme Corp",
            created_by=user,
        )
        assert company.pk is not None
        assert company.legal_id == "ABC-001"
        assert company.legal_name == "Acme Corp"
        assert company.created_by == user

    def test_str_returns_legal_name_and_legal_id(self):
        company = CompanyFactory(legal_id="X-100", legal_name="TestCo")
        assert str(company) == "TestCo (X-100)"

    def test_display_name_returns_brand_name_when_set(self):
        company = CompanyFactory(legal_name="Legal Corp", brand_name="Cool Brand")
        assert company.display_name == "Cool Brand"

    def test_display_name_returns_legal_name_when_brand_name_empty(self):
        company = CompanyFactory(legal_name="Legal Corp", brand_name="")
        assert company.display_name == "Legal Corp"

    def test_ordering_by_legal_name(self):
        CompanyFactory(legal_name="Zeta Inc")
        CompanyFactory(legal_name="Alpha LLC")
        CompanyFactory(legal_name="Mu Corp")
        names = list(Company.objects.values_list("legal_name", flat=True))
        assert names == sorted(names)

    def test_legal_id_is_unique(self):
        CompanyFactory(legal_id="UNIQUE-001")
        with pytest.raises(Exception):
            CompanyFactory(legal_id="UNIQUE-001")

    def test_created_at_and_updated_at_auto_set(self):
        company = CompanyFactory()
        assert company.created_at is not None
        assert company.updated_at is not None

    def test_set_default_favorite_contact_with_contacts(self):
        company = CompanyFactory()
        # The post_save signal on Contact already sets favorite for first contact,
        # so we clear it to test set_default_favorite_contact explicitly.
        contact = ContactFactory(company=company)
        company.favorite_contact = None
        Company.objects.filter(pk=company.pk).update(favorite_contact=None)
        company.refresh_from_db()
        assert company.favorite_contact is None

        company.set_default_favorite_contact()
        company.refresh_from_db()
        assert company.favorite_contact == contact

    def test_set_default_favorite_contact_no_contacts(self):
        company = CompanyFactory()
        company.favorite_contact = None
        Company.objects.filter(pk=company.pk).update(favorite_contact=None)
        company.refresh_from_db()

        company.set_default_favorite_contact()
        company.refresh_from_db()
        assert company.favorite_contact is None

    def test_ensure_favorite_contact_clears_when_no_contacts(self):
        company = CompanyFactory()
        # Manually set a dangling favorite (simulating deleted contact scenario)
        assert company.contacts.count() == 0
        company.ensure_favorite_contact()
        company.refresh_from_db()
        assert company.favorite_contact is None

    def test_ensure_favorite_contact_sets_first_when_invalid(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        ContactFactory(company=company, name="Beta")

        # Set favorite to None, then ensure reassigns
        Company.objects.filter(pk=company.pk).update(favorite_contact=None)
        company.refresh_from_db()
        company.ensure_favorite_contact()
        company.refresh_from_db()
        # Should pick first by ordering (name), which is Alpha
        assert company.favorite_contact == c1

    def test_save_auto_sets_favorite_contact(self):
        """Company.save() auto-sets favorite_contact if none exists and contacts are present."""
        company = CompanyFactory()
        contact = ContactFactory(company=company)
        # The signal already sets it; verify it persisted
        company.refresh_from_db()
        assert company.favorite_contact == contact

    def test_save_does_not_overwrite_existing_favorite(self):
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="First")
        c2 = ContactFactory(company=company, name="Second")
        company.favorite_contact = c2
        company.save()
        company.refresh_from_db()
        assert company.favorite_contact == c2


@pytest.mark.django_db
class TestContactModel:
    def test_create_contact_with_required_fields(self):
        company = CompanyFactory()
        contact = ContactFactory(
            company=company,
            name="Jane Doe",
            position="CTO",
        )
        assert contact.pk is not None
        assert contact.name == "Jane Doe"
        assert contact.position == "CTO"
        assert contact.company == company

    def test_str_representation(self):
        company = CompanyFactory(legal_name="TestCo", brand_name="")
        contact = ContactFactory(company=company, name="John Smith", position="CEO")
        assert str(contact) == "John Smith - CEO at TestCo"

    def test_str_uses_display_name_brand(self):
        company = CompanyFactory(legal_name="Legal Name", brand_name="Brand Name")
        contact = ContactFactory(company=company, name="John Smith", position="CEO")
        assert str(contact) == "John Smith - CEO at Brand Name"

    def test_ordering_by_name(self):
        company = CompanyFactory()
        ContactFactory(company=company, name="Zara")
        ContactFactory(company=company, name="Alice")
        ContactFactory(company=company, name="Mike")
        names = list(company.contacts.values_list("name", flat=True))
        assert names == sorted(names)

    def test_created_at_and_updated_at_auto_set(self):
        contact = ContactFactory()
        assert contact.created_at is not None
        assert contact.updated_at is not None

    def test_signal_sets_favorite_on_first_contact_creation(self):
        """post_save signal auto-sets first contact as favorite."""
        company = CompanyFactory()
        assert company.favorite_contact is None
        contact = ContactFactory(company=company)
        company.refresh_from_db()
        assert company.favorite_contact == contact

    def test_signal_does_not_overwrite_existing_favorite(self):
        """post_save signal should not overwrite if a favorite already exists."""
        company = CompanyFactory()
        c1 = ContactFactory(company=company)
        company.refresh_from_db()
        assert company.favorite_contact == c1

        c2 = ContactFactory(company=company)
        company.refresh_from_db()
        # Favorite should still be c1
        assert company.favorite_contact == c1

    def test_cascade_delete_removes_contacts(self):
        company = CompanyFactory()
        ContactFactory(company=company)
        ContactFactory(company=company)
        company_pk = company.pk
        assert Contact.objects.filter(company_id=company_pk).count() == 2
        company.delete()
        assert Contact.objects.filter(company_id=company_pk).count() == 0
