"""
SettingsService — business logic for user settings.

Lightweight service layer for the user_settings app. Most settings operations
are simple CRUD handled by Django CBVs, but we centralize lookup/validation
logic here for consistency with the project's service-layer pattern.
"""

from django.db import transaction

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..models import SystemConfiguration, UserPreferences


class SettingsService:
    @staticmethod
    def get_or_create_preferences(*, user) -> UserPreferences:
        """Get or create preferences for a user."""
        return UserPreferences.get_or_create_for_user(user)

    @staticmethod
    @transaction.atomic
    def update_preferences(*, user, **fields) -> UserPreferences:
        """Update user preferences.

        Args:
            user: The user whose preferences to update.
            **fields: Allowed fields — theme, language, timezone,
                      notifications_email, notifications_browser, dashboard_layout.

        Returns:
            Updated UserPreferences instance.
        """
        prefs = UserPreferences.get_or_create_for_user(user)
        allowed = {
            "theme",
            "language",
            "timezone",
            "notifications_email",
            "notifications_browser",
            "dashboard_layout",
        }
        for key, value in fields.items():
            if key in allowed:
                setattr(prefs, key, value)
        prefs.save()
        return prefs

    @staticmethod
    def get_system_setting(*, key: str, default=None):
        """Retrieve a system configuration value."""
        return SystemConfiguration.get_setting(key, default=default)

    @staticmethod
    @transaction.atomic
    def set_system_setting(
        *,
        key: str,
        value: str,
        user,
        description: str = "",
        data_type: str = "string",
    ) -> SystemConfiguration:
        """Create or update a system configuration setting.

        Args:
            key: Setting key.
            value: Setting value (stored as string).
            user: The user making the change (for audit).
            description: Optional description.
            data_type: One of string, integer, boolean, json.

        Returns:
            The SystemConfiguration instance.

        Raises:
            PermissionDeniedError: If user is not an Owner or staff.
        """
        if not (user.has_role("Owner") or user.is_staff):
            raise PermissionDeniedError("Only owners and staff can modify system settings")
        return SystemConfiguration.set_setting(
            key, value, description=description, data_type=data_type, user=user
        )
