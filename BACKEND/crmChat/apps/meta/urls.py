"""Rutas del webhook unificado y de configuración Meta."""

from django.urls import path

from .views import (
    IntegrationDetailView,
    IntegrationListCreateView,
    IntegrationValidateView,
    MetaConnectView,
    MetaConnectionAccountsView,
    MetaConnectionDetailView,
    MetaConnectionListView,
    MetaOAuthCallbackView,
    MetaWebhookView,
    WhatsAppCoexistenceCompleteView,
    WhatsAppCoexistenceConfigView,
)

urlpatterns = [
    path('webhook/', MetaWebhookView.as_view(), name='meta-webhook'),
    path('connect/', MetaConnectView.as_view(), name='meta-connect'),
    path('callback/', MetaOAuthCallbackView.as_view(), name='meta-callback'),
    path('connections/', MetaConnectionListView.as_view(), name='meta-connections'),
    path('connections/<int:pk>/', MetaConnectionDetailView.as_view(), name='meta-connection-detail'),
    path('connections/<int:pk>/accounts/', MetaConnectionAccountsView.as_view(), name='meta-connection-accounts'),
    path('integrations/', IntegrationListCreateView.as_view(), name='meta-integrations'),
    path('integrations/<int:pk>/', IntegrationDetailView.as_view(), name='meta-integration-detail'),
    path('integrations/<int:pk>/validate/', IntegrationValidateView.as_view(), name='meta-integration-validate'),
    path('whatsapp/coexistence/config/', WhatsAppCoexistenceConfigView.as_view(), name='whatsapp-coexistence-config'),
    path('whatsapp/coexistence/complete/', WhatsAppCoexistenceCompleteView.as_view(), name='whatsapp-coexistence-complete'),
]
