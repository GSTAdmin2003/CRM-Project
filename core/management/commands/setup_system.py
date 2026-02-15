from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Role, UserRole
from core.utils import create_default_roles, setup_default_apps, discover_and_register_apps

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup the ERP system with default roles, apps, and admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='Create an admin user',
        )

    def handle(self, **options):
        self.stdout.write(self.style.SUCCESS('Setting up ERP system...'))
        
        # Create default roles
        self.stdout.write('Creating default roles...')
        create_default_roles()
        
        # Setup default apps
        self.stdout.write('Setting up default apps...')
        setup_default_apps()
        
        # Discover and register apps
        self.stdout.write('Discovering apps...')
        discover_and_register_apps()
        
        # Create admin user if requested
        if options['create_admin']:
            self.create_admin_user()
        
        self.stdout.write(self.style.SUCCESS('System setup completed!'))

    def create_admin_user(self):
        """Create an admin user with Owner role"""
        username = input('Admin username: ')
        email = input('Admin email: ')
        password = input('Admin password: ')
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
            return
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        # Assign Owner role
        try:
            owner_role = Role.objects.get(name='Owner')
            UserRole.objects.create(user=user, role=owner_role)
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {username} with Owner role'))
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('Owner role not found'))