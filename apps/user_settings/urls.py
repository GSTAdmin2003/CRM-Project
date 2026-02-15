from django.urls import path, include
from .views.base import SettingsHomeView
from .views.profile import profile_urls
from .views.general import general_urls
from .views.crm import crm_urls
from .views.voip import voip_urls

app_name = 'settings'

profile_patterns = (profile_urls, 'profile')
general_patterns = (general_urls, 'general')
crm_patterns = (crm_urls, 'crm')
voip_patterns = (voip_urls, 'voip')

urlpatterns = [
    path('', SettingsHomeView.as_view(), name='home'),
    path('profile/', include(profile_patterns)),
    path('general/', include(general_patterns)),
    path('crm/', include(crm_patterns)),
    path('voip/', include(voip_patterns)),
]