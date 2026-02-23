from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, path
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from .base import SettingsBaseMixin
from ..models import SystemConfiguration
from ..forms import SystemConfigurationForm
from core.models import Role, UserRole, AppRegistry

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
        context['system_configs_count'] = SystemConfiguration.objects.count()
        context['roles_count'] = Role.objects.count()
        context['users_count'] = User.objects.count()
        context['apps_count'] = AppRegistry.objects.count()
        context['current_cc'] = SystemConfiguration.get_setting("default_country_code", default="")
        return context


class SystemConfigView(SettingsBaseMixin, AdminRequiredMixin, ListView):
    """System configuration management"""
    model = SystemConfiguration
    template_name = 'settings/general/system_config.html'
    context_object_name = 'configurations'
    paginate_by = 20
    settings_section = 'general'
    settings_page = 'system_config'
    
    def get_queryset(self):
        return SystemConfiguration.objects.order_by('key')


class SystemConfigUpdateView(SettingsBaseMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update system configuration"""
    model = SystemConfiguration
    form_class = SystemConfigurationForm
    template_name = 'settings/general/system_config_form.html'
    success_message = "Configuration updated successfully."
    success_url = reverse_lazy('settings:general:system_config')
    settings_section = 'general'
    settings_page = 'system_config'
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class SystemConfigCreateView(SettingsBaseMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new system configuration"""
    model = SystemConfiguration
    form_class = SystemConfigurationForm
    template_name = 'settings/general/system_config_form.html'
    success_message = "Configuration created successfully."
    success_url = reverse_lazy('settings:general:system_config')
    settings_section = 'general'
    settings_page = 'system_config'
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class RoleManagementView(SettingsBaseMixin, AdminRequiredMixin, ListView):
    """Role management page"""
    model = Role
    template_name = 'settings/general/roles.html'
    context_object_name = 'roles'
    settings_section = 'general'
    settings_page = 'roles'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        return context


class AppRegistryView(SettingsBaseMixin, AdminRequiredMixin, ListView):
    """App registry management page"""
    model = AppRegistry
    template_name = 'settings/general/app_registry.html'
    context_object_name = 'apps'
    settings_section = 'general'
    settings_page = 'app_registry'
    
    def get_queryset(self):
        return AppRegistry.objects.prefetch_related('required_roles').order_by('order', 'display_name')


# URL patterns for general section
general_urls = [
    path('', GeneralIndexView.as_view(), name='index'),
    path('phone-settings/', PhoneSettingsView.as_view(), name='phone_settings'),
    path('system-config/', SystemConfigView.as_view(), name='system_config'),
    path('system-config/create/', SystemConfigCreateView.as_view(), name='system_config_create'),
    path('system-config/<int:pk>/edit/', SystemConfigUpdateView.as_view(), name='system_config_edit'),
    path('roles/', RoleManagementView.as_view(), name='roles'),
    path('app-registry/', AppRegistryView.as_view(), name='app_registry'),
]