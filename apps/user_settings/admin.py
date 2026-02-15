from django.contrib import admin
from .models import UserPreferences, SystemConfiguration


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'language', 'timezone', 'updated_at']
    list_filter = ['theme', 'language', 'timezone']
    search_fields = ['user__username', 'user__email']


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']