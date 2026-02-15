from django.contrib import admin
from .models import SalesTeam, Lead, LeadStage, LeadActivity, LeadFile


@admin.register(SalesTeam)
class SalesTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(LeadStage)
class LeadStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'probability', 'color', 'is_active', 'is_closed_stage']
    list_filter = ['is_active', 'is_closed_stage']
    ordering = ['order']
    list_editable = ['order', 'probability', 'is_active']


class LeadActivityInline(admin.TabularInline):
    model = LeadActivity
    extra = 0
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'full_name', 'company_name', 'stage', 'estimated_value', 
        'probability', 'assigned_to', 'created_at'
    ]
    list_filter = [
        'stage', 'source', 'status', 'assigned_to', 'sales_team', 
        'created_at', 'expected_close_date'
    ]
    search_fields = [
        'title', 'first_name', 'last_name', 'email', 'company_name', 'phone'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_activity']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', ('first_name', 'last_name'), 'email', 'phone')
        }),
        ('Company Information', {
            'fields': ('company_name', 'position', 'company', 'contact')
        }),
        ('Sales Information', {
            'fields': (
                'stage', ('estimated_value', 'probability'), 
                'expected_close_date', ('source', 'status')
            )
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'sales_team')
        }),
        ('Additional Information', {
            'fields': ('notes', 'custom_fields'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',),
            'description': 'System tracking fields'
        })
    )
    
    inlines = [LeadActivityInline]
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['lead', 'activity_type', 'subject', 'user', 'created_at']
    list_filter = ['activity_type', 'created_at', 'user']
    search_fields = ['lead__title', 'subject', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at']


@admin.register(LeadFile)
class LeadFileAdmin(admin.ModelAdmin):
    list_display = ['lead', 'filename', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['lead__title', 'filename', 'description']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']