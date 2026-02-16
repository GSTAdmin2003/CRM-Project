from django.db import models


class ActivityType(models.Model):
    """Type of activity with custom icon and color"""

    name = models.CharField(max_length=100)
    icon = models.CharField(
        max_length=50, help_text="Font Awesome icon class (e.g., 'fas fa-phone')"
    )
    color = models.CharField(max_length=7, default="#6366f1", help_text="Hex color code")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Activity Type"
        verbose_name_plural = "Activity Types"

    def __str__(self):
        return self.name
