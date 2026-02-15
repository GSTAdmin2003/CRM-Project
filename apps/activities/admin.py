from django.contrib import admin
from .models import ActivityType, Activity


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Activity Type Information', {
            'fields': ('name', 'icon', 'color', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'lead', 'activity_type', 'scheduled_date', 'status', 'assigned_to', 'created_at']
    list_filter = ['activity_type', 'status', 'assigned_to', 'scheduled_date', 'created_at']
    search_fields = ['title', 'description', 'lead__title', 'lead__full_name']
    readonly_fields = ['created_by', 'created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'scheduled_date'

    fieldsets = (
        ('Activity Information', {
            'fields': ('activity_type', 'title', 'description')
        }),
        ('Assignment', {
            'fields': ('lead', 'assigned_to', 'scheduled_date', 'status')
        }),
        ('Outcome', {
            'fields': ('outcome', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
