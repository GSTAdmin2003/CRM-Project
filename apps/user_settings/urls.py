from django.urls import path, include
from .views.base import SettingsHomeView
from .views.profile import profile_urls
from .views.general import general_urls
from .views.crm import crm_urls
from .views.voip import voip_urls
from .views.users import users_urls
from .views.whatsapp import whatsapp_urls
from .views.elevenlabs import elevenlabs_urls

app_name = 'settings'

profile_patterns = (profile_urls, 'profile')
general_patterns = (general_urls, 'general')
crm_patterns = (crm_urls, 'crm')
voip_patterns = (voip_urls, 'voip')
users_patterns = (users_urls, 'users')
whatsapp_patterns = (whatsapp_urls, 'whatsapp')
elevenlabs_patterns = (elevenlabs_urls, 'elevenlabs')

urlpatterns = [
    path('', SettingsHomeView.as_view(), name='home'),
    path('profile/', include(profile_patterns)),
    path('general/', include(general_patterns)),
    path('crm/', include(crm_patterns)),
    path('voip/', include(voip_patterns)),
    path('general/users/', include(users_patterns)),
    path('whatsapp/', include(whatsapp_patterns)),
    path('elevenlabs/', include(elevenlabs_patterns)),
]