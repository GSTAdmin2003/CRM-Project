"""
Activities app test fixtures using factory_boy.
"""

import factory
from datetime import date, timedelta

from apps.activities.models import Activity, ActivityType
from apps.crm.models import Lead, LeadStage, SalesTeam
from core.models import User


class ActivityTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActivityType

    name = factory.Sequence(lambda n: f"Activity Type {n}")
    icon = "fas fa-phone"
    color = "#6366f1"
    is_active = True


class SalesTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesTeam

    name = factory.Sequence(lambda n: f"Team {n}")
    is_active = True


class LeadStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadStage

    name = factory.Sequence(lambda n: f"Stage {n}")
    order = factory.Sequence(lambda n: n)
    is_active = True
    probability = 50


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    title = factory.Sequence(lambda n: f"Opportunity {n}")
    full_name = factory.Faker("name")
    stage = factory.SubFactory(LeadStageFactory)
    assigned_to = factory.LazyAttribute(lambda o: UserFactory())
    created_by = factory.LazyAttribute(lambda o: o.assigned_to)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity

    lead = factory.SubFactory(LeadFactory)
    activity_type = factory.SubFactory(ActivityTypeFactory)
    title = factory.Sequence(lambda n: f"Activity {n}")
    description = "Test activity description"
    scheduled_date = factory.LazyFunction(lambda: date.today() + timedelta(days=1))
    status = "planned"
    assigned_to = factory.LazyAttribute(lambda o: o.lead.assigned_to)
    created_by = factory.LazyAttribute(lambda o: o.lead.assigned_to)
