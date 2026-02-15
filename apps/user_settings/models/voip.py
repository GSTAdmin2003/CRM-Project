from django.db import models
from django.conf import settings
from .base import BaseSettingModel


class SIPSettings(BaseSettingModel):
    """Store SIP credentials for VoIP calling"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sip_settings'
    )

    # SIP Server Configuration
    server_ip = models.CharField(
        max_length=255,
        verbose_name='SIP Server IP/Host',
        help_text='The IP address or hostname of your SIP trunk provider'
    )
    server_port = models.PositiveIntegerField(
        default=5060,
        verbose_name='SIP Port',
        help_text='Default is 5060 for UDP'
    )

    # Authentication
    username = models.CharField(
        max_length=128,
        verbose_name='SIP Username',
        help_text='Your SIP account username (often your phone number)'
    )
    password = models.CharField(
        max_length=128,
        verbose_name='SIP Password',
        help_text='Your SIP account password'
    )

    # Caller ID
    caller_id = models.CharField(
        max_length=32,
        verbose_name='Caller ID',
        help_text='The phone number displayed to called parties'
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active',
        help_text='Enable or disable SIP calling'
    )

    # Registration status (updated by system)
    registration_status = models.CharField(
        max_length=50,
        default='unknown',
        choices=[
            ('unknown', 'Unknown'),
            ('registered', 'Registered'),
            ('unregistered', 'Unregistered'),
            ('failed', 'Registration Failed'),
        ]
    )
    last_registration_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'user_settings'
        verbose_name = 'SIP Settings'
        verbose_name_plural = 'SIP Settings'

    def __str__(self):
        return f"SIP Settings for {self.user.username}"
