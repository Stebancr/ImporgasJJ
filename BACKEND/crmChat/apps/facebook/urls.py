"""Rutas opcionales del canal Facebook."""

from django.urls import path

from .views import FacebookWebhookView

urlpatterns = [path('webhook/', FacebookWebhookView.as_view(), name='facebook-webhook')]
