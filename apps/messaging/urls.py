from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.messaging.views import api_views, template_views

router = DefaultRouter()
router.register(r"conversations", api_views.ConversationViewSet, basename="conversation")
router.register(r"templates", api_views.TemplateViewSet, basename="template")

app_name = "messaging"

urlpatterns = [
    # DRF API endpoints
    path("api/", include(router.urls)),
    # Messaging is only accessible from leads — these redirect to /crm/opportunities/
    path("", template_views.inbox, name="inbox"),
    path("<int:pk>/", template_views.conversation_detail, name="conversation_detail"),
    # Utility endpoints (still needed)
    path("webhook/", template_views.webhook, name="webhook"),
    path("check-whatsapp/", template_views.check_whatsapp_phone, name="check_whatsapp_phone"),
    path("templates/<int:pk>/variables/", template_views.template_variables_api, name="template_variables"),
]
