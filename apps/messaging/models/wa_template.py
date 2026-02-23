from django.db import models

APPROVAL_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('pending', 'Pending Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('paused', 'Paused'),
]


class WhatsAppTemplate(models.Model):
    """
    Stores Meta-approved WhatsApp template messages.
    Agents select a template when initiating a new conversation.
    """

    name = models.CharField(
        max_length=200,
        help_text="Exact template name as registered in Meta (e.g. hello_world)",
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Friendly label shown to agents",
    )
    language = models.CharField(
        max_length=20,
        default="en_US",
        help_text="BCP-47 language code (e.g. en_US, ar, pt_BR)",
    )
    body_preview = models.TextField(
        help_text="Body text with {{1}}, {{2}} placeholders",
    )
    variable_names = models.JSONField(
        default=list,
        help_text="Ordered list of UI labels for each placeholder (e.g. ['Customer Name', 'Date'])",
    )
    is_active = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "messaging"
        verbose_name = "WhatsApp Template"
        verbose_name_plural = "WhatsApp Templates"
        ordering = ["display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'language'], name='unique_template_name_language'
            )
        ]

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    def render_body(self, variables: list) -> str:
        """Replace {{1}}, {{2}} … with supplied variable values."""
        body = self.body_preview
        for i, val in enumerate(variables):
            body = body.replace("{{" + str(i + 1) + "}}", val)
        return body
