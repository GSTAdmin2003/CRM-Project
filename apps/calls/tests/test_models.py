"""
Tests for Calls app models (Call, CallLog, CallRecording, SIPSettings).
"""

import pytest

from apps.calls.models import Call, CallLog, CallRecording, SIPSettings

from .conftest import (
    CallFactory,
    CallLogFactory,
    CallRecordingFactory,
    SIPSettingsFactory,
    UserFactory,
)


# =============================================================================
# Call Model
# =============================================================================


@pytest.mark.django_db
class TestCallModel:
    def test_create_call_with_required_fields(self):
        user = UserFactory()
        call = CallFactory(
            direction="outbound",
            status="initiated",
            from_number="100",
            to_number="+15551234567",
            user=user,
        )
        assert call.pk is not None
        assert call.direction == "outbound"
        assert call.status == "initiated"
        assert call.from_number == "100"
        assert call.to_number == "+15551234567"
        assert call.user == user

    def test_str_representation_outbound(self):
        call = CallFactory(
            direction="outbound",
            from_number="100",
            to_number="+15559876543",
        )
        expected = "Outbound call: 100 -> +15559876543"
        assert str(call) == expected

    def test_str_representation_inbound(self):
        call = CallFactory(
            direction="inbound",
            from_number="+15559876543",
            to_number="100",
        )
        expected = "Inbound call: +15559876543 -> 100"
        assert str(call) == expected

    def test_duration_formatted_no_duration(self):
        call = CallFactory(duration=None)
        assert call.duration_formatted == "00:00"

    def test_duration_formatted_zero_seconds(self):
        call = CallFactory(duration=0)
        assert call.duration_formatted == "00:00"

    def test_duration_formatted_seconds_only(self):
        call = CallFactory(duration=45)
        assert call.duration_formatted == "00:45"

    def test_duration_formatted_minutes_and_seconds(self):
        call = CallFactory(duration=185)  # 3 min 5 sec
        assert call.duration_formatted == "03:05"

    def test_duration_formatted_with_hours(self):
        call = CallFactory(duration=3661)  # 1 hr 1 min 1 sec
        assert call.duration_formatted == "01:01:01"

    def test_created_at_and_updated_at_auto_set(self):
        call = CallFactory()
        assert call.created_at is not None
        assert call.updated_at is not None

    def test_ordering_by_created_at_descending(self):
        call1 = CallFactory()
        call2 = CallFactory()
        call3 = CallFactory()
        pks = list(Call.objects.values_list("pk", flat=True))
        # Most recent first
        assert pks == [call3.pk, call2.pk, call1.pk]

    def test_asterisk_channel_id_unique(self):
        CallFactory(asterisk_channel_id="unique-channel")
        with pytest.raises(Exception):
            CallFactory(asterisk_channel_id="unique-channel")

    def test_contact_fk_nullable(self):
        call = CallFactory(contact=None)
        assert call.contact is None

    def test_opportunity_fk_nullable(self):
        call = CallFactory(opportunity=None)
        assert call.opportunity is None

    def test_user_fk_nullable(self):
        call = CallFactory(user=None)
        assert call.user is None

    def test_default_status_is_initiated(self):
        call = CallFactory()
        assert call.status == "initiated"

    def test_notes_blank_by_default(self):
        call = CallFactory()
        assert call.notes == ""


# =============================================================================
# CallRecording Model
# =============================================================================


@pytest.mark.django_db
class TestCallRecordingModel:
    def test_create_recording(self):
        recording = CallRecordingFactory()
        assert recording.pk is not None
        assert recording.call is not None
        assert recording.duration == 120
        assert recording.file_size == 1048576

    def test_str_representation(self):
        call = CallFactory(direction="outbound", from_number="100", to_number="+15550001234")
        recording = CallRecordingFactory(call=call)
        assert "Recording for" in str(recording)
        assert "Outbound call" in str(recording)

    def test_file_size_formatted_zero(self):
        recording = CallRecordingFactory(file_size=None)
        assert recording.file_size_formatted == "0 B"

    def test_file_size_formatted_bytes(self):
        recording = CallRecordingFactory(file_size=512)
        assert recording.file_size_formatted == "512.0 B"

    def test_file_size_formatted_kilobytes(self):
        recording = CallRecordingFactory(file_size=2048)
        assert recording.file_size_formatted == "2.0 KB"

    def test_file_size_formatted_megabytes(self):
        recording = CallRecordingFactory(file_size=1048576)
        assert recording.file_size_formatted == "1.0 MB"

    def test_file_size_formatted_gigabytes(self):
        recording = CallRecordingFactory(file_size=1073741824)
        assert recording.file_size_formatted == "1.0 GB"

    def test_one_to_one_with_call(self):
        call = CallFactory()
        recording = CallRecordingFactory(call=call)
        assert call.recording == recording

    def test_cascade_delete_with_call(self):
        call = CallFactory()
        recording = CallRecordingFactory(call=call)
        recording_pk = recording.pk
        call.delete()
        assert not CallRecording.objects.filter(pk=recording_pk).exists()

    def test_created_at_auto_set(self):
        recording = CallRecordingFactory()
        assert recording.created_at is not None


# =============================================================================
# CallLog Model
# =============================================================================


@pytest.mark.django_db
class TestCallLogModel:
    def test_create_call_log(self):
        log = CallLogFactory(event="initiated", data={"from_ext": "100"})
        assert log.pk is not None
        assert log.event == "initiated"
        assert log.data == {"from_ext": "100"}

    def test_str_representation(self):
        call = CallFactory(direction="outbound", from_number="100", to_number="+15550009999")
        log = CallLogFactory(call=call, event="answered")
        result = str(log)
        assert "Outbound call" in result
        assert "answered" in result

    def test_ordering_by_timestamp(self):
        call = CallFactory()
        log1 = CallLogFactory(call=call, event="initiated")
        log2 = CallLogFactory(call=call, event="ringing")
        log3 = CallLogFactory(call=call, event="answered")
        events = list(call.logs.values_list("event", flat=True))
        assert events == ["initiated", "ringing", "answered"]

    def test_cascade_delete_with_call(self):
        call = CallFactory()
        log = CallLogFactory(call=call)
        log_pk = log.pk
        call.delete()
        assert not CallLog.objects.filter(pk=log_pk).exists()

    def test_default_data_is_empty_dict(self):
        call = CallFactory()
        log = CallLog.objects.create(call=call, event="test_event")
        assert log.data == {}

    def test_timestamp_auto_set(self):
        log = CallLogFactory()
        assert log.timestamp is not None


# =============================================================================
# SIPSettings Model
# =============================================================================


@pytest.mark.django_db
class TestSIPSettingsModel:
    def test_create_sip_settings(self):
        user = UserFactory()
        sip = SIPSettingsFactory(user=user)
        assert sip.pk is not None
        assert sip.user == user
        assert sip.server_ip == "192.168.1.100"
        assert sip.server_port == 5060
        assert sip.is_active is True

    def test_str_representation(self):
        user = UserFactory(username="voipuser")
        sip = SIPSettingsFactory(user=user)
        assert str(sip) == "SIP Settings for voipuser"

    def test_one_to_one_with_user(self):
        user = UserFactory()
        SIPSettingsFactory(user=user)
        with pytest.raises(Exception):
            SIPSettingsFactory(user=user)

    def test_password_encryption_and_decryption(self):
        user = UserFactory()
        sip = SIPSettingsFactory(user=user)
        sip.password = "my_secret_pass"
        sip.save()
        sip.refresh_from_db()
        # The raw _password should not be the plaintext
        assert sip._password != "my_secret_pass"
        # The property should decrypt back to plaintext
        assert sip.password == "my_secret_pass"

    def test_password_setter_empty_value(self):
        user = UserFactory()
        sip = SIPSettingsFactory(user=user)
        sip.password = ""
        assert sip._password == ""

    def test_password_getter_empty_value(self):
        user = UserFactory()
        sip = SIPSettingsFactory(user=user, _password="")
        assert sip.password == ""

    def test_default_registration_status(self):
        user = UserFactory()
        sip = SIPSettings.objects.create(
            user=user,
            server_ip="10.0.0.1",
            username="siptest",
            _password="test",
            caller_id="1000",
        )
        assert sip.registration_status == "unknown"

    def test_default_port(self):
        user = UserFactory()
        sip = SIPSettings.objects.create(
            user=user,
            server_ip="10.0.0.1",
            username="siptest",
            _password="test",
            caller_id="1000",
        )
        assert sip.server_port == 5060

    def test_created_at_and_updated_at_auto_set(self):
        sip = SIPSettingsFactory()
        assert sip.created_at is not None
        assert sip.updated_at is not None
