from django.db import models
from django.contrib.auth import get_user_model
from .base import BaseSettingModel

User = get_user_model()


class UserPreferences(BaseSettingModel):
    """User preference settings"""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    notifications_email = models.BooleanField(default=True)
    notifications_browser = models.BooleanField(default=True)
    dashboard_layout = models.JSONField(default=dict, blank=True)
    
    class Meta:
        app_label = 'user_settings'
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"
    
    def __str__(self):
        return f"{self.user.username}'s preferences"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create preferences for a user"""
        preferences, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'theme': 'light',
                'language': 'en',
                'timezone': 'UTC',
            }
        )
        return preferences