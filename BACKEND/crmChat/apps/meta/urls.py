"""Rutas del webhook unificado y de configuración Meta."""

from django.urls import path

from .views import IntegrationDetailView, IntegrationListCreateView, IntegrationValidateView, MetaWebhookView

urlpatterns = [
    path('webhook/', MetaWebhookView.as_view(), name='meta-webhook'),
    path('integrations/', IntegrationListCreateView.as_view(), name='meta-integrations'),
    path('integrations/<int:pk>/', IntegrationDetailView.as_view(), name='meta-integration-detail'),
    path('integrations/<int:pk>/validate/', IntegrationValidateView.as_view(), name='meta-integration-validate'),
]
