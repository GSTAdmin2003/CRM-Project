from django.db import models
from django.conf import settings
from apps.crm.models import Lead


class ActivityType(models.Model):
    """Type of activity with custom icon and color"""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class (e.g., 'fas fa-phone')")
    color = models.CharField(max_length=7, default='#6366f1', help_text="Hex color code")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Activity Type'
        verbose_name_plural = 'Activity Types'

    def __str__(self):
        return self.name


class Activity(models.Model):
    """Activity scheduled for an opportunity"""
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='scheduled_activities', verbose_name='Opportunity')
    activity_type = models.ForeignKey(ActivityType, on_delete=models.PROTECT, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    outcome = models.TextField(blank=True, help_text="Notes about the outcome (filled when completed)")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_activities'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_activities'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_date', '-created_at']
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'

    def __str__(self):
        return f"{self.activity_type.name}: {self.title} ({self.lead.title})"

    def can_be_viewed_by(self, user):
        """Check if user can view this activity based on lead ownership/team"""
        # Executives see all activities
        if user.is_sales_executive():
            return True

        # Managers see their team's activities
        if user.is_sales_manager() and user.sales_team:
            if self.lead.assigned_to and self.lead.assigned_to.sales_team == user.sales_team:
                return True
            if self.lead.sales_team == user.sales_team:
                return True

        # Users see activities for leads assigned to them
        if self.lead.assigned_to == user:
            return True

        # Creator can always see
        return self.created_by == user

    def can_be_edited_by(self, user):
        """Check if user can edit this activity"""
        # Executives can edit all
        if user.is_sales_executive():
            return True

        # Managers can edit their team's activities
        if user.is_sales_manager() and user.sales_team:
            if self.lead.assigned_to and self.lead.assigned_to.sales_team == user.sales_team:
                return True
            if self.lead.sales_team == user.sales_team:
                return True

        # Assigned user can edit
        if self.assigned_to == user:
            return True

        # Creator can edit
        return self.created_by == user

    def is_overdue(self):
        """Check if activity is overdue (past scheduled date and not completed)"""
        from datetime import date
        return self.scheduled_date < date.today() and self.status == 'planned'
