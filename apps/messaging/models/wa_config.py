from django.db import models


class WhatsAppConfig(models.Model):
    """
    Singleton model storing Meta Cloud API credentials.
    Configured via Settings > WhatsApp, not environment variables.
    """

    access_token = models.TextField(
        blank=True,
        help_text="Permanent access token from Meta Business Suite",
    )
    phone_number_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Phone Number ID from Meta developer console",
    )
    app_secret = models.CharField(
        max_length=300,
        blank=True,
        help_text="App Secret used to verify webhook signatures",
    )
    webhook_verify_token = models.CharField(
        max_length=200,
        default="crm-webhook-token",
        help_text="Token you set in Meta webhook configuration",
    )
    app_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Facebook App ID (required for media uploads during template submission)",
    )
    waba_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="WhatsApp Business Account ID (required for template submission)",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Enable/disable WhatsApp integration",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "messaging"
        verbose_name = "WhatsApp Configuration"

    def __str__(self):
        return "WhatsApp Configuration"

    @classmethod
    def get_config(cls):
        """Return the single config instance, or None if not set up."""
        return cls.objects.first()

    @classmethod
    def get_or_create_config(cls):
        """Return the single config instance, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_configured(self):
        return bool(self.access_token and self.phone_number_id)

    def can_submit_templates(self):
        return bool(self.is_configured() and self.waba_id)
