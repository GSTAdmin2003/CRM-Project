"""
Root conftest.py — shared fixtures for all test modules.

Usage:
    These fixtures are automatically available in all tests under apps/**/tests/.
"""

import pytest
from django.test import RequestFactory

from core.models import Role, User, UserRole


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def role_sales_rep(db):
    return Role.objects.get_or_create(name="Sales Rep", defaults={"description": "Sales Rep"})[0]


@pytest.fixture
def role_sales_manager(db):
    return Role.objects.get_or_create(
        name="Sales Manager", defaults={"description": "Sales Manager"}
    )[0]


@pytest.fixture
def role_sales_executive(db):
    return Role.objects.get_or_create(
        name="Sales Executive", defaults={"description": "Sales Executive"}
    )[0]


@pytest.fixture
def role_owner(db):
    return Role.objects.get_or_create(name="Owner", defaults={"description": "Owner"})[0]


@pytest.fixture
def user_sales_rep(db, role_sales_rep):
    user = User.objects.create_user(
        username="salesrep",
        email="rep@example.com",
        password="testpass123",
    )
    UserRole.objects.create(user=user, role=role_sales_rep)
    return user


@pytest.fixture
def user_sales_manager(db, role_sales_manager):
    user = User.objects.create_user(
        username="salesmanager",
        email="manager@example.com",
        password="testpass123",
    )
    UserRole.objects.create(user=user, role=role_sales_manager)
    return user


@pytest.fixture
def user_sales_executive(db, role_sales_executive):
    user = User.objects.create_user(
        username="salesexec",
        email="exec@example.com",
        password="testpass123",
    )
    UserRole.objects.create(user=user, role=role_sales_executive)
    return user


@pytest.fixture
def admin_user(db, role_owner):
    user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="testpass123",
    )
    UserRole.objects.create(user=user, role=role_owner)
    return user


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user_sales_rep):
    # Use force_login (not force_authenticate) because RoleBasedAccessMiddleware
    # checks request.user.is_authenticated at the Django layer before DRF runs.
    api_client.force_login(user_sales_rep)
    return api_client


@pytest.fixture
def manager_api_client(api_client, user_sales_manager):
    api_client.force_login(user_sales_manager)
    return api_client


@pytest.fixture
def executive_api_client(api_client, user_sales_executive):
    api_client.force_login(user_sales_executive)
    return api_client
