from django.urls import path

from apps.messaging.views import template_views

app_name = "messaging"

urlpatterns = [
    path("", template_views.inbox, name="inbox"),
    path("<int:pk>/", template_views.conversation_detail, name="conversation_detail"),
    path("<int:pk>/messages/", template_views.messages_partial, name="messages_partial"),
    path("<int:pk>/send/", template_views.send_message, name="send_message"),
    path("webhook/", template_views.webhook, name="webhook"),
    path("check-whatsapp/", template_views.check_whatsapp_phone, name="check_whatsapp_phone"),
    path("templates/<int:pk>/variables/", template_views.template_variables_api, name="template_variables"),
]
