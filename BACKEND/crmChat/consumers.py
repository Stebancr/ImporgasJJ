"""Consumer WebSocket para actualizaciones de la bandeja de asesores."""

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from usuarios.models import Credenciales


class CRMInboxConsumer(AsyncJsonWebsocketConsumer):
    """Publica eventos solo a usuarios con rol administrativo del CRM."""

    group_name = 'crm_agents'

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated or getattr(user, 'tipo_usuario', 0) not in (1, 4):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol='crm-chat')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not await self.authorized():
            await self.close(code=4403)
            return
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    async def crm_event(self, event):
        if not await self.authorized():
            await self.close(code=4403)
            return
        await self.send_json(event['payload'])

    @database_sync_to_async
    def authorized(self):
        user = self.scope.get('user')
        return bool(user and Credenciales.objects.filter(pk=user.pk, estado=1,
            tipo_usuario__in=(1, 4), password_version=getattr(user, 'password_version', 0)).exists())

class CustomerChatConsumer(CRMInboxConsumer):
    """A customer receives only IDs belonging to their own web conversation."""

    async def connect(self):
        from .models import ChatSession
        user = self.scope.get('user')
        session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'crm_session_{session_id}'
        if not user or not user.is_authenticated:
            await self.close(code=4403)
            return
        allowed = await database_sync_to_async(ChatSession.objects.filter(
            pk=session_id, channel='ecommerce', user_id_ref=user.pk).exists)()
        if not allowed:
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol='crm-chat')
    @database_sync_to_async
    def authorized(self):
        from .models import ChatSession
        user = self.scope.get('user')
        return bool(user and Credenciales.objects.filter(pk=user.pk, estado=1,
            password_version=getattr(user, 'password_version', 0)).exists()
            and ChatSession.objects.filter(pk=self.scope['url_route']['kwargs']['session_id'],
                channel='ecommerce', user_id_ref=user.pk).exists())
