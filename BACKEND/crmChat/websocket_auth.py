"""Autenticación JWT para WebSocket sin incluir credenciales en la URL."""

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _resolve_user(raw_token):
    authentication = JWTAuthentication()
    try:
        validated = authentication.get_validated_token(raw_token)
        return authentication.get_user(validated)
    except Exception:
        return AnonymousUser()


class JWTSubprotocolAuthMiddleware:
    """Lee ``jwt.<token>`` del subprotocolo WebSocket, no del query string."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = ''
        for protocol in scope.get('subprotocols', []):
            if protocol.startswith('jwt.'):
                token = protocol[4:]
                break
        scope['user'] = await _resolve_user(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)
