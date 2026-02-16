"""
Service tests for the user_settings app.
"""

import pytest

from core.exceptions import PermissionDeniedError
from core.models import Role, UserRole

from apps.user_settings.models import SystemConfiguration, UserPreferences
from apps.user_settings.services import SettingsService
from .conftest import SystemConfigurationFactory, UserFactory, UserPreferencesFactory


@pytest.mark.django_db
class TestSettingsServiceGetOrCreatePreferences:
    def test_creates_when_none_exist(self):
        user = UserFactory()
        prefs = SettingsService.get_or_create_preferences(user=user)
        assert prefs.user == user
        assert prefs.theme == "light"

    def test_returns_existing(self):
        user = UserFactory()
        existing = UserPreferencesFactory(user=user, theme="dark")
        prefs = SettingsService.get_or_create_preferences(user=user)
        assert prefs.pk == existing.pk
        assert prefs.theme == "dark"


@pytest.mark.django_db
class TestSettingsServiceUpdatePreferences:
    def test_update_theme(self):
        user = UserFactory()
        UserPreferencesFactory(user=user, theme="light")
        prefs = SettingsService.update_preferences(user=user, theme="dark")
        assert prefs.theme == "dark"

    def test_update_multiple_fields(self):
        user = UserFactory()
        UserPreferencesFactory(user=user)
        prefs = SettingsService.update_preferences(
            user=user, theme="dark", language="es", notifications_email=False
        )
        assert prefs.theme == "dark"
        assert prefs.language == "es"
        assert prefs.notifications_email is False

    def test_ignores_disallowed_fields(self):
        user = UserFactory()
        existing = UserPreferencesFactory(user=user)
        prefs = SettingsService.update_preferences(user=user, pk=999)
        assert prefs.pk == existing.pk  # pk should not have been changed

    def test_creates_preferences_if_not_exist(self):
        user = UserFactory()
        prefs = SettingsService.update_preferences(user=user, theme="dark")
        assert prefs.theme == "dark"
        assert prefs.user == user


@pytest.mark.django_db
class TestSettingsServiceGetSystemSetting:
    def test_returns_value(self):
        SystemConfigurationFactory(key="site_name", value="My CRM", data_type="string")
        assert SettingsService.get_system_setting(key="site_name") == "My CRM"

    def test_returns_default_when_missing(self):
        assert SettingsService.get_system_setting(key="nonexistent", default="fallback") == "fallback"


@pytest.mark.django_db
class TestSettingsServiceSetSystemSetting:
    def test_set_setting_as_owner(self):
        user = UserFactory()
        role = Role.objects.get_or_create(name="Owner", defaults={"description": "Owner"})[0]
        UserRole.objects.create(user=user, role=role)
        config = SettingsService.set_system_setting(
            key="max_leads", value="100", user=user, data_type="integer"
        )
        assert config.key == "max_leads"
        assert config.value == "100"

    def test_set_setting_as_staff(self):
        user = UserFactory()
        user.is_staff = True
        user.save()
        config = SettingsService.set_system_setting(key="setting_x", value="val", user=user)
        assert config.key == "setting_x"

    def test_set_setting_denied_for_regular_user(self):
        user = UserFactory()
        with pytest.raises(PermissionDeniedError):
            SettingsService.set_system_setting(key="forbidden", value="val", user=user)
