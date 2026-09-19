from django.urls import include, path
from . import views

urlpatterns = [
    # Endpoints para agentes y usuarios autenticados
    path('sessions/',               views.SessionListCreateView.as_view(), name='crm-session-list'),
    path('sessions/pending-count/', views.PendingCountView.as_view(),      name='crm-pending-count'),
    path('sessions/<int:pk>/',      views.SessionDetailView.as_view(),     name='crm-session-detail'),
    path('sessions/<int:pk>/messages/', views.MessageListCreateView.as_view(), name='crm-messages'),
    
    # Endpoints públicos para el bot (ecommerce)
    path('bot/chat/',               views.BotChatView.as_view(),           name='bot-chat'),
    path('bot/sessions/<int:session_id>/messages/', views.BotSessionMessagesView.as_view(), name='bot-session-messages'),
    path('queues/', views.AssignmentQueueListCreateView.as_view(), name='crm-queue-list'),
    path('queues/<int:pk>/', views.AssignmentQueueDetailView.as_view(), name='crm-queue-detail'),
    path('whatsapp-web/', include('crmChat.apps.whatsapp_web.urls_admin')),
]
