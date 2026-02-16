"""
Tests for Contacts DRF API endpoints (CompanyViewSet and ContactViewSet).

Note: We use api_client.force_login() instead of force_authenticate() because
the RoleBasedAccessMiddleware checks request.user.is_authenticated at the Django
middleware layer, before DRF's authentication runs.
"""

import pytest

from django.urls import reverse
from rest_framework import status

from apps.contacts.models import Company, Contact

from .conftest import CompanyFactory, ContactFactory, UserFactory


# =============================================================================
# CompanyViewSet API Tests
# =============================================================================


@pytest.mark.django_db
class TestCompanyListAPI:
    def test_list_requires_auth(self, api_client):
        url = reverse("contacts:company-api-list")
        response = api_client.get(url)
        # Middleware redirects to login (302) or DRF returns 403
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_returns_companies(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CompanyFactory(legal_name="Alpha Corp")
        CompanyFactory(legal_name="Beta Inc")

        url = reverse("contacts:company-api-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Paginated response
        results = response.data.get("results", response.data)
        names = [c["legal_name"] for c in results]
        assert "Alpha Corp" in names
        assert "Beta Inc" in names

    def test_list_with_search_filter(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CompanyFactory(legal_name="Acme Corp")
        CompanyFactory(legal_name="Other Inc")

        url = reverse("contacts:company-api-list")
        response = api_client.get(url, {"search": "Acme"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["legal_name"] == "Acme Corp"


@pytest.mark.django_db
class TestCompanyCreateAPI:
    def test_create_company_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-list")
        data = {
            "legal_id": "API-001",
            "legal_name": "API Created Company",
            "brand_name": "API Brand",
            "industry": "Technology",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["legal_id"] == "API-001"
        assert response.data["legal_name"] == "API Created Company"
        assert Company.objects.filter(legal_id="API-001").exists()

    def test_create_company_missing_legal_id_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-list")
        data = {
            "legal_name": "No ID Company",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_company_missing_legal_name_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-list")
        data = {
            "legal_id": "VALID-001",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_company_duplicate_legal_id_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        CompanyFactory(legal_id="DUP-API")

        url = reverse("contacts:company-api-list")
        data = {
            "legal_id": "DUP-API",
            "legal_name": "Duplicate Company",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCompanyRetrieveAPI:
    def test_retrieve_company_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory(legal_name="Detail Corp")

        url = reverse("contacts:company-api-detail", kwargs={"pk": company.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["legal_name"] == "Detail Corp"
        assert response.data["id"] == company.pk

    def test_retrieve_company_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-detail", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCompanyUpdateAPI:
    def test_update_company_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory(legal_name="Old Name", legal_id="UPD-001")

        url = reverse("contacts:company-api-detail", kwargs={"pk": company.pk})
        data = {
            "legal_id": "UPD-001",
            "legal_name": "Updated Name",
            "brand_name": "New Brand",
        }
        response = api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["legal_name"] == "Updated Name"
        assert response.data["brand_name"] == "New Brand"

    def test_update_company_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-detail", kwargs={"pk": 99999})
        data = {
            "legal_id": "X",
            "legal_name": "X",
        }
        response = api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCompanyDeleteAPI:
    def test_delete_company_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()
        pk = company.pk

        url = reverse("contacts:company-api-detail", kwargs={"pk": pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=pk).exists()

    def test_delete_company_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:company-api-detail", kwargs={"pk": 99999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# ContactViewSet API Tests
# =============================================================================


@pytest.mark.django_db
class TestContactListAPI:
    def test_list_requires_auth(self, api_client):
        url = reverse("contacts:contact-api-list")
        response = api_client.get(url)
        assert response.status_code in (
            status.HTTP_302_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_returns_contacts(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()
        ContactFactory(company=company, name="Alice")
        ContactFactory(company=company, name="Bob")

        url = reverse("contacts:contact-api-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        names = [c["name"] for c in results]
        assert "Alice" in names
        assert "Bob" in names

    def test_list_filter_by_company_id(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company1 = CompanyFactory()
        company2 = CompanyFactory()
        ContactFactory(company=company1, name="C1 Contact")
        ContactFactory(company=company2, name="C2 Contact")

        url = reverse("contacts:contact-api-list")
        response = api_client.get(url, {"company_id": company1.pk})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        names = [c["name"] for c in results]
        assert "C1 Contact" in names
        assert "C2 Contact" not in names


@pytest.mark.django_db
class TestContactCreateAPI:
    def test_create_contact_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()

        url = reverse("contacts:contact-api-list")
        data = {
            "company_id": company.pk,
            "name": "New Contact",
            "position": "Manager",
            "email": "new@example.com",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Contact"
        assert response.data["position"] == "Manager"
        assert Contact.objects.filter(name="New Contact").exists()

    def test_create_contact_missing_company_id_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:contact-api-list")
        data = {
            "name": "No Company Contact",
            "position": "CEO",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_contact_invalid_company_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:contact-api-list")
        data = {
            "company_id": 99999,
            "name": "Ghost Contact",
            "position": "CEO",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_contact_missing_name_returns_400(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()

        url = reverse("contacts:contact-api-list")
        data = {
            "company_id": company.pk,
            "position": "CEO",
        }
        response = api_client.post(url, data, format="json")

        # Serializer enforces name is required
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestContactRetrieveAPI:
    def test_retrieve_contact_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        contact = ContactFactory(name="Detail Contact")

        url = reverse("contacts:contact-api-detail", kwargs={"pk": contact.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Detail Contact"
        assert response.data["id"] == contact.pk

    def test_retrieve_contact_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:contact-api-detail", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestContactDeleteAPI:
    def test_delete_contact_success(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        contact = ContactFactory()
        pk = contact.pk

        url = reverse("contacts:contact-api-detail", kwargs={"pk": pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Contact.objects.filter(pk=pk).exists()

    def test_delete_contact_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:contact-api-detail", kwargs={"pk": 99999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestContactToggleFavoriteAPI:
    def test_toggle_favorite_set_favorite(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()
        c1 = ContactFactory(company=company, name="Alpha")
        c2 = ContactFactory(company=company, name="Beta")
        # c1 is auto-favorite
        company.refresh_from_db()
        assert company.favorite_contact == c1

        url = reverse("contacts:contact-api-toggle-favorite", kwargs={"pk": c2.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_favorite"] is True
        company.refresh_from_db()
        assert company.favorite_contact == c2

    def test_toggle_favorite_only_contact_stays(self, api_client):
        user = UserFactory()
        api_client.force_login(user)
        company = CompanyFactory()
        contact = ContactFactory(company=company)

        url = reverse("contacts:contact-api-toggle-favorite", kwargs={"pk": contact.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_favorite"] is True
        assert "remains favorite" in response.data["message"]

    def test_toggle_favorite_contact_not_found_returns_404(self, api_client):
        user = UserFactory()
        api_client.force_login(user)

        url = reverse("contacts:contact-api-toggle-favorite", kwargs={"pk": 99999})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
