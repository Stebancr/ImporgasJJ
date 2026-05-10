from django.urls import path
from usuarios import views

urlpatterns = [
    path("register/", views.Register.as_view(), name="register"),
    path("register/<int:usuario_id>/", views.Register.as_view(), name="register-detail"),
    path("register-temporal/", views.RegisterTemporal.as_view(), name="register-temporal"),
    path('registrar-masivo/', views.RegistrarMasivoView.as_view(), name='registrar-masivo'),
    path("perfil/", views.Perfil.as_view(), name="perfil"),
    path("perfil/<int:id>/", views.Perfil.as_view(), name="perfil-especifico"),
    path("lista-usuarios/", views.ListaUsuarios.as_view(), name="lista-usuarios"),
    path("cargo-nivel-regional/", views.CargoNivelRegionalView.as_view(), name="cargo-nivel-regional"),
    path("filtrar-usuarios/", views.FiltrarUsuariosView.as_view(), name="filtrar-usuarios"),
    path("cambiar-estado-usuario/", views.CambiarEstadoUsuarioView.as_view(), name="cambiar-estado-usuario-post"),
    path("cambiar-estado-usuario/<int:usuario_id>/", views.CambiarEstadoUsuarioView.as_view(), name="cambiar-estado-usuario"),
    path("actualizar-rol-usuario/<int:usuario_id>/", views.ActualizarRolUsuarioView.as_view(), name="actualizar-rol-usuario"),
    path("cargo/", views.DatosCargoView.as_view(), name="datos-cargo"),
    path("nivel/", views.DatosNivelView.as_view(), name="datos-nivel"),
    path("region/", views.DatosRegionView.as_view(), name="datos-region"),
    path("reporte-usuarios/", views.ReporteUsuariosView.as_view(), name="reporte-usuarios"),
]