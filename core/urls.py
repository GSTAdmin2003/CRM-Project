"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
import importlib
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from . import views
from .views import api

urlpatterns = [
    path('admin/', admin.site.urls),
    # Core API endpoints
    path('core/api/autocomplete/search/', api.api_autocomplete_search, name='api_autocomplete_search'),
    path('', views.redirect_to_dashboard, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.settings_profile_view, name='settings_profile'),
    path('settings/general/', views.settings_general_view, name='settings_general'),
    path('settings/voip/', views.settings_voip_view, name='settings_voip'),
]

# Dynamically include app URLs
apps_dir = os.path.join(settings.BASE_DIR, 'apps')
if os.path.exists(apps_dir):
    for item in os.listdir(apps_dir):
        app_path = os.path.join(apps_dir, item)

        # Skip if not a directory or if it's __pycache__
        if not os.path.isdir(app_path) or item.startswith('__'):
            continue

        # Skip user_settings - handled separately below
        if item == 'user_settings':
            continue

        # Check if app has urls.py
        urls_path = os.path.join(app_path, 'urls.py')
        if os.path.exists(urls_path):
            try:
                # Import and include app URLs
                app_urls = importlib.import_module(f'apps.{item}.urls')
                urlpatterns.append(path(f'{item}/', include(f'apps.{item}.urls', namespace=item)))
            except ImportError:
                pass


# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)