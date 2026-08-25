from django.urls import path
from . import views

urlpatterns = [
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

    # Calendar
    path('calendario/', views.CalendarioView.as_view(), name='visitas-calendario'),

    # PDF
    path('<int:pk>/pdf/', views.PDFReporteView.as_view(), name='visitas-pdf'),
]
