from django.core.management.base import BaseCommand
from django.db import transaction
from user_settings.utils import initialize_settings_navigation
from user_settings.models import SystemConfiguration


class Command(BaseCommand):
    help = 'Initialize settings app with default navigation and configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing settings app...'))
        
        # Initialize settings navigation
        initialize_settings_navigation()
        self.stdout.write(self.style.SUCCESS('✓ Settings navigation initialized'))
        
        # Create default system configurations
        default_configs = [
            {
                'key': 'site_name',
                'value': 'CRM System',
                'description': 'Name of the site displayed in headers and titles',
                'data_type': 'string',
                'is_public': True,
            },
            {
                'key': 'site_description',
                'value': 'Customer Relationship Management System',
                'description': 'Brief description of the site',
                'data_type': 'string',
                'is_public': True,
            },
            {
                'key': 'maintenance_mode',
                'value': 'false',
                'description': 'Enable maintenance mode to restrict access',
                'data_type': 'boolean',
                'is_public': False,
            },
            {
                'key': 'max_upload_size',
                'value': '10485760',  # 10MB
                'description': 'Maximum file upload size in bytes',
                'data_type': 'integer',
                'is_public': False,
            },
            {
                'key': 'session_timeout',
                'value': '7200',  # 2 hours
                'description': 'User session timeout in seconds',
                'data_type': 'integer',
                'is_public': False,
            },
        ]
        
        with transaction.atomic():
            for config_data in default_configs:
                config, created = SystemConfiguration.objects.get_or_create(
                    key=config_data['key'],
                    defaults=config_data
                )
                if created:
                    self.stdout.write(f'✓ Created configuration: {config.key}')
                else:
                    self.stdout.write(f'- Configuration already exists: {config.key}')
        
        self.stdout.write(self.style.SUCCESS('Settings app initialization complete!'))