from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import User
from apps.contacts.models import Company, Contact
import json


class SalesTeam(models.Model):
    """Sales team model for organizing users"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_teams')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_team_members(self):
        """Get all active team members"""
        return User.objects.filter(sales_team=self, is_active=True)
    
    def get_team_leads(self):
        """Get all leads assigned to team members"""
        team_members = self.get_team_members()
        return Lead.objects.filter(assigned_to__in=team_members)


class LeadStage(models.Model):
    """Kanban stages for opportunities"""
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#6B7280')  # Hex color
    is_active = models.BooleanField(default=True)
    is_closed_stage = models.BooleanField(default=False)
    probability = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default probability percentage for this stage"
    )
    # Team-specific stages - null means global/default stages
    sales_team = models.ForeignKey('SalesTeam', on_delete=models.CASCADE, null=True, blank=True, related_name='custom_stages')
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_stages')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        ordering = ['sales_team', 'order', 'name']
        # Stage names should be unique per team (including global stages)
        unique_together = [['name', 'sales_team']]
    
    def __str__(self):
        if self.sales_team:
            return f"{self.name} ({self.sales_team.name})"
        return f"{self.name} (Global)"
    
    @classmethod
    def get_stages_for_team(cls, sales_team=None):
        """Get stages for a specific team, falling back to global stages if team has no custom stages"""
        if sales_team:
            # First try to get team-specific stages
            team_stages = cls.objects.filter(sales_team=sales_team, is_active=True).order_by('order')
            if team_stages.exists():
                return team_stages
        
        # Fall back to global stages
        return cls.objects.filter(sales_team=None, is_active=True).order_by('order')
    
    @classmethod
    def get_default_stage_for_team(cls, sales_team=None):
        """Get the first (default) stage for a team"""
        stages = cls.get_stages_for_team(sales_team)
        return stages.first()
    
    def can_be_edited_by(self, user):
        """Check if user can edit this stage"""
        # Global stages can only be edited by sales executives
        if not self.sales_team:
            return user.is_sales_executive()
        
        # Team stages can be edited by the team manager or sales executives
        return (user.is_sales_executive() or 
                (user.is_sales_manager() and self.sales_team.manager == user))
    
    @classmethod
    def migrate_leads_to_new_stages(cls, sales_team):
        """Migrate leads when team stages change"""
        from django.db.models import Q
        
        # Get team's current custom stages
        team_stages = cls.objects.filter(
            sales_team=sales_team, 
            is_active=True,
            is_closed_stage=False  # Exclude Won/Lost stages
        ).order_by('probability', 'order')
        
        if not team_stages.exists():
            return  # No custom stages to migrate to
        
        # Get all leads for this team that are on global stages
        team_leads = Lead.objects.filter(
            Q(sales_team=sales_team) | Q(assigned_to__sales_team=sales_team),
            stage__sales_team__isnull=True,  # Currently on global stages
            stage__is_closed_stage=False     # Not on Won/Lost stages
        )
        
        for lead in team_leads:
            current_probability = lead.stage.probability
            
            # Find closest team stage by probability (excluding closed stages)
            closest_stage = min(
                team_stages,
                key=lambda stage: abs(stage.probability - current_probability)
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
                    activity_type='stage_change',
                    subject=f'Auto-migrated from {old_stage.name} to {closest_stage.name}',
                    description=f'Lead automatically moved from global stage "{old_stage.name}" to team stage "{closest_stage.name}" due to team pipeline changes'
                )


class Lead(models.Model):
    """Lead model for CRM pipeline"""
    
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('cold_call', 'Cold Call'),
        ('email', 'Email Campaign'),
        ('social_media', 'Social Media'),
        ('trade_show', 'Trade Show'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('unqualified', 'Unqualified'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Opportunity Title")
    full_name = models.CharField(max_length=200, verbose_name="Full Name", blank=True, default="")
    first_name = models.CharField(max_length=100, blank=True)  # Kept for backward compatibility
    last_name = models.CharField(max_length=100, blank=True)   # Kept for backward compatibility
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=100, blank=True)
    
    # Sales Information
    stage = models.ForeignKey(LeadStage, on_delete=models.PROTECT, related_name='leads')
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    expected_close_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Relationships
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_leads')
    sales_team = models.ForeignKey(SalesTeam, on_delete=models.SET_NULL, null=True, related_name='team_leads')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Additional data as JSON
    custom_fields = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-last_activity']
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
    
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
        return reverse('crm:opportunity_edit', kwargs={'pk': self.pk})
    
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
        if user.has_role('Sales Rep'):
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
        # Auto-assign sales team if not set
        if not self.sales_team and self.assigned_to and self.assigned_to.sales_team:
            self.sales_team = self.assigned_to.sales_team
        
        # Update probability from stage if not explicitly set
        if self.stage and not kwargs.get('update_fields'):
            self.probability = self.stage.probability
        
        # Sync full_name with first_name/last_name for backward compatibility
        if self.full_name and not self.first_name and not self.last_name:
            name_parts = self.full_name.split(' ', 1)
            self.first_name = name_parts[0] if name_parts else ''
            self.last_name = name_parts[1] if len(name_parts) > 1 else ''
        elif self.first_name or self.last_name:
            if not self.full_name:
                self.full_name = f"{self.first_name} {self.last_name}".strip()
        
        super().save(*args, **kwargs)


class LeadActivity(models.Model):
    """Activity tracking for opportunities"""

    ACTIVITY_TYPES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('note', 'Note'),
        ('stage_change', 'Stage Changed'),
        ('created', 'Opportunity Created'),
        ('assigned', 'Opportunity Assigned'),
        ('updated', 'Opportunity Updated'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lead_activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Additional data
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in minutes")
    outcome = models.CharField(max_length=100, blank=True)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Opportunity Activity'
        verbose_name_plural = 'Opportunity Activities'

    def __str__(self):
        return f"{self.lead.title} - {self.get_activity_type_display()}"


class LeadFile(models.Model):
    """File attachments for opportunities"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='leads/files/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.lead.title} - {self.filename}"


class IncomingLead(models.Model):
    """Simple lead capture - contact information and message"""

    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('converted', 'Converted to Opportunity'),
        ('rejected', 'Rejected'),
    ]

    # Relationships
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_leads')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_leads')

    # Lead Details
    message = models.TextField(help_text="Initial message or inquiry from the lead")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    # Assignment
    sales_team = models.ForeignKey(
        SalesTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_leads',
        help_text="Sales team responsible for this lead"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_incoming_leads',
        help_text="Sales person assigned to follow up"
    )

    # Conversion tracking
    converted_opportunity = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_lead',
        help_text="Opportunity created from this lead"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_incoming_leads'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'

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