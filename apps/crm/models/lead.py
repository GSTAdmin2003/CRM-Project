from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from apps.contacts.models import Company, Contact
from core.models import User


class Lead(models.Model):
    """Unified Lead model — covers both leads (lead_type='lead') and opportunities (lead_type='opportunity')."""

    TYPE_LEAD = "lead"
    TYPE_OPPORTUNITY = "opportunity"
    TYPE_CHOICES = [
        ("lead", "Lead"),
        ("opportunity", "Opportunity"),
    ]

    SOURCE_CHOICES = [
        ("website", "Website"),
        ("referral", "Referral"),
        ("cold_call", "Cold Call"),
        ("email", "Email Campaign"),
        ("social_media", "Social Media"),
        ("trade_show", "Trade Show"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("unqualified", "Unqualified"),
        ("converted", "Converted"),
        ("rejected", "Rejected"),
    ]

    # Type discriminator
    lead_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="opportunity", db_index=True
    )

    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Opportunity Title")
    full_name = models.CharField(max_length=200, verbose_name="Full Name", blank=True, default="")
    first_name = models.CharField(max_length=100, blank=True)  # Kept for backward compatibility
    last_name = models.CharField(max_length=100, blank=True)  # Kept for backward compatibility
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=100, blank=True)

    # Lead-specific fields
    message = models.TextField(blank=True, help_text="Initial inquiry (for leads)")
    converted_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_opportunities",
    )

    # Sales Information
    stage = models.ForeignKey(
        "crm.LeadStage", on_delete=models.PROTECT, related_name="leads",
        null=True, blank=True,
    )
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    expected_close_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="other")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    # Relationships
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assigned_leads"
    )
    sales_team = models.ForeignKey(
        "crm.SalesTeam", on_delete=models.SET_NULL, null=True, related_name="team_leads"
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )

    # Tracking
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_leads"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)

    # Additional data as JSON
    custom_fields = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-last_activity"]
        verbose_name = "Opportunity"
        verbose_name_plural = "Opportunities"

    def __str__(self):
        return f"{self.title} - {self.full_name or f'{self.first_name} {self.last_name}'.strip()}"

    @property
    def contact_full_name(self):
        """Get the full name, prioritizing the full_name field"""
        return self.full_name or f"{self.first_name} {self.last_name}".strip()

    @property
    def weighted_value(self):
        """Calculate weighted value based on probability"""
        return float(self.estimated_value) * (self.probability / 100)

    def get_absolute_url(self):
        return reverse("crm:opportunity_edit", kwargs={"pk": self.pk})

    def can_be_viewed_by(self, user):
        """Check if user can view this lead based on role and team"""
        # Executives (including Owners) can see all leads
        if user.is_sales_executive():
            return True

        # Managers can see their team's leads
        if user.is_sales_manager():
            if self.sales_team and user in self.sales_team.get_team_members():
                return True
            if self.sales_team and self.sales_team.manager == user:
                return True

        # Sales reps can see their own leads
        if user.has_role("Sales Rep"):
            return self.assigned_to == user

        # Lead creator can always see their lead
        return self.created_by == user

    def can_be_edited_by(self, user):
        """Check if user can edit this lead"""
        # Executives (including Owners) can edit all leads
        if user.is_sales_executive():
            return True

        # Managers can edit their team's leads
        if user.is_sales_manager():
            if self.sales_team and self.sales_team.manager == user:
                return True

        # Assigned user can edit their lead
        return self.assigned_to == user

    def save(self, *args, **kwargs):
        from core.utils import normalize_phone
        self.phone = normalize_phone(self.phone)

        # Auto-assign sales team if not set
        if not self.sales_team and self.assigned_to and self.assigned_to.sales_team:
            self.sales_team = self.assigned_to.sales_team

        # Update probability from stage if not explicitly set
        if self.stage and not kwargs.get("update_fields"):
            self.probability = self.stage.probability

        # Sync full_name with first_name/last_name for backward compatibility
        if self.full_name and not self.first_name and not self.last_name:
            name_parts = self.full_name.split(" ", 1)
            self.first_name = name_parts[0] if name_parts else ""
            self.last_name = name_parts[1] if len(name_parts) > 1 else ""
        elif self.first_name or self.last_name:
            if not self.full_name:
                self.full_name = f"{self.first_name} {self.last_name}".strip()

        super().save(*args, **kwargs)
