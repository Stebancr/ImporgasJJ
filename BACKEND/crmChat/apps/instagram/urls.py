"""Rutas opcionales del canal Instagram."""

from django.urls import path

from .views import InstagramOAuthCallbackView, InstagramOAuthStartView, InstagramWebhookView

urlpatterns = [
    path('webhook/', InstagramWebhookView.as_view(), name='instagram-webhook'),
    path('oauth/callback/', InstagramOAuthCallbackView.as_view(), name='instagram-oauth-callback'),
    path('integrations/<int:pk>/oauth/start/', InstagramOAuthStartView.as_view(), name='instagram-oauth-start'),
]
