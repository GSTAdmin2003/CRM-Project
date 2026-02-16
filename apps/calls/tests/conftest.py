"""
Calls app test fixtures using factory_boy.
"""

from unittest.mock import MagicMock, patch

import factory
import pytest

from apps.calls.models import Call, CallLog, CallRecording, SIPSettings
from apps.contacts.models import Company, Contact
from apps.crm.models import Lead, LeadStage, SalesTeam
from core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"calluser{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    legal_id = factory.Sequence(lambda n: f"CALL-LID-{n:04d}")
    legal_name = factory.Sequence(lambda n: f"Call Company {n}")
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda o: o.created_by)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Call Contact {n}")
    position = "Manager"
    email = factory.LazyAttribute(
        lambda o: f"{o.name.lower().replace(' ', '.')}@example.com"
    )


class SalesTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesTeam

    name = factory.Sequence(lambda n: f"Call Team {n}")
    is_active = True


class LeadStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadStage

    name = factory.Sequence(lambda n: f"Call Stage {n}")
    order = factory.Sequence(lambda n: n)
    is_active = True
    probability = 50


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    title = factory.Sequence(lambda n: f"Call Opportunity {n}")
    full_name = factory.Faker("name")
    stage = factory.SubFactory(LeadStageFactory)
    assigned_to = factory.SubFactory(UserFactory)
    created_by = factory.LazyAttribute(lambda o: o.assigned_to)


class CallFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Call

    asterisk_channel_id = factory.Sequence(lambda n: f"channel-{n:06d}")
    asterisk_uniqueid = factory.Sequence(lambda n: f"uniqueid-{n}")
    direction = "outbound"
    status = "initiated"
    from_number = "100"
    to_number = factory.Sequence(lambda n: f"+155500{n:04d}")
    user = factory.SubFactory(UserFactory)


class CallLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CallLog

    call = factory.SubFactory(CallFactory)
    event = "initiated"
    data = factory.LazyFunction(dict)


class CallRecordingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CallRecording

    call = factory.SubFactory(CallFactory)
    file = "call_recordings/2025/01/test.wav"
    duration = 120
    file_size = 1048576  # 1 MB


class SIPSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SIPSettings

    user = factory.SubFactory(UserFactory)
    server_ip = "192.168.1.100"
    server_port = 5060
    username = factory.Sequence(lambda n: f"sip_user_{n}")
    _password = "encrypted_placeholder"
    caller_id = factory.Sequence(lambda n: f"+1555000{n:04d}")
    is_active = True
    registration_status = "registered"


@pytest.fixture
def mock_ari_client():
    """Patch the global ari_client singleton used by CallService."""
    with patch("apps.calls.services.call_service.ari_client") as mock_ari:
        yield mock_ari
