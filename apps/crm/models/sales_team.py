from django.db import models
from core.models import User


class SalesTeam(models.Model):
    """Sales team model for organizing users"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_teams"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_team_members(self):
        """Get all active team members"""
        return User.objects.filter(sales_team=self, is_active=True)

    def get_team_leads(self):
        """Get all leads assigned to team members"""
        from apps.crm.models.lead import Lead

        team_members = self.get_team_members()
        return Lead.objects.filter(assigned_to__in=team_members)
