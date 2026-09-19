from django.urls import path
from .views import InternalMediaView, InternalStatusView, InternalWebhookView

urlpatterns = [
    path('webhook/', InternalWebhookView.as_view(), name='whatsapp-web-internal-webhook'),
    path('status/', InternalStatusView.as_view(), name='whatsapp-web-internal-status'),
    path('media/', InternalMediaView.as_view(), name='whatsapp-web-internal-media'),
]
