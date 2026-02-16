from django.db import models

from core.models import User


class LeadActivity(models.Model):
    """Activity tracking for opportunities"""

    ACTIVITY_TYPES = [
        ("call", "Phone Call"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("note", "Note"),
        ("stage_change", "Stage Changed"),
        ("created", "Opportunity Created"),
        ("assigned", "Opportunity Assigned"),
        ("updated", "Opportunity Updated"),
    ]

    lead = models.ForeignKey("crm.Lead", on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="lead_activities"
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Additional data
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in minutes")
    outcome = models.CharField(max_length=100, blank=True)
    follow_up_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Opportunity Activity"
        verbose_name_plural = "Opportunity Activities"

    def __str__(self):
        return f"{self.lead.title} - {self.get_activity_type_display()}"
