import os
import importlib
from django.apps import apps
from django.conf import settings
from .models import AppRegistry, Role


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to E.164 format (+XXXXXXXXX) on save.

    Reads the system default country code from SystemConfiguration
    (key: 'default_country_code') to handle local numbers without a prefix.

    Rules:
      - Empty/blank input → returned as-is (no change)
      - Already starts with '+' → strip non-digit chars, keep as E.164
      - Starts with '00' → treat as international prefix (00 → +)
      - Otherwise: prepend default country code if configured
        - Leading '0' (trunk prefix) is stripped before prepending cc
        - If number already starts with cc digits → just add '+'
    """
    if not phone or not phone.strip():
        return phone

    # Lazy import to avoid circular deps at module load time
    try:
        from apps.user_settings.models import SystemConfiguration
        default_cc = SystemConfiguration.get_setting("default_country_code", default="")
    except Exception:
        default_cc = ""

    cleaned = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )

    if cleaned.startswith("+"):
        return cleaned  # Already E.164

    if cleaned.startswith("00"):
        return "+" + cleaned[2:]  # International with 00 prefix

    if not default_cc:
        return phone  # Nothing to infer from — leave as entered

    cc = default_cc.strip().lstrip("+").lstrip("0")
    if not cc:
        return phone

    if cleaned.startswith(cc):
        return "+" + cleaned  # Already contains country code digits

    if cleaned.startswith("0"):
        return "+" + cc + cleaned[1:]  # Local trunk prefix — strip 0, prepend cc

    return "+" + cc + cleaned  # Bare local number — prepend cc


def discover_and_register_apps():
    """Discover apps in the apps directory and register them"""
    apps_dir = os.path.join(settings.BASE_DIR, 'apps')
    
    if not os.path.exists(apps_dir):
        return
    
    for item in os.listdir(apps_dir):
        app_path = os.path.join(apps_dir, item)
        
        # Skip if not a directory or if it's __pycache__
        if not os.path.isdir(app_path) or item.startswith('__'):
            continue
        
        # Check if it's a valid Django app (has __init__.py)
        if not os.path.exists(os.path.join(app_path, '__init__.py')):
            continue
        
        # Check if app has apps.py for configuration
        app_config_path = os.path.join(app_path, 'apps.py')
        if os.path.exists(app_config_path):
            try:
                # Import the app configuration
                module = importlib.import_module(f'apps.{item}.apps')
                
                # Look for app configuration class
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (hasattr(attr, '__bases__') and 
                        any('AppConfig' in base.__name__ for base in attr.__bases__)):
                        
                        # Get app metadata
                        config = attr()
                        display_name = getattr(config, 'verbose_name', item.title())
                        description = getattr(config, 'description', '')
                        icon = getattr(config, 'icon', 'default-icon.svg')
                        url_name = getattr(config, 'url_name', f'{item}:index')
                        
                        # Register or update app
                        app_registry, created = AppRegistry.objects.get_or_create(
                            name=item,
                            defaults={
                                'display_name': display_name,
                                'description': description,
                                'icon': icon,
                                'url_name': url_name,
                                'is_active': True,
                            }
                        )
                        
                        if created:
                            print(f"Registered new app: {display_name}")
                        
                        break
            except ImportError as e:
                print(f"Could not import app {item}: {e}")
                continue


def create_default_roles():
    """Create default roles if they don't exist"""
    default_roles = [
        {
            'name': 'Owner',
            'description': 'Full access to all system features and administration'
        },
    ]
    
    for role_data in default_roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={'description': role_data['description']}
        )
        if created:
            print(f"Created default role: {role.name}")


def setup_default_apps():
    """Setup default apps in the registry"""
    default_apps = [
        {
            'name': 'settings',
            'display_name': 'Settings',
            'description': 'System configuration and user management',
            'icon': 'settings-icon.svg',
            'url_name': 'settings:home',
            'required_roles': ['Owner'],
        },
    ]
    
    for app_data in default_apps:
        app_registry, created = AppRegistry.objects.get_or_create(
            name=app_data['name'],
            defaults={
                'display_name': app_data['display_name'],
                'description': app_data['description'],
                'icon': app_data['icon'],
                'url_name': app_data['url_name'],
                'is_active': False,  # Will be activated when app is actually created
            }
        )
        
        if created and 'required_roles' in app_data:
            # Add required roles
            for role_name in app_data['required_roles']:
                try:
                    role = Role.objects.get(name=role_name)
                    app_registry.required_roles.add(role)
                except Role.DoesNotExist:
                    pass