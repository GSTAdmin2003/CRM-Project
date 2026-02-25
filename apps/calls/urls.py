from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import call_views, template_views

router = DefaultRouter()
router.register(r"calls", call_views.CallViewSet, basename="call-api")

app_name = "calls"

urlpatterns = [
    # DRF API endpoints
    path("api/", include(router.urls)),
    # Internal call action endpoints (used by JS / WebRTC layer)
    path("initiate/", template_views.initiate_call, name="initiate_call"),
    path("inbound/lookup/", template_views.lookup_inbound_call, name="lookup_inbound_call"),
    path("inbound/register/", template_views.register_inbound_call, name="register_inbound_call"),
    path("inbound/missed/", template_views.record_missed_call, name="record_missed_call"),
    path("<int:pk>/ended/", template_views.call_ended, name="call_ended"),
    path("<int:pk>/hangup/", template_views.hangup_call, name="hangup_call"),
    path("<int:pk>/answer/", template_views.answer_call, name="answer_call"),
    path("<int:pk>/status/", template_views.call_status, name="call_status"),
    path("<int:pk>/notes/", template_views.update_call_notes, name="update_call_notes"),
    path(
        "<int:pk>/link-contact/",
        template_views.link_call_to_contact,
        name="link_call_to_contact",
    ),
    path(
        "<int:pk>/link-opportunity/",
        template_views.link_call_to_opportunity,
        name="link_call_to_opportunity",
    ),
    # Recording
    path(
        "recording/<int:pk>/download/",
        template_views.recording_download,
        name="recording_download",
    ),
    # Transcription
    path("<int:pk>/transcript/start/", template_views.start_transcription, name="start_transcription"),
    path("<int:pk>/transcript/cancel/", template_views.cancel_transcription, name="cancel_transcription"),
    # AI Analysis
    path("<int:pk>/analysis/start/", template_views.start_ai_analysis, name="start_ai_analysis"),
    path("<int:pk>/analysis/status/", template_views.ai_analysis_status, name="ai_analysis_status"),
    path("<int:pk>/analysis/cancel/", template_views.cancel_ai_analysis, name="cancel_ai_analysis"),
    # Legacy API endpoint (kept for backward compatibility)
    path("api/active/", template_views.active_calls, name="active_calls"),
    # SIP settings (accessed via user settings, but route kept here)
    path("sip-settings/", template_views.sip_settings_view, name="sip_settings"),
]
