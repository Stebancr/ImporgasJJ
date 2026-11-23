import io
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from django.core.management import call_command
from auth.serializers import TokenLMSSerializer
from usuarios.models import Credenciales, AuthSession
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class GlobalRealtimeRevocationTests(TransactionTestCase):
    def run_scenario(self, mutation):
        from core.asgi import application
        user = Credenciales.objects.create(usuario='synthetic-realtime', estado=1, tipo_usuario=1)
        refresh = TokenLMSSerializer.get_token(user)
        token = str(refresh.access_token)

        async def scenario():
            tabs = [WebsocketCommunicator(application, '/ws/crm-chat/', subprotocols=['crm-chat', f'jwt.{token}']) for _ in range(2)]
            for tab in tabs:
                self.assertTrue((await tab.connect())[0])
            await database_sync_to_async(mutation)(user, refresh)
            for tab in tabs:
                self.assertEqual(await tab.receive_output(timeout=5), {'type': 'websocket.close', 'code': 4401})
                await tab.disconnect()
            stale = WebsocketCommunicator(application, '/ws/crm-chat/', subprotocols=['crm-chat', f'jwt.{token}'])
            self.assertFalse((await stale.connect())[0])
            await stale.disconnect()
        async_to_sync(scenario)()

    def test_global_revocation_closes_idle_tabs_and_denies_reconnection(self):
        self.run_scenario(lambda user, token: call_command('revoke_all_sessions', reason='test_release', operation_id='idle-tabs', actor_id=user.pk, stdout=io.StringIO()))

    def test_individual_version_closes_idle_tabs(self):
        self.run_scenario(lambda user, token: Credenciales.objects.filter(pk=user.pk).update(password_version=1))

    def test_inactive_account_closes_idle_tabs(self):
        self.run_scenario(lambda user, token: Credenciales.objects.filter(pk=user.pk).update(estado=0))

    def test_expired_parent_session_closes_idle_tabs(self):
        self.run_scenario(lambda user, token: AuthSession.objects.filter(pk=token['session_id']).update(expires_at=timezone.now()))

    def test_explicit_logout_closes_idle_tabs(self):
        self.run_scenario(lambda user, token: AuthSession.objects.filter(pk=token['session_id']).update(revoked_at=timezone.now()))
