"""
Contacts app test fixtures using factory_boy.
"""

import factory

from apps.contacts.models import Company, Contact
from core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    legal_id = factory.Sequence(lambda n: f"LID-{n:04d}")
    legal_name = factory.Sequence(lambda n: f"Company {n}")
    brand_name = ""
    company_phone = ""
    company_mobile = ""
    company_email = ""
    industry = ""
    category = ""
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Contact {n}")
    position = factory.Faker("job")
    email = factory.LazyAttribute(
        lambda obj: f"{obj.name.lower().replace(' ', '.')}@example.com"
    )
    phone = ""
    mobile = ""
