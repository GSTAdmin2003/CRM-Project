from django.db import models
from django.contrib.auth import get_user_model
from .base import BaseSettingModel

User = get_user_model()


class SystemConfiguration(BaseSettingModel):
    """System-wide configuration settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=20, 
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    is_public = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        app_label = 'user_settings'
        ordering = ['key']
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"
    
    def __str__(self):
        return self.key
    
    def get_typed_value(self):
        """Return value converted to appropriate type"""
        if self.data_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        return self.value
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a system setting value"""
        try:
            setting = cls.objects.get(key=key)
            return setting.get_typed_value()
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(cls, key, value, description='', data_type='string', user=None):
        """Set a system setting value"""
        setting, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value),
                'description': description,
                'data_type': data_type,
                'updated_by': user,
            }
        )
        return setting