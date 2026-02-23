from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/messaging/<int:pk>/', consumers.ChatConsumer.as_asgi()),
]
