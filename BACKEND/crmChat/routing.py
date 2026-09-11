"""Rutas WebSocket de la aplicación CRM."""

from django.urls import path

from .consumers import CRMInboxConsumer

websocket_urlpatterns = [
    path('ws/crm-chat/', CRMInboxConsumer.as_asgi(), name='ws-crm-chat'),
]
