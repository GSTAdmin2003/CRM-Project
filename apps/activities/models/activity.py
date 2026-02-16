from datetime import date

from django.conf import settings
from django.db import models

from apps.crm.models import Lead

from .activity_type import ActivityType


class Activity(models.Model):
    """Activity scheduled for an opportunity"""

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="scheduled_activities",
        verbose_name="Opportunity",
    )
    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.PROTECT, related_name="activities"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    outcome = models.TextField(
        blank=True, help_text="Notes about the outcome (filled when completed)"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_activities",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-scheduled_date", "-created_at"]
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return f"{self.activity_type.name}: {self.title} ({self.lead.title})"

    def can_be_viewed_by(self, user):
        """Check if user can view this activity based on lead ownership/team"""
        if user.is_sales_executive():
            return True

        if user.is_sales_manager() and user.sales_team:
            if self.lead.assigned_to and self.lead.assigned_to.sales_team == user.sales_team:
                return True
            if self.lead.sales_team == user.sales_team:
                return True

        if self.lead.assigned_to == user:
            return True

        return self.created_by == user

    def can_be_edited_by(self, user):
        """Check if user can edit this activity"""
        if user.is_sales_executive():
            return True

        if user.is_sales_manager() and user.sales_team:
            if self.lead.assigned_to and self.lead.assigned_to.sales_team == user.sales_team:
                return True
            if self.lead.sales_team == user.sales_team:
                return True

        if self.assigned_to == user:
            return True

        return self.created_by == user

    def is_overdue(self):
        """Check if activity is overdue (past scheduled date and not completed)"""
        return self.scheduled_date < date.today() and self.status == "planned"
