"""
CRM app test fixtures using factory_boy.
"""

import factory

from apps.contacts.models import Company, Contact
from apps.crm.models import Lead, LeadActivity, LeadFile, LeadStage, SalesTeam
from core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"crmuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    legal_id = factory.Sequence(lambda n: f"CRM-LID-{n:04d}")
    legal_name = factory.Sequence(lambda n: f"CRM Company {n}")
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"CRM Contact {n}")
    position = "Manager"
    email = factory.LazyAttribute(
        lambda obj: f"{obj.name.lower().replace(' ', '.')}@example.com"
    )
    phone = ""
    mobile = ""


class SalesTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesTeam

    name = factory.Sequence(lambda n: f"Sales Team {n}")
    description = "A test sales team"
    is_active = True


class LeadStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadStage

    name = factory.Sequence(lambda n: f"Stage {n}")
    order = factory.Sequence(lambda n: n)
    color = "#6B7280"
    is_active = True
    is_closed_stage = False
    probability = 50


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    title = factory.Sequence(lambda n: f"Opportunity {n}")
    full_name = factory.Faker("name")
    email = factory.Faker("email")
    phone = ""
    company_name = factory.Faker("company")
    position = ""
    estimated_value = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    source = "website"
    status = "new"
    stage = factory.SubFactory(LeadStageFactory)
    assigned_to = factory.SubFactory(UserFactory)
    created_by = factory.LazyAttribute(lambda obj: obj.assigned_to)


class LeadActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadActivity

    lead = factory.SubFactory(LeadFactory)
    user = factory.SubFactory(UserFactory)
    activity_type = "note"
    subject = factory.Sequence(lambda n: f"Activity {n}")
    description = "Test activity description"


class LeadFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadFile

    lead = factory.SubFactory(LeadFactory)
    file = "leads/files/test_file.pdf"
    filename = factory.Sequence(lambda n: f"document_{n}.pdf")
    description = "Test file"
    uploaded_by = factory.SubFactory(UserFactory)


class LeadTypeLeadFactory(factory.django.DjangoModelFactory):
    """Factory for incoming leads (Lead with status='new')."""

    class Meta:
        model = Lead

    title = factory.Sequence(lambda n: f"Lead {n}")
    message = factory.Faker("paragraph")
    status = "new"
    created_by = factory.SubFactory(UserFactory)
