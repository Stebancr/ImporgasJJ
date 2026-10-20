from django.urls import path
from .views import DocumentView, RenewLinkView, DeliveryAuditView, RetryDeliveryView

urlpatterns = [path('documents/<uuid:pk>/',DocumentView.as_view(),name='transactional-document'),
               path('documents/<uuid:pk>/renew/',RenewLinkView.as_view(),name='transactional-document-renew'),
               path('deliveries/',DeliveryAuditView.as_view(),name='transactional-audit'),
               path('deliveries/<uuid:pk>/retry/',RetryDeliveryView.as_view(),name='transactional-retry')]
