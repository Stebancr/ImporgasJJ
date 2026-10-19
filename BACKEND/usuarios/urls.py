from django.urls import path
from usuarios import views
from usuarios import account_views
from usuarios import admin_accounts

urlpatterns = [
    path('password/change', account_views.ChangePasswordView.as_view(), name='customer-password-change'),
    path('password/reset/request', account_views.RequestPasswordResetView.as_view(), name='customer-password-reset-request'),
    path('password/reset/confirm', account_views.ConfirmPasswordResetView.as_view(), name='customer-password-reset-confirm'),
    path('terms', views.TermsInfo.as_view(), name='terms-info'),
    path('terms/accept', views.AcceptTerms.as_view(), name='terms-accept'),
    path("registerUsers", views.registerUsers.as_view(), name="register-users"),
    path("register", admin_accounts.AccountCreate.as_view(), name="register"),
    path("register-public", views.registerUsers.as_view(), name="register-public"),
    path("register/<int:usuario_id>", admin_accounts.AccountDetail.as_view(), name="register-detail"),
    path('register/<int:usuario_id>/password', admin_accounts.AccountPassword.as_view(), name='admin-account-password'),
    path("register-temporal", views.RegisterTemporal.as_view(), name="register-temporal"),
    path('registrar-masivo', views.RegistrarMasivoView.as_view(), name='registrar-masivo'),
    path("perfil", views.Perfil.as_view(), name="perfil"),
    path("perfil/<int:id>", views.Perfil.as_view(), name="perfil-especifico"),
    path("lista-usuarios", admin_accounts.AccountList.as_view(), name="lista-usuarios"),
    path("cargo-nivel-regional", views.CargoNivelRegionalView.as_view(), name="cargo-nivel-regional"),
    path("cargos", views.CargosView.as_view(), name="cargos-list"),
    path("cargos/<int:cargo_id>", views.CargosView.as_view(), name="cargos-detail"),
    path("filtrar-usuarios", views.FiltrarUsuariosView.as_view(), name="filtrar-usuarios"),
    path("cambiar-estado-usuario", admin_accounts.AccountState.as_view(), name="cambiar-estado-usuario-post"),
    path("cambiar-estado-usuario/<int:usuario_id>", admin_accounts.AccountState.as_view(), name="cambiar-estado-usuario"),
    path("actualizar-rol-usuario/<int:usuario_id>", admin_accounts.AccountRole.as_view(), name="actualizar-rol-usuario"),
    path("cargo", views.DatosCargoView.as_view(), name="datos-cargo"),
    path("nivel", views.DatosNivelView.as_view(), name="datos-nivel"),
    path("region", views.DatosRegionView.as_view(), name="datos-region"),
    path("reporte-usuarios", views.ReporteUsuariosView.as_view(), name="reporte-usuarios"),
]
