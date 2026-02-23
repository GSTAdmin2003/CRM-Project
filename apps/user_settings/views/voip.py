from django.urls import path
from apps.calls.views.template_views import sip_settings_view

voip_urls = [
    path('sip-credentials/', sip_settings_view, name='sip_credentials'),
]
