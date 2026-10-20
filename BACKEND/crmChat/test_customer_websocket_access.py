from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase,override_settings
from rest_framework_simplejwt.tokens import AccessToken
from usuarios.models import Credenciales
from crmChat.models import ChatSession


@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class CustomerRealtimeAccessTests(TransactionTestCase):
    def test_customer_receives_own_events_and_revocation_closes_connection(self):
        from core.asgi import application
        for index,change in enumerate(({'estado':0},{'password_version':1})):
            user=Credenciales.objects.create(usuario=f'customer-socket-{index}',estado=1,tipo_usuario=0)
            session=ChatSession.objects.create(user_id_ref=user.pk,channel='ecommerce')
            token=str(AccessToken.for_user(user))
            async def scenario():
                socket=WebsocketCommunicator(application,f'/ws/crm-chat/sessions/{session.pk}/',subprotocols=['crm-chat',f'jwt.{token}'])
                self.assertTrue((await socket.connect())[0])
                await socket.send_json_to({'type':'ping'})
                self.assertEqual(await socket.receive_json_from(),{'type':'pong'})
                await get_channel_layer().group_send(f'crm_session_{session.pk}',{'type':'crm.event','payload':{'type':'message.created','session_id':session.pk}})
                self.assertEqual((await socket.receive_json_from())['session_id'],session.pk)
                await database_sync_to_async(Credenciales.objects.filter(pk=user.pk).update)(**change)
                await socket.send_json_to({'type':'ping'})
                self.assertEqual(await socket.receive_output(),{'type':'websocket.close','code':4403})
                await socket.disconnect()
            async_to_sync(scenario)()

    def test_customer_cannot_join_another_customers_session(self):
        from core.asgi import application
        user=Credenciales.objects.create(usuario='foreign-socket',estado=1,tipo_usuario=0)
        session=ChatSession.objects.create(user_id_ref=user.pk+1000,channel='ecommerce')
        token=str(AccessToken.for_user(user))
        async def scenario():
            socket=WebsocketCommunicator(application,f'/ws/crm-chat/sessions/{session.pk}/',subprotocols=['crm-chat',f'jwt.{token}'])
            self.assertFalse((await socket.connect())[0])
            await socket.disconnect()
        async_to_sync(scenario)()
