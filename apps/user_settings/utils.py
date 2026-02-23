from django.db import transaction
from .models import SettingsCategory, SettingsPage


def initialize_settings_navigation():
    """Initialize default settings navigation structure"""
    with transaction.atomic():
        # Create Dashboard category
        dashboard_cat, _ = SettingsCategory.objects.get_or_create(
            name='dashboard',
            defaults={
                'display_name': 'Dashboard',
                'description': 'Settings overview and quick access',
                'icon': 'fas fa-tachometer-alt',
                'order': 0,
            }
        )
        
        # Create Profile category
        profile_cat, _ = SettingsCategory.objects.get_or_create(
            name='profile',
            defaults={
                'display_name': 'Profile',
                'description': 'Personal settings and preferences',
                'icon': 'fas fa-user',
                'order': 1,
            }
        )
        
        # Create General category
        general_cat, _ = SettingsCategory.objects.get_or_create(
            name='general',
            defaults={
                'display_name': 'General',
                'description': 'System administration and management',
                'icon': 'fas fa-cog',
                'order': 2,
            }
        )
        
        # Create Profile pages
        profile_pages = [
            {
                'name': 'personal_info',
                'display_name': 'Personal Info',
                'description': 'Update your basic information',
                'url_name': 'settings:profile:personal_info',
                'icon': 'fas fa-id-card',
                'order': 0,
            },
            {
                'name': 'security',
                'display_name': 'Security',
                'description': 'Password and security settings',
                'url_name': 'settings:profile:security',
                'icon': 'fas fa-shield-alt',
                'order': 1,
            },
            {
                'name': 'preferences',
                'display_name': 'Preferences',
                'description': 'Customize your experience',
                'url_name': 'settings:profile:preferences',
                'icon': 'fas fa-sliders-h',
                'order': 2,
            },
        ]
        
        for page_data in profile_pages:
            SettingsPage.objects.get_or_create(
                category=profile_cat,
                name=page_data['name'],
                defaults=page_data
            )
        
        # Create General pages
        general_pages = [
            {
                'name': 'system_config',
                'display_name': 'System Config',
                'description': 'System-wide configuration settings',
                'url_name': 'settings:general:system_config',
                'icon': 'fas fa-server',
                'order': 0,
            },
            {
                'name': 'roles',
                'display_name': 'Role Management',
                'description': 'Create and manage user roles',
                'url_name': 'settings:general:roles',
                'icon': 'fas fa-users-cog',
                'order': 1,
            },
            {
                'name': 'users',
                'display_name': 'User Management',
                'description': 'Manage system users',
                'url_name': 'settings:users:list',
                'icon': 'fas fa-users',
                'order': 2,
            },
            {
                'name': 'app_registry',
                'display_name': 'App Registry',
                'description': 'Manage registered applications',
                'url_name': 'settings:general:app_registry',
                'icon': 'fas fa-th-list',
                'order': 3,
            },
        ]
        
        for page_data in general_pages:
            SettingsPage.objects.get_or_create(
                category=general_cat,
                name=page_data['name'],
                defaults=page_data
            )


def get_settings_breadcrumbs(section, page=None):
    """Generate breadcrumbs for settings navigation"""
    breadcrumbs = [
        {'name': 'Settings', 'url': 'settings:home'}
    ]
    
    if section == 'profile':
        breadcrumbs.append({'name': 'Profile', 'url': 'settings:profile:index'})
        if page:
            page_names = {
                'personal_info': 'Personal Info',
                'security': 'Security',
                'preferences': 'Preferences',
            }
            if page in page_names:
                breadcrumbs.append({'name': page_names[page], 'url': None})
    
    elif section == 'general':
        breadcrumbs.append({'name': 'General', 'url': 'settings:general:index'})
        if page:
            page_names = {
                'system_config': 'System Config',
                'roles': 'Role Management',
                'users': 'User Management',
                'app_registry': 'App Registry',
            }
            if page in page_names:
                breadcrumbs.append({'name': page_names[page], 'url': None})
    
    return breadcrumbs