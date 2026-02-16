from django.db import models

from apps.contacts.models import Company, Contact
from core.models import User


class IncomingLead(models.Model):
    """Simple lead capture - contact information and message"""

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("converted", "Converted to Opportunity"),
        ("rejected", "Rejected"),
    ]

    # Relationships
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_leads"
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_leads"
    )

    # Lead Details
    message = models.TextField(help_text="Initial message or inquiry from the lead")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    # Assignment
    sales_team = models.ForeignKey(
        "crm.SalesTeam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_leads",
        help_text="Sales team responsible for this lead",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_incoming_leads",
        help_text="Sales person assigned to follow up",
    )

    # Conversion tracking
    converted_opportunity = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_lead",
        help_text="Opportunity created from this lead",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_incoming_leads",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self):
        if self.contact:
            return f"{self.contact.name} - {self.contact.email}"
        elif self.company:
            return f"Lead from {self.company.display_name}"
        return f"Lead #{self.pk}"

    def can_be_viewed_by(self, user):
        """Check if user can view this lead"""
        # Executives can see all leads
        if user.is_sales_executive():
            return True

        # Managers can see their team's leads
        if user.is_sales_manager():
            if self.sales_team and user.sales_team == self.sales_team:
                return True

        # Assigned user can see their leads
        if self.assigned_to == user:
            return True

        # Creator can see their leads
        return self.created_by == user

    def can_be_edited_by(self, user):
        """Check if user can edit this lead"""
        # Executives can edit all leads
        if user.is_sales_executive():
            return True

        # Managers can edit their team's leads
        if user.is_sales_manager():
            if self.sales_team and user.sales_team == self.sales_team:
                return True

        # Assigned user can edit their leads
        return self.assigned_to == user
