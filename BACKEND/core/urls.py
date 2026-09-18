"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from auth.views import TokenLMSView, PasswordVersionRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/token/', TokenLMSView.as_view(), name='token_obtain_pair'),
    # Alias sin barra para proxies que normalizan la URL y redirigen los POST.
    path('auth/token', TokenLMSView.as_view(), name='token_obtain_pair_no_slash'),
    path('auth/token/refresh/', PasswordVersionRefreshView.as_view(), name='token_refresh'),
    path('auth/token/refresh', PasswordVersionRefreshView.as_view(), name='token_refresh_no_slash'),
    path('user/', include('usuarios.urls')),
    path('ecommerce/', include('ecommerce.urls')),  # kept for legacy
    path('', include('ecommerce.urls')),            # root-level — /products, /brands, etc.
    path('gestion/', include('gestion.urls')),
    path('crm-chat/', include('crmChat.urls')),
    # Meta usa un callback público independiente de la autenticación del CRM.
    path('meta/', include('crmChat.apps.meta.urls')),
    path('meta/whatsapp/', include('crmChat.apps.whatsapp.urls')),
    path('meta/facebook/', include('crmChat.apps.facebook.urls')),
    path('meta/instagram/', include('crmChat.apps.instagram.urls')),
    # Compatibilidad con proxies externos que entregan el prefijo /api/ a
    # Django sin pasar por Nginx. Evita 404 sin duplicar la lógica Meta.
    path('api/meta/', include('crmChat.apps.meta.urls')),
    path('api/meta/whatsapp/', include('crmChat.apps.whatsapp.urls')),
    path('api/meta/facebook/', include('crmChat.apps.facebook.urls')),
    path('api/meta/instagram/', include('crmChat.apps.instagram.urls')),
    path('visits/', include('AppVisits.urls')),
]

# Servir archivos media en desarrollo
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

