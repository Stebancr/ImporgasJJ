from django.urls import path
from . import views
from .offline import SincronizarVisitaView

urlpatterns = [
    path('tipos/', views.TiposVisitaView.as_view(), name='visitas-tipos'),
    path('tipos/<int:pk>/', views.TipoVisitaDetailView.as_view(), name='visitas-tipo-detail'),
    path('exportar/', views.ExportarVisitasView.as_view(), name='visitas-exportar'),
    path('<int:pk>/sincronizar/', SincronizarVisitaView.as_view(), name='visitas-sincronizar'),
    path('<int:pk>/costo/', views.CostoVisitaView.as_view(), name='visitas-costo'),
    path('<int:pk>/indicaciones/', views.IndicacionesVisitaView.as_view(), name='visitas-indicaciones'),
    # Technician helpers
    path('tecnicos/', views.TecnicosView.as_view(), name='visitas-tecnicos'),

    # Visits CRUD
    path('', views.VisitaListCreateView.as_view(), name='visitas-list-create'),
    path('<int:pk>/', views.VisitaDetailView.as_view(), name='visitas-detail'),

    # Actions
    path('<int:pk>/iniciar/', views.IniciarVisitaView.as_view(), name='visitas-iniciar'),
    path('<int:pk>/finalizar/', views.FinalizarVisitaView.as_view(), name='visitas-finalizar'),

    # Photos
    path('<int:pk>/fotos/', views.FotosView.as_view(), name='visitas-fotos'),
    path('<int:pk>/fotos/<int:foto_id>/', views.FotosView.as_view(), name='visitas-fotos-delete'),
    path('<int:pk>/fotos/<int:foto_id>/archivo/', views.FotoPublicaView.as_view(), name='visitas-foto-publica'),
    path('<int:pk>/firma/', views.FirmaPublicaView.as_view(), name='visitas-firma-publica'),

    # Calendar
    path('calendario/', views.CalendarioView.as_view(), name='visitas-calendario'),

    # PDF
    path('<int:pk>/pdf/', views.PDFReporteView.as_view(), name='visitas-pdf'),
    path('<int:pk>/pdf/publico/', views.PDFPublicoView.as_view(), name='visitas-pdf-publico'),
    path('<int:pk>/pdf/revocar/', views.RevocarEnlacesView.as_view(), name='visitas-pdf-revocar'),
    path('<int:pk>/pdf/reintentar/', views.ReintentarPdfView.as_view(), name='visitas-pdf-reintentar'),
]
