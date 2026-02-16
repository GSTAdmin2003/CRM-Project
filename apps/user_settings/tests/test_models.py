"""
Model tests for the user_settings app.
"""

import pytest

from apps.user_settings.models import SettingsCategory, SettingsPage, SystemConfiguration, UserPreferences
from .conftest import (
    SettingsCategoryFactory,
    SettingsPageFactory,
    SystemConfigurationFactory,
    UserFactory,
    UserPreferencesFactory,
)


@pytest.mark.django_db
class TestSettingsCategory:
    def test_create_category(self):
        cat = SettingsCategoryFactory(name="profile", display_name="Profile")
        assert cat.name == "profile"
        assert cat.display_name == "Profile"
        assert cat.is_active is True

    def test_str_returns_display_name(self):
        cat = SettingsCategoryFactory(display_name="My Category")
        assert str(cat) == "My Category"

    def test_ordering_by_order_then_name(self):
        c2 = SettingsCategoryFactory(order=2, name="bravo")
        c1 = SettingsCategoryFactory(order=1, name="alpha")
        c3 = SettingsCategoryFactory(order=2, name="alpha_two")
        categories = list(SettingsCategory.objects.all())
        assert categories[0] == c1
        assert categories[1] == c3  # same order, alpha_two < bravo
        assert categories[2] == c2


@pytest.mark.django_db
class TestSettingsPage:
    def test_create_page(self):
        page = SettingsPageFactory(name="personal_info")
        assert page.name == "personal_info"
        assert page.category is not None
        assert page.is_active is True

    def test_str_returns_category_and_page(self):
        cat = SettingsCategoryFactory(display_name="Profile")
        page = SettingsPageFactory(category=cat, display_name="Personal Info")
        assert str(page) == "Profile > Personal Info"

    def test_unique_together_category_name(self):
        cat = SettingsCategoryFactory()
        SettingsPageFactory(category=cat, name="page_a")
        with pytest.raises(Exception):
            SettingsPageFactory(category=cat, name="page_a")


@pytest.mark.django_db
class TestUserPreferences:
    def test_create_preferences(self):
        prefs = UserPreferencesFactory()
        assert prefs.theme == "light"
        assert prefs.language == "en"
        assert prefs.timezone == "UTC"
        assert prefs.notifications_email is True
        assert prefs.notifications_browser is True

    def test_str_returns_username_preferences(self):
        user = UserFactory(username="testuser")
        prefs = UserPreferencesFactory(user=user)
        assert str(prefs) == "testuser's preferences"

    def test_get_or_create_for_user_creates(self):
        user = UserFactory()
        prefs = UserPreferences.get_or_create_for_user(user)
        assert prefs.user == user
        assert prefs.theme == "light"

    def test_get_or_create_for_user_returns_existing(self):
        user = UserFactory()
        prefs1 = UserPreferencesFactory(user=user, theme="dark")
        prefs2 = UserPreferences.get_or_create_for_user(user)
        assert prefs2.pk == prefs1.pk
        assert prefs2.theme == "dark"

    def test_one_to_one_with_user(self):
        user = UserFactory()
        UserPreferencesFactory(user=user)
        with pytest.raises(Exception):
            UserPreferencesFactory(user=user)

    def test_timestamps_auto_set(self):
        prefs = UserPreferencesFactory()
        assert prefs.created_at is not None
        assert prefs.updated_at is not None


@pytest.mark.django_db
class TestSystemConfiguration:
    def test_create_configuration(self):
        config = SystemConfigurationFactory(key="site_name", value="My CRM")
        assert config.key == "site_name"
        assert config.value == "My CRM"

    def test_str_returns_key(self):
        config = SystemConfigurationFactory(key="max_leads")
        assert str(config) == "max_leads"

    def test_key_is_unique(self):
        SystemConfigurationFactory(key="unique_key")
        with pytest.raises(Exception):
            SystemConfigurationFactory(key="unique_key")

    def test_get_typed_value_string(self):
        config = SystemConfigurationFactory(value="hello", data_type="string")
        assert config.get_typed_value() == "hello"

    def test_get_typed_value_integer(self):
        config = SystemConfigurationFactory(value="42", data_type="integer")
        assert config.get_typed_value() == 42

    def test_get_typed_value_integer_invalid(self):
        config = SystemConfigurationFactory(value="not_a_number", data_type="integer")
        assert config.get_typed_value() == 0

    def test_get_typed_value_boolean_true(self):
        for val in ("true", "1", "yes", "on"):
            config = SystemConfigurationFactory(value=val, data_type="boolean")
            assert config.get_typed_value() is True

    def test_get_typed_value_boolean_false(self):
        config = SystemConfigurationFactory(value="false", data_type="boolean")
        assert config.get_typed_value() is False

    def test_get_typed_value_json(self):
        config = SystemConfigurationFactory(value='{"a": 1}', data_type="json")
        assert config.get_typed_value() == {"a": 1}

    def test_get_typed_value_json_invalid(self):
        config = SystemConfigurationFactory(value="not json", data_type="json")
        assert config.get_typed_value() == {}

    def test_get_setting_existing(self):
        SystemConfigurationFactory(key="test_key", value="test_val", data_type="string")
        assert SystemConfiguration.get_setting("test_key") == "test_val"

    def test_get_setting_missing_returns_default(self):
        assert SystemConfiguration.get_setting("nonexistent", default="fallback") == "fallback"

    def test_set_setting_creates(self):
        user = UserFactory()
        config = SystemConfiguration.set_setting("new_key", "new_val", user=user)
        assert config.key == "new_key"
        assert config.value == "new_val"

    def test_set_setting_updates_existing(self):
        user = UserFactory()
        SystemConfigurationFactory(key="existing_key", value="old_val")
        config = SystemConfiguration.set_setting("existing_key", "new_val", user=user)
        assert config.value == "new_val"
