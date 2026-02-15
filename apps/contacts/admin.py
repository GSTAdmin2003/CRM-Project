from django.contrib import admin
from .models import Company, Contact


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['legal_name', 'legal_id', 'brand_name', 'industry', 'category', 'created_at']
    list_filter = ['industry', 'category', 'created_at']
    search_fields = ['legal_name', 'brand_name', 'legal_id', 'company_email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('legal_id', 'legal_name', 'brand_name')
        }),
        ('Classification', {
            'fields': ('industry', 'category')
        }),
        ('Contact Information', {
            'fields': ('company_email', 'company_phone', 'company_mobile')
        }),
        ('System Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'company', 'email', 'phone', 'mobile']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'position', 'email', 'company__legal_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'position')
        }),
        ('Company', {
            'fields': ('company',)
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'mobile')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )