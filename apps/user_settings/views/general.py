from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import path
from django.views import View
from django.views.generic import TemplateView
from .base import SettingsBaseMixin
from ..models import SystemConfiguration
from core.models import Role, AppRegistry

User = get_user_model()


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only admins can access general settings"""
    
    def test_func(self):
        return self.request.user.has_role('Owner') or self.request.user.is_staff


class PhoneSettingsView(SettingsBaseMixin, AdminRequiredMixin, View):
    """Save the system-wide default country code for phone number normalization."""

    settings_section = "general"
    settings_page = "phone_settings"

    def post(self, request, *args, **kwargs):
        cc = request.POST.get("default_country_code", "").strip().lstrip("+").lstrip("0")
        if cc:
            SystemConfiguration.set_setting(
                key="default_country_code",
                value=cc,
                description=(
                    "Default country calling code used to normalize local phone numbers "
                    "(digits only, e.g. 995 for Georgia)."
                ),
                data_type="string",
                user=request.user,
            )
            messages.success(request, f"Default country code set to +{cc}.")
        else:
            messages.error(request, "Please enter a valid country code (digits only).")
        return redirect("settings:general:index")


class GeneralIndexView(SettingsBaseMixin, AdminRequiredMixin, TemplateView):
    """General settings overview page"""
    template_name = 'settings/general/index.html'
    settings_section = 'general'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles_count'] = Role.objects.count()
        context['users_count'] = User.objects.count()
        context['apps_count'] = AppRegistry.objects.count()
        context['current_cc'] = SystemConfiguration.get_setting("default_country_code", default="")
        return context








_LANG_CHOICES = [('en', 'English'), ('ka', 'Georgian')]


class PreferredLanguageView(SettingsBaseMixin, AdminRequiredMixin, TemplateView):
    """System-wide default preferred language setting."""

    settings_section = 'general'
    settings_page = 'preferred_language'
    template_name = 'settings/general/preferred_language.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = SystemConfiguration.get_setting('default_preferred_language', 'en')
        context['language_choices'] = _LANG_CHOICES
        return context

    def post(self, request, *args, **kwargs):
        language = request.POST.get('preferred_language', '').strip()
        if language in dict(_LANG_CHOICES):
            SystemConfiguration.set_setting(
                key='default_preferred_language',
                value=language,
                description='Default preferred language for communications.',
                data_type='string',
                user=request.user,
            )
            messages.success(request, 'Default preferred language updated.')
        else:
            messages.error(request, 'Invalid language selection.')
        return redirect('settings:general:preferred_language')


# URL patterns for general section
general_urls = [
    path('', GeneralIndexView.as_view(), name='index'),
    path('phone-settings/', PhoneSettingsView.as_view(), name='phone_settings'),
    path('preferred-language/', PreferredLanguageView.as_view(), name='preferred_language'),
]