"""Rutas WebSocket de la aplicación CRM."""

from django.urls import path

from .consumers import CRMInboxConsumer, CustomerChatConsumer

websocket_urlpatterns = [
    path('ws/crm-chat/', CRMInboxConsumer.as_asgi(), name='ws-crm-chat'),
    path('ws/crm-chat/sessions/<int:session_id>/', CustomerChatConsumer.as_asgi(), name='ws-customer-chat'),
]
