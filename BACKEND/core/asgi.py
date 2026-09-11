"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

django_asgi_application = get_asgi_application()

from crmChat.routing import websocket_urlpatterns
from crmChat.websocket_auth import JWTSubprotocolAuthMiddleware

application = ProtocolTypeRouter({
    'http': django_asgi_application,
    'websocket': JWTSubprotocolAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
