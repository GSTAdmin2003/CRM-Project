# CRM System - Django ERP Foundation

A lightweight Django-based CRM/ERP system designed as a modular foundation with authentication, role-based access control, and a beautiful dashboard interface.

## Features

- **Authentication**: Django built-in authentication with invite-only access
- **Role System**: Dynamic, configurable roles with UI management capability
- **Modular Architecture**: Support for pluggable Django apps in isolated modules
- **Beautiful Dashboard**: 6-column grid layout inspired by modern ERP systems
- **Docker Support**: Full containerized development environment
- **PostgreSQL**: Production-ready database backend
- **Tailwind CSS**: Modern, responsive UI framework

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. **Clone and navigate to project**:
   ```bash
   cd "/path/to/CRM Project"
   ```

2. **Build and start containers**:
   ```bash
   docker compose build
   docker compose up -d db
   ```

3. **Run migrations and setup system**:
   ```bash
   docker compose run --rm web python manage.py migrate
   docker compose run --rm web python manage.py setup_system
   ```

4. **Create admin user**:
   ```bash
   docker compose run --rm web python manage.py createsuperuser
   ```

5. **Start the application**:
   ```bash
   docker compose up
   ```

6. **Access the application**:
   - Dashboard: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

## Project Structure

```
CRM Project/
├── core/                      # Main Django project & core functionality
│   ├── models.py             # User, Role, AppRegistry models
│   ├── views.py              # Authentication & dashboard views
│   ├── utils.py              # App discovery utilities
│   ├── middleware.py         # Role-based access control
│   └── management/
│       └── commands/
│           └── setup_system.py  # System setup command
├── apps/                     # Directory for modular apps
│   └── __init__.py
├── templates/
│   ├── base.html            # Base layout template
│   ├── core/
│   │   └── dashboard.html   # Main dashboard
│   └── registration/
│       ├── login.html       # Login page
│       └── logged_out.html  # Logout page
├── static/
│   ├── css/
│   │   └── dashboard.css    # Dashboard styling
│   ├── js/
│   └── icons/               # App icons directory
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Django app container
└── requirements.txt        # Python dependencies
```

## Key Models

### User Model
- Extended Django User with role support
- Email-based authentication
- Timestamps and role checking methods

### Role System
- **Role**: Dynamic role definitions
- **UserRole**: Many-to-many relationship with assignment tracking
- **AppRegistry**: App registration for dashboard display

### App Registry
- Automatic app discovery
- Role-based access control
- Dashboard integration

## Adding New Apps

1. **Create app in apps directory**:
   ```bash
   cd apps/
   django-admin startapp your_app_name
   ```

2. **Add to INSTALLED_APPS** in `core/settings.py`:
   ```python
   INSTALLED_APPS = [
       # ... existing apps
       'your_app_name',
   ]
   ```

3. **Create app configuration** in `apps/your_app_name/apps.py`:
   ```python
   from django.apps import AppConfig

   class YourAppNameConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'your_app_name'
       verbose_name = 'Your App Display Name'
       description = 'Description of your app'
       icon = 'your-app-icon.svg'
       url_name = 'your_app_name:index'
   ```

4. **Register app in dashboard**:
   ```bash
   docker compose run --rm web python manage.py setup_system
   ```

## Role-Based Access Control

The system includes middleware for role-based access control:

- **Public URLs**: Login, admin login
- **Protected URLs**: All other URLs require authentication
- **Role-specific access**: Apps can define required roles

### Managing Roles

1. Access admin panel: http://localhost:8000/admin
2. Navigate to "Roles" section
3. Create/modify roles as needed
4. Assign roles to users via "User roles"

## Dashboard Features

- **Responsive Grid**: 6 columns on desktop, adapts to mobile
- **App Cards**: Clean design with hover effects
- **Auto-discovery**: New apps appear automatically
- **Role filtering**: Users only see permitted apps
- **Demo Mode**: Shows sample apps when no real apps are configured

## Development

### Hot Reloading

The development setup includes hot reloading:
```bash
docker compose up  # File changes trigger auto-reload
```

### Database

- **Service**: PostgreSQL 15
- **Port**: 5433 (mapped from container's 5432)
- Credentials are configured via `.env` file (see `.env.example`)

### Management Commands

- `python manage.py setup_system`: Initialize roles and apps
- `python manage.py setup_system --create-admin`: Also create admin user

## Customization

### Styling

- **Framework**: Tailwind CSS (CDN)
- **Custom CSS**: `static/css/dashboard.css`
- **Icons**: Emoji-based (easily replaceable)

### Templates

- **Base Template**: `templates/base.html`
- **Dashboard**: `templates/core/dashboard.html`
- **Auth**: `templates/registration/`

## Production Considerations

1. **Security**:
   - Change `SECRET_KEY` in production
   - Set `DEBUG=False`
   - Configure proper `ALLOWED_HOSTS`

2. **Database**:
   - Use managed PostgreSQL service
   - Set up backups
   - Configure SSL

3. **Static Files**:
   - Use CDN for static files
   - Configure `STATIC_ROOT` properly

4. **Environment Variables**:
   - Copy `.env.example` to `.env`
   - Set production values

## License

This project is a foundation for your ERP/CRM system. Modify as needed for your requirements.