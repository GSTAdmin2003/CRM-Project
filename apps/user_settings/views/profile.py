from django.views.generic import UpdateView, TemplateView
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, path
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from .base import SettingsBaseMixin
from ..forms import ProfileUpdateForm, UserPreferencesForm, CustomPasswordChangeForm
from ..models import UserPreferences

User = get_user_model()


class ProfilePersonalInfoView(SettingsBaseMixin, SuccessMessageMixin, UpdateView):
    """View for updating personal information"""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'settings/profile/personal_info.html'
    success_message = "Your personal information has been updated successfully."
    success_url = reverse_lazy('settings:profile:personal_info')
    settings_section = 'profile'
    settings_page = 'personal_info'
    
    def get_object(self):
        return self.request.user


class ProfileSecurityView(SettingsBaseMixin, SuccessMessageMixin, PasswordChangeView):
    """View for changing password"""
    form_class = CustomPasswordChangeForm
    template_name = 'settings/profile/security.html'
    success_message = "Your password has been changed successfully."
    success_url = reverse_lazy('settings:profile:security')
    settings_section = 'profile'
    settings_page = 'security'


class ProfilePreferencesView(SettingsBaseMixin, SuccessMessageMixin, UpdateView):
    """View for updating user preferences"""
    model = UserPreferences
    form_class = UserPreferencesForm
    template_name = 'settings/profile/preferences.html'
    success_message = "Your preferences have been updated successfully."
    success_url = reverse_lazy('settings:profile:preferences')
    settings_section = 'profile'
    settings_page = 'preferences'
    
    def get_object(self):
        return UserPreferences.get_or_create_for_user(self.request.user)


class ProfileIndexView(SettingsBaseMixin, TemplateView):
    """Profile overview page"""
    template_name = 'settings/profile/index.html'
    settings_section = 'profile'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['preferences'] = UserPreferences.get_or_create_for_user(self.request.user)
        return context


# URL patterns for profile section
profile_urls = [
    path('', ProfileIndexView.as_view(), name='index'),
    path('personal-info/', ProfilePersonalInfoView.as_view(), name='personal_info'),
    path('security/', ProfileSecurityView.as_view(), name='security'),
    path('preferences/', ProfilePreferencesView.as_view(), name='preferences'),
]