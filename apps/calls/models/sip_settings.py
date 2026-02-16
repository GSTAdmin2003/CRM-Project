from django.conf import settings
from django.db import models

from ..encryption import decrypt, encrypt


class SIPSettings(models.Model):
    """Store SIP credentials for VoIP calling"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sip_settings",
    )
    server_ip = models.CharField(max_length=255, verbose_name="SIP Server IP/Host")
    server_port = models.PositiveIntegerField(default=5060, verbose_name="SIP Port")
    username = models.CharField(max_length=128, verbose_name="SIP Username")
    _password = models.TextField(db_column="password", verbose_name="SIP Password")
    caller_id = models.CharField(max_length=32, verbose_name="Caller ID")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    registration_status = models.CharField(
        max_length=50,
        default="unknown",
        choices=[
            ("unknown", "Unknown"),
            ("registered", "Registered"),
            ("unregistered", "Unregistered"),
            ("failed", "Registration Failed"),
        ],
    )
    last_registration_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SIP Settings"
        verbose_name_plural = "SIP Settings"

    def __str__(self):
        return f"SIP Settings for {self.user.username}"

    @property
    def password(self):
        """Decrypt and return the password."""
        if self._password:
            try:
                return decrypt(self._password)
            except Exception:
                return self._password
        return ""

    @password.setter
    def password(self, value):
        """Encrypt and store the password."""
        if value:
            self._password = encrypt(value)
        else:
            self._password = ""
