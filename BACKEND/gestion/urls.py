from django.urls import path
from . import views

urlpatterns = [
    # ── Mi sede / asignación ──────────────────────────────────────────────────
    path('mi-sede', views.MiSedeView.as_view(), name='gestion-mi-sede'),
    path('asignar-sede', views.AsignarSedeView.as_view(), name='gestion-asignar-sede'),

    # ── Stock por sede ────────────────────────────────────────────────────────
    path('stock', views.StockSedeView.as_view(), name='gestion-stock-list'),
    path('stock/<int:product_id>', views.StockSedeView.as_view(), name='gestion-stock-detail'),

    # ── Cotizaciones ──────────────────────────────────────────────────────────
    path('cotizaciones', views.CotizacionListView.as_view(), name='gestion-cotizacion-list'),
    path('cotizaciones/<int:pk>', views.CotizacionDetailView.as_view(), name='gestion-cotizacion-detail'),
    path('cotizaciones/<int:pk>/convertir', views.CotizacionConvertirView.as_view(), name='gestion-cotizacion-convertir'),

    # ── Facturas ──────────────────────────────────────────────────────────────
    path('facturas', views.FacturaListView.as_view(), name='gestion-factura-list'),
    path('facturas/<int:pk>', views.FacturaDetailView.as_view(), name='gestion-factura-detail'),
    path('facturas/<int:pk>/anular', views.FacturaAnularView.as_view(), name='gestion-factura-anular'),
]

