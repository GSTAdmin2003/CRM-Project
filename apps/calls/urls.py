from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import call_views, template_views

router = DefaultRouter()
router.register(r"calls", call_views.CallViewSet, basename="call-api")

app_name = "calls"

urlpatterns = [
    # DRF API endpoints
    path("api/", include(router.urls)),
    # Existing template views
    path("", template_views.call_list, name="call_list"),
    path("dialpad/", template_views.dialpad, name="dialpad"),
    path("<int:pk>/", template_views.call_detail, name="call_detail"),
    # Call actions (template views)
    path("initiate/", template_views.initiate_call, name="initiate_call"),
    path("<int:pk>/hangup/", template_views.hangup_call, name="hangup_call"),
    path("<int:pk>/answer/", template_views.answer_call, name="answer_call"),
    path("<int:pk>/status/", template_views.call_status, name="call_status"),
    # Call management (template views)
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
    # Legacy API endpoint (kept for backward compatibility)
    path("api/active/", template_views.active_calls, name="active_calls"),
]
