from django.urls import path
from . import views

urlpatterns = [
    path('sessions/',               views.SessionListCreateView.as_view(), name='crm-session-list'),
    path('sessions/pending-count/', views.PendingCountView.as_view(),      name='crm-pending-count'),
    path('sessions/<int:pk>/',      views.SessionDetailView.as_view(),     name='crm-session-detail'),
    path('sessions/<int:pk>/messages/', views.MessageListCreateView.as_view(), name='crm-messages'),
]
