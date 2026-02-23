from django.urls import path
from apps.calls.views.template_views import voip_config_view, voip_sounds_view, voip_working_hours_view

voip_urls = [
    path('config/', voip_config_view, name='voip_config'),
    path('sounds/', voip_sounds_view, name='voip_sounds'),
    path('working-hours/', voip_working_hours_view, name='voip_working_hours'),
]
