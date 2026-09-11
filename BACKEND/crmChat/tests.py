import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import (
    ChannelIdentity,
    ChannelIntegration,
    AssignmentQueue,
    ChatMessage,
    ChatSession,
    ChatAuditEvent,
    CRMContact,
    WebhookEvent,
    QueueMember,
)
from usuarios.models import Credenciales
from .assignment import assign_session_automatically
from .apps.meta.webhooks import normalize_payload
from .apps.meta.services import MetaAPIError, dispatch_outbound_message, secret_store
from .ollama_service import ollama_service
from .tasks import _assert_public_https, audit_meta_tokens
from core.asgi import application


class ConversationStateTests(APITestCase):
    def test_purchase_budget_topic_change_and_return(self):
        state = ollama_service.update_state('Quiero comprar un calentador')
        self.assertEqual(state['intent'], 'purchase')
        self.assertEqual(state['product'], 'calentador')
        self.assertFalse(state['needs_human'])

        state = ollama_service.update_state('Tengo un millón', state)
        self.assertEqual(state['budget'], 1_000_000)
        self.assertEqual(state['stage'], 'recommendation')

        state = ollama_service.update_state('¿Y hacen envíos?', state)
        self.assertEqual(state['topic'], 'shipping')
        self.assertEqual(state['product'], 'calentador')
        self.assertEqual(state['budget'], 1_000_000)

        state = ollama_service.update_state('¿Qué garantía manejan?', state)
        self.assertEqual(state['topic'], 'warranty')
        self.assertEqual(state['product'], 'calentador')
        state = ollama_service.update_state('¿Y cuál calentador me recomiendas?', state)
        self.assertEqual(state['topic'], 'product')
        self.assertIn('warranty', state['previous_topics'])

    def test_buying_does_not_escalate_but_explicit_advisor_does(self):
        self.assertFalse(ollama_service.needs_human_agent('Quiero comprar un celular'))
        self.assertTrue(ollama_service.needs_human_agent('Quiero hablar con un asesor'))
        self.assertTrue(ollama_service.needs_human_agent('No me estás entendiendo'))

    @patch('crmChat.ollama_service.requests.post')
    def test_api_persists_structured_memory_across_turns(self, ollama_post):
        provider_response = Mock()
        provider_response.raise_for_status.return_value = None
        provider_response.json.return_value = {'message': {'content': 'Respuesta basada en el contexto.'}}
        ollama_post.return_value = provider_response

        session_id = None
        responses = {}
        for message in ('Hola', 'Quiero comprar un celular', 'Tengo un millón', '¿Cuál me recomiendas?', '¿Y hacen envíos?'):
            response = self.client.post(reverse('bot-chat'), {
                'message': message,
                'session_id': session_id,
                'user_name': 'Cliente',
            }, format='json')
            self.assertEqual(response.status_code, 200)
            session_id = response.data['session_id']
            responses[message] = response.data['message']

        session = ChatSession.objects.get(pk=session_id)
        self.assertEqual(session.conversation_state['intent'], 'purchase')
        self.assertEqual(session.conversation_state['product'], 'celular')
        self.assertEqual(session.conversation_state['budget'], 1_000_000)
        self.assertEqual(session.conversation_state['topic'], 'shipping')
        self.assertIn('catálogo actual', responses['¿Cuál me recomiendas?'])
        self.assertIn('envíos a todo el país', responses['¿Y hacen envíos?'])
        self.assertLessEqual(len(ollama_post.call_args.kwargs['json']['messages']), 12)

        response = self.client.post(reverse('bot-chat'), {
            'message': 'Quiero hablar con un asesor',
            'session_id': session_id,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['needs_login'])
        session.refresh_from_db()
        self.assertTrue(session.conversation_state['needs_human'])


class OmnichannelModelTests(APITestCase):
    """Protege compatibilidad e idempotencia del esquema omnicanal."""

    def test_existing_conversation_defaults_to_ecommerce(self):
        session = ChatSession.objects.create(user_name='Cliente legado')
        self.assertEqual(session.channel, ChannelIntegration.CHANNEL_ECOMMERCE)
        self.assertIsNone(session.integration)

    def test_external_message_id_is_idempotent(self):
        session = ChatSession.objects.create(user_name='Cliente WhatsApp')
        ChatMessage.objects.create(
            session=session,
            text='Hola',
            sender_type='user',
            external_message_id='wamid.test-1',
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChatMessage.objects.create(
                session=session,
                text='Mensaje duplicado',
                sender_type='user',
                external_message_id='wamid.test-1',
            )

    def test_identity_is_unique_per_integration(self):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp pruebas',
            channel=ChannelIntegration.CHANNEL_WHATSAPP,
            external_account_id='waba-test',
        )
        contact = CRMContact.objects.create(name='Cliente')
        ChannelIdentity.objects.create(
            integration=integration,
            contact=contact,
            external_id='573001234567',
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChannelIdentity.objects.create(
                integration=integration,
                contact=CRMContact.objects.create(name='Duplicado'),
                external_id='573001234567',
            )

    @patch('crmChat.apps.facebook.services.send_text', side_effect=ValueError('payload inválido'))
    def test_outbound_failure_is_safe_and_preserves_payload(self, _send):
        integration = ChannelIntegration.objects.create(
            name='Facebook pruebas',
            channel='facebook',
            active=True,
            external_account_id='page-outbound',
            page_id='page-outbound',
            graph_api_version='v-test',
        )
        session = ChatSession.objects.create(
            user_name='Cliente',
            channel='facebook',
            integration=integration,
            external_thread_id='customer-outbound',
        )
        message = ChatMessage.objects.create(
            session=session,
            text='Hola',
            sender_type='agent',
            direction='outbound',
            status='queued',
            metadata={'outbound_payload': {'quick_replies': []}},
        )
        with self.assertRaises(MetaAPIError):
            dispatch_outbound_message(message)
        message.refresh_from_db()
        self.assertEqual(message.status, 'failed')
        self.assertIn('outbound_payload', message.metadata)


@override_settings(
    META_APP_SECRET='app-secret-test',
    META_WEBHOOK_VERIFY_TOKEN='verify-test',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class MetaWebhookTests(APITestCase):
    """Valida firma, challenge, detección y persistencia del webhook real."""

    def setUp(self):
        self.integration = ChannelIntegration.objects.create(
            name='WhatsApp pruebas',
            channel='whatsapp',
            active=True,
            external_account_id='waba-1',
            phone_number_id='phone-1',
            graph_api_version='v-test',
        )
        self.payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': 'waba-1',
                'changes': [{
                    'field': 'messages',
                    'value': {
                        'metadata': {'phone_number_id': 'phone-1'},
                        'contacts': [{'wa_id': '573001234567', 'profile': {'name': 'Cliente Meta'}}],
                        'messages': [{
                            'from': '573001234567',
                            'id': 'wamid.webhook-1',
                            'timestamp': '1700000000',
                            'type': 'text',
                            'text': {'body': 'Hola desde WhatsApp'},
                        }],
                    },
                }],
            }],
        }

    def _signed_post(self, payload=None, signature=''):
        body = json.dumps(payload or self.payload, separators=(',', ':')).encode()
        if not signature:
            signature = 'sha256=' + hmac.new(b'app-secret-test', body, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse('meta-webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

    def test_verification_returns_plain_challenge(self):
        response = self.client.get(reverse('meta-webhook'), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'verify-test',
            'hub.challenge': '123456',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'123456')

    def test_api_prefixed_whatsapp_alias_verifies_for_direct_backend_proxy(self):
        """Acepta el prefijo /api cuando un proxy externo no lo elimina."""

        response = self.client.get('/api/meta/whatsapp/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'verify-test',
            'hub.challenge': 'direct-backend-challenge',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'direct-backend-challenge')

    def test_invalid_signature_is_rejected(self):
        response = self._signed_post(signature='sha256=bad')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(WebhookEvent.objects.exists())

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    def test_whatsapp_message_is_normalized_and_idempotent(self, read_receipt):
        first = self._signed_post()
        second = self._signed_post()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        message = ChatMessage.objects.get(external_message_id='wamid.webhook-1')
        self.assertEqual(message.text, 'Hola desde WhatsApp')
        self.assertEqual(message.direction, 'inbound')
        self.assertEqual(message.session.channel, 'whatsapp')
        read_receipt.assert_called_once_with(message.id)


class ChannelAdapterTests(APITestCase):
    """Comprueba que Messenger e Instagram producen el mismo contrato interno."""

    def test_facebook_and_instagram_text_are_normalized(self):
        base = {
            'entry': [{
                'id': 'professional-1',
                'messaging': [{
                    'sender': {'id': 'customer-1'},
                    'recipient': {'id': 'professional-1'},
                    'timestamp': 1700000000000,
                    'message': {'mid': 'mid-1', 'text': 'Hola'},
                }],
            }],
        }
        facebook = normalize_payload({**base, 'object': 'page'})[0]
        instagram = normalize_payload({**base, 'object': 'instagram'})[0]
        self.assertEqual(facebook.channel, 'facebook')
        self.assertEqual(instagram.channel, 'instagram')
        self.assertEqual(facebook.text, instagram.text)
        self.assertEqual(facebook.sender_id, 'customer-1')

    def test_echo_is_status_not_new_customer_message(self):
        payload = {
            'object': 'page',
            'entry': [{'id': 'page-1', 'messaging': [{
                'sender': {'id': 'page-1'},
                'recipient': {'id': 'customer-1'},
                'message': {'mid': 'outbound-1', 'is_echo': True, 'text': 'Respuesta'},
            }]}],
        }
        event = normalize_payload(payload)[0]
        self.assertEqual(event.status, 'sent')
        self.assertEqual(event.external_message_id, 'outbound-1')

    def test_messenger_delivery_updates_external_message(self):
        payload = {
            'object': 'page',
            'entry': [{'id': 'page-1', 'messaging': [{
                'sender': {'id': 'customer-1'},
                'recipient': {'id': 'page-1'},
                'delivery': {'mids': ['mid-delivered'], 'watermark': 1700000000000},
            }]}],
        }
        event = normalize_payload(payload)[0]
        self.assertEqual(event.status, 'delivered')
        self.assertEqual(event.external_message_id, 'mid-delivered')


@override_settings(META_CREDENTIALS_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'))
class IntegrationSecurityTests(APITestCase):
    """Verifica permisos, cifrado, auditoría y manejo de redes no confiables."""

    def setUp(self):
        self.admin_user = Credenciales.objects.create(usuario='meta_admin', tipo_usuario=1, estado=1)
        self.client.force_authenticate(self.admin_user)

    def test_secrets_are_write_only_encrypted_and_audited(self):
        response = self.client.post(reverse('meta-integrations'), {
            'name': 'Canal seguro',
            'channel': 'facebook',
            'external_account_id': 'page-security-test',
            'access_token': 'token-que-no-debe-salir',
            'app_secret': 'secret-que-no-debe-salir',
            'verify_token': 'verify-que-no-debe-salir',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('access_token', response.data)
        self.assertNotIn('app_secret', response.data)
        self.assertNotIn('verify_token', response.data)
        integration = ChannelIntegration.objects.get(pk=response.data['id'])
        self.assertNotEqual(integration.access_token_encrypted, 'token-que-no-debe-salir')
        audit = ChatAuditEvent.objects.get(action='integration.created')
        self.assertNotIn('token-que-no-debe-salir', json.dumps(audit.details))

    def test_non_administrator_cannot_list_integrations(self):
        user = Credenciales.objects.create(usuario='customer_meta', tipo_usuario=2, estado=1)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse('meta-integrations')).status_code, 403)

    def test_token_expiration_audit_is_idempotent_per_day(self):
        ChannelIntegration.objects.create(
            name='Token próximo a vencer',
            channel='instagram',
            active=True,
            instagram_account_id='ig-expiring',
            graph_api_version='v-test',
            token_expires_at=timezone.now() + timedelta(days=1),
        )
        audit_meta_tokens()
        audit_meta_tokens()
        self.assertEqual(ChatAuditEvent.objects.filter(action='integration.token_expiring').count(), 1)

    def test_private_attachment_address_is_rejected(self):
        with self.assertRaises(ValueError):
            _assert_public_https('https://127.0.0.1/private-file')

    @override_settings(
        INSTAGRAM_OAUTH_REDIRECT_URI='https://crm.example.test/api/meta/instagram/oauth/callback/',
        INSTAGRAM_OAUTH_AUTHORIZE_URL='https://www.instagram.com/oauth/authorize',
        INSTAGRAM_OAUTH_SCOPES='instagram_business_basic,instagram_business_manage_messages',
    )
    def test_instagram_oauth_start_is_admin_only_and_uses_exact_redirect(self):
        integration = ChannelIntegration.objects.create(
            name='Instagram OAuth',
            channel='instagram',
            app_id='instagram-app-id',
            app_secret_encrypted=secret_store.encrypt('instagram-app-secret'),
        )
        response = self.client.post(reverse('instagram-oauth-start', args=[integration.pk]))
        self.assertEqual(response.status_code, 200)
        query = parse_qs(urlparse(response.data['authorization_url']).query)
        self.assertEqual(query['client_id'], ['instagram-app-id'])
        self.assertEqual(query['redirect_uri'], ['https://crm.example.test/api/meta/instagram/oauth/callback/'])
        self.assertIn('instagram_business_manage_messages', query['scope'][0])
        self.assertNotIn('instagram-app-secret', response.data['authorization_url'])

        user = Credenciales.objects.create(usuario='instagram_customer', tipo_usuario=2, estado=1)
        self.client.force_authenticate(user)
        self.assertEqual(
            self.client.post(reverse('instagram-oauth-start', args=[integration.pk])).status_code,
            403,
        )

    @override_settings(
        INSTAGRAM_OAUTH_REDIRECT_URI='https://crm.example.test/api/meta/instagram/oauth/callback/',
        INSTAGRAM_OAUTH_TOKEN_URL='https://api.instagram.test/oauth/access_token',
        INSTAGRAM_GRAPH_API_URL='https://graph.instagram.test',
    )
    @patch('crmChat.apps.instagram.services.requests.get')
    @patch('crmChat.apps.instagram.services.requests.post')
    def test_instagram_oauth_callback_encrypts_token_and_state_cannot_be_reused(self, post, get):
        integration = ChannelIntegration.objects.create(
            name='Instagram Callback',
            channel='instagram',
            app_id='instagram-app-id',
            app_secret_encrypted=secret_store.encrypt('instagram-app-secret'),
        )
        start = self.client.post(reverse('instagram-oauth-start', args=[integration.pk]))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        post.return_value = Mock(
            ok=True,
            status_code=200,
            content=b'json',
            json=lambda: {'access_token': 'short-lived-token', 'user_id': 'ig-professional-123'},
        )
        get.return_value = Mock(
            ok=True,
            status_code=200,
            content=b'json',
            json=lambda: {'access_token': 'long-lived-token', 'expires_in': 5_184_000},
        )

        callback = self.client.get(reverse('instagram-oauth-callback'), {'code': 'authorization-code', 'state': state})
        self.assertEqual(callback.status_code, 302)
        self.assertIn('instagram_oauth=success', callback['Location'])
        integration.refresh_from_db()
        self.assertEqual(integration.instagram_account_id, 'ig-professional-123')
        self.assertNotEqual(integration.access_token_encrypted, 'long-lived-token')
        self.assertEqual(secret_store.decrypt(integration.access_token_encrypted), 'long-lived-token')
        self.assertIsNotNone(integration.token_expires_at)

        replay = self.client.get(reverse('instagram-oauth-callback'), {'code': 'authorization-code', 'state': state})
        self.assertEqual(replay.status_code, 302)
        self.assertIn('instagram_oauth=invalid_state', replay['Location'])
        self.assertEqual(post.call_count, 1)


class AssignmentTests(APITestCase):
    """Valida selección determinista por carga y capacidad."""

    def test_automatic_assignment_uses_available_member(self):
        advisor = Credenciales.objects.create(usuario='advisor_test', tipo_usuario=1, estado=1)
        advisor.set_password('test-password')
        advisor.save(update_fields=['password'])
        queue = AssignmentQueue.objects.create(
            name='Ventas Meta',
            auto_assign=True,
            channels=['whatsapp', 'facebook', 'instagram'],
        )
        QueueMember.objects.create(queue=queue, user=advisor, capacity=2)
        session = ChatSession.objects.create(user_name='Cliente', channel='whatsapp', status='bot')

        assign_session_automatically(session)

        self.assertEqual(session.queue, queue)
        self.assertEqual(session.assigned_to, advisor)
        self.assertEqual(session.agent_id_ref, advisor.id)
        self.assertEqual(session.status, 'active')


class WebSocketSecurityTests(APITestCase):
    """Comprueba autenticación y protocolo de la bandeja en tiempo real."""

    def test_administrator_connects_and_receives_pong(self):
        advisor = Credenciales.objects.create(usuario='ws_advisor', tipo_usuario=1, estado=1)
        token = str(AccessToken.for_user(advisor))

        async def scenario():
            communicator = WebsocketCommunicator(
                application,
                '/ws/crm-chat/',
                subprotocols=['crm-chat', f'jwt.{token}'],
            )
            connected, protocol = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual(protocol, 'crm-chat')
            await communicator.send_json_to({'type': 'ping'})
            self.assertEqual(await communicator.receive_json_from(), {'type': 'pong'})
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_connection_without_token_is_rejected(self):
        async def scenario():
            communicator = WebsocketCommunicator(
                application,
                '/ws/crm-chat/',
                subprotocols=['crm-chat'],
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(scenario)()
