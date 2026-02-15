from django.views.generic import TemplateView, UpdateView, CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, path
from django.shortcuts import redirect
from django.contrib import messages
from .base import SettingsBaseMixin
from ..models import SIPSettings
from ..forms import SIPSettingsForm


class VoIPIndexView(SettingsBaseMixin, TemplateView):
    """VoIP settings overview page"""
    template_name = 'settings/voip/index.html'
    settings_section = 'voip'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['sip_settings'] = self.request.user.sip_settings
        except SIPSettings.DoesNotExist:
            context['sip_settings'] = None
        return context


class SIPSettingsView(SettingsBaseMixin, SuccessMessageMixin, UpdateView):
    """Edit SIP credentials"""
    model = SIPSettings
    form_class = SIPSettingsForm
    template_name = 'settings/voip/sip_credentials.html'
    success_message = "SIP credentials updated successfully."
    success_url = reverse_lazy('settings:voip:sip_credentials')
    settings_section = 'voip'
    settings_page = 'sip_credentials'

    def get_object(self, queryset=None):
        # Get or create SIP settings for current user
        obj, created = SIPSettings.objects.get_or_create(
            user=self.request.user,
            defaults={
                'server_ip': '',
                'username': '',
                'password': '',
                'caller_id': '',
            }
        )
        return obj

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class SIPSettingsDeleteView(SettingsBaseMixin, TemplateView):
    """Delete SIP credentials"""
    template_name = 'settings/voip/sip_credentials.html'
    settings_section = 'voip'

    def post(self, request, *args, **kwargs):
        try:
            sip_settings = request.user.sip_settings
            sip_settings.delete()
            messages.success(request, "SIP credentials deleted successfully.")
        except SIPSettings.DoesNotExist:
            messages.error(request, "No SIP credentials found.")
        return redirect('settings:voip:index')


# URL patterns for VoIP section
voip_urls = [
    path('', VoIPIndexView.as_view(), name='index'),
    path('sip-credentials/', SIPSettingsView.as_view(), name='sip_credentials'),
    path('sip-credentials/delete/', SIPSettingsDeleteView.as_view(), name='sip_credentials_delete'),
]
