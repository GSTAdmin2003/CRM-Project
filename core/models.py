from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
import importlib
import os


class User(AbstractUser):
    """Extended user model with role support"""
    email = models.EmailField(unique=True)
    sales_team = models.ForeignKey('crm.SalesTeam', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    # VoIP extension for making calls
    extension = models.CharField(max_length=20, blank=True, help_text="SIP extension for VoIP calls")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_roles(self):
        """Get all roles assigned to this user"""
        return self.user_roles.all()
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return self.user_roles.filter(role__name=role_name).exists()
    
    def is_owner(self):
        """Check if user is an owner"""
        return self.has_role('Owner')
    
    def is_sales_rep(self):
        """Check if user is a sales rep"""
        return self.has_role('Sales Rep')
    
    def is_sales_manager(self):
        """Check if user is a sales manager"""
        return self.has_role('Sales Manager') or self.has_role('Owner')
    
    def is_sales_executive(self):
        """Check if user is a sales executive"""
        return self.has_role('Sales Executive') or self.has_role('Owner')
    
    def get_accessible_leads_queryset(self):
        """Get leads queryset based on user role and team"""
        from apps.crm.models import Lead

        # Executives see all leads
        if self.is_sales_executive():
            return Lead.objects.all()

        # Managers see their team's leads
        if self.is_sales_manager() and self.sales_team:
            team_members = self.sales_team.get_team_members()
            return Lead.objects.filter(assigned_to__in=team_members)

        # Sales reps see their own leads
        return Lead.objects.filter(assigned_to=self)

    def get_accessible_activities_queryset(self):
        """Get activities queryset based on user role and team"""
        from apps.activities.models import Activity

        # Executives see all activities
        if self.is_sales_executive():
            return Activity.objects.all()

        # Managers see their team's activities
        if self.is_sales_manager() and self.sales_team:
            team_members = self.sales_team.get_team_members()
            return Activity.objects.filter(lead__assigned_to__in=team_members)

        # Sales reps see activities for their own leads
        return Activity.objects.filter(lead__assigned_to=self)


class Role(models.Model):
    """Role model for dynamic role management"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserRole(models.Model):
    """Many-to-many relationship between users and roles"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    
    class Meta:
        unique_together = ['user', 'role']
        ordering = ['assigned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class AppRegistry(models.Model):
    """Registry for installed apps and their metadata"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, default='default-icon.svg')
    url_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    required_roles = models.ManyToManyField(Role, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'display_name']
        verbose_name_plural = "App Registry"
    
    def __str__(self):
        return self.display_name
    
    def get_absolute_url(self):
        """Get the URL for this app"""
        try:
            return reverse(self.url_name)
        except:
            return '#'
    
    def user_has_access(self, user):
        """Check if user has access to this app"""
        if not self.is_active:
            return False
        
        if not self.required_roles.exists():
            return True
        
        user_role_names = user.user_roles.values_list('role__name', flat=True)
        required_role_names = self.required_roles.values_list('name', flat=True)
        
        return bool(set(user_role_names) & set(required_role_names))
    
    @classmethod
    def get_user_apps(cls, user):
        """Get all apps accessible to a user"""
        all_apps = cls.objects.filter(is_active=True)
        accessible_apps = []
        
        for app in all_apps:
            if app.user_has_access(user):
                accessible_apps.append(app)
        
        return accessible_apps