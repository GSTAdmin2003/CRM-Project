from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseSettingModel(models.Model):
    """Abstract base model for all settings"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SettingsCategory(models.Model):
    """Model to define setting categories for sidebar organization"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-cog')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'user_settings'
        ordering = ['order', 'name']
        verbose_name_plural = "Settings Categories"
    
    def __str__(self):
        return self.display_name


class SettingsPage(models.Model):
    """Model to define individual settings pages within categories"""
    category = models.ForeignKey(SettingsCategory, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    url_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='fas fa-circle')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'user_settings'
        ordering = ['order', 'name']
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.display_name} > {self.display_name}"