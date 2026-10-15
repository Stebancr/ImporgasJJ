from django.urls import path
from .views import ShippingConfigView, CityListView, QuoteView, ShipmentActionView

urlpatterns = [
    path('config', ShippingConfigView.as_view(), name='shipping-config'),
    path('cities', CityListView.as_view(), name='shipping-cities'),
    path('quote', QuoteView.as_view(), name='shipping-quote'),
    path('orders/<int:order_id>/<str:action>', ShipmentActionView.as_view(), name='shipping-action'),
]
