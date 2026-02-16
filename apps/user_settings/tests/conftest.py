"""
Factories and fixtures for user_settings tests.
"""

import factory
from django.contrib.auth import get_user_model

from apps.user_settings.models import SettingsCategory, SettingsPage, SystemConfiguration, UserPreferences

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"settingsuser{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class SettingsCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SettingsCategory

    name = factory.Sequence(lambda n: f"category_{n}")
    display_name = factory.LazyAttribute(lambda o: o.name.replace("_", " ").title())
    order = factory.Sequence(lambda n: n)
    is_active = True


class SettingsPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SettingsPage

    category = factory.SubFactory(SettingsCategoryFactory)
    name = factory.Sequence(lambda n: f"page_{n}")
    display_name = factory.LazyAttribute(lambda o: o.name.replace("_", " ").title())
    url_name = factory.LazyAttribute(lambda o: f"settings:{o.name}")
    order = factory.Sequence(lambda n: n)
    is_active = True


class UserPreferencesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserPreferences

    user = factory.SubFactory(UserFactory)
    theme = "light"
    language = "en"
    timezone = "UTC"
    notifications_email = True
    notifications_browser = True


class SystemConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SystemConfiguration

    key = factory.Sequence(lambda n: f"config_key_{n}")
    value = "test_value"
    data_type = "string"
    description = "Test configuration"
