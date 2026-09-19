from django.urls import path
from .views import GatewayCommandView, GatewayRealtimeTokenView, GatewayStatusView, ProtectedAttachmentView

urlpatterns = [
    path('status/', GatewayStatusView.as_view(), name='whatsapp-web-status'),
    path('realtime-token/', GatewayRealtimeTokenView.as_view(), name='whatsapp-web-realtime-token'),
    path('commands/<str:command>/', GatewayCommandView.as_view(), name='whatsapp-web-command'),
    path('attachments/<int:pk>/', ProtectedAttachmentView.as_view(), name='whatsapp-web-attachment'),
]
