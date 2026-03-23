from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class LeadStage(models.Model):
    """Kanban stages for opportunities"""

    STAGE_TYPE_CHOICES = [
        ("normal", "Normal"),
        ("contacted", "Contacted"),
    ]

    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default="#6B7280")  # Hex color
    is_active = models.BooleanField(default=True)
    is_closed_stage = models.BooleanField(default=False)
    stage_type = models.CharField(max_length=10, choices=STAGE_TYPE_CHOICES, default="normal")
    probability = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default probability percentage for this stage",
    )
    # Team-specific stages - null means global/default stages
    sales_team = models.ForeignKey(
        "crm.SalesTeam",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="custom_stages",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stages",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["sales_team", "order", "name"]
        # Stage names should be unique per team (including global stages)
        unique_together = [["name", "sales_team"]]

    def __str__(self):
        if self.sales_team:
            return f"{self.name} ({self.sales_team.name})"
        return f"{self.name} (Global)"

    @classmethod
    def get_stages_for_team(cls, sales_team=None):
        """Get stages for a specific team, falling back to global stages if team has no custom stages"""
        if sales_team:
            # First try to get team-specific stages
            team_stages = cls.objects.filter(sales_team=sales_team, is_active=True).order_by(
                "order"
            )
            if team_stages.exists():
                return team_stages

        # Fall back to global stages
        return cls.objects.filter(sales_team=None, is_active=True).order_by("order")

    @classmethod
    def get_default_stage_for_team(cls, sales_team=None):
        """Get the first (default) stage for a team"""
        stages = cls.get_stages_for_team(sales_team)
        return stages.first()

    @classmethod
    def get_contacted_stage_for_team(cls, sales_team=None):
        """Get the 'contacted' stage for a team, falling back to global."""
        if sales_team:
            stage = cls.objects.filter(
                sales_team=sales_team, is_active=True, stage_type="contacted"
            ).first()
            if stage:
                return stage
        return cls.objects.filter(
            sales_team=None, is_active=True, stage_type="contacted"
        ).first()

    def can_be_edited_by(self, user):
        """Check if user can edit this stage"""
        # Global stages: directors only
        if not self.sales_team:
            return user.is_sales_director()

        # Team stages: the team's manager or any director
        return user.is_sales_director() or (
            user.is_sales_manager() and self.sales_team.manager == user
        )

    @classmethod
    def migrate_leads_to_new_stages(cls, sales_team):
        """Migrate leads when team stages change"""
        from django.db.models import Q

        from apps.crm.models.lead import Lead
        from apps.crm.models.lead_activity import LeadActivity

        # Get team's current custom stages
        team_stages = cls.objects.filter(
            sales_team=sales_team,
            is_active=True,
            is_closed_stage=False,  # Exclude Won/Lost stages
        ).order_by("probability", "order")

        if not team_stages.exists():
            return  # No custom stages to migrate to

        # Get all leads for this team that are on global stages
        team_leads = Lead.objects.filter(
            Q(sales_team=sales_team) | Q(assigned_to__sales_team=sales_team),
            stage__sales_team__isnull=True,  # Currently on global stages
            stage__is_closed_stage=False,  # Not on Won/Lost stages
        )

        for lead in team_leads:
            current_probability = lead.stage.probability

            # Find closest team stage by probability (excluding closed stages)
            closest_stage = min(
                team_stages, key=lambda stage: abs(stage.probability - current_probability)
            )

            # Only migrate if it's actually different
            if lead.stage != closest_stage:
                old_stage = lead.stage
                lead.stage = closest_stage
                lead.probability = closest_stage.probability
                lead.save()

                # Log the migration activity
                LeadActivity.objects.create(
                    lead=lead,
                    user=None,  # System migration
                    activity_type="stage_change",
                    subject=f"Auto-migrated from {old_stage.name} to {closest_stage.name}",
                    description=(
                        f'Lead automatically moved from global stage "{old_stage.name}" to team'
                        f' stage "{closest_stage.name}" due to team pipeline changes'
                    ),
                )
