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
from django.core.cache import cache
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
    MetaConnection,
    MetaFacebookPage,
    MetaInstagramAccount,
    WebhookEvent,
    QueueMember,
)
from usuarios.models import Credenciales
from .assignment import assign_session_automatically
from .apps.meta.webhooks import normalize_payload
from .apps.meta.services import MetaAPIError, dispatch_outbound_message, graph_request, secret_store, disconnect_integration
from .apps.meta.oauth import REQUIRED_SCOPES, ensure_oauth_webhook_subscriptions, get_page_details
from .ollama_service import ollama_service
from .tasks import (
    _assert_public_https,
    audit_meta_tokens,
    close_inactive_bot_sessions,
    generate_omnichannel_bot_reply,
    INACTIVITY_WARNING_TEXT,
)
from core.asgi import application
from core.logging_filters import redact_webhook_tokens
from ecommerce.models import Brand, Category, Product, ProductSpec, SpecAttribute


class ConversationStateTests(APITestCase):
    def test_product_context_ignores_budget_and_tracks_topics(self):
        state = ollama_service.update_state('Estoy interesado en un calentador')
        self.assertEqual(state['intent'], 'purchase')
        self.assertEqual(state['product'], 'calentador')
        self.assertFalse(state['needs_human'])

        state = ollama_service.update_state('Tengo un millón', state)
        self.assertIsNone(state['budget'])
        self.assertEqual(state['stage'], 'recommendation')

        state = ollama_service.update_state('¿Y hacen envíos?', state)
        self.assertEqual(state['topic'], 'shipping')
        self.assertEqual(state['product'], 'calentador')
        self.assertIsNone(state['budget'])

        state = ollama_service.update_state('¿Qué garantía manejan?', state)
        self.assertEqual(state['topic'], 'warranty')
        self.assertEqual(state['product'], 'calentador')
        state = ollama_service.update_state('¿Y cuál calentador me recomiendas?', state)
        self.assertEqual(state['topic'], 'product')
        self.assertIn('warranty', state['previous_topics'])

    def test_buying_does_not_escalate_but_explicit_advisor_does(self):
        self.assertFalse(ollama_service.needs_human_agent('Quiero comprar un celular'))
        self.assertTrue(ollama_service.needs_human_agent('Quiero comprar un calentador'))
        self.assertTrue(ollama_service.needs_human_agent('Necesito cotizar 20 unidades'))
        self.assertTrue(ollama_service.needs_human_agent('Quiero hablar con un asesor'))
        self.assertTrue(ollama_service.needs_human_agent('No me estás entendiendo'))

    def test_propano_is_not_confused_with_ropa(self):
        self.assertFalse(ollama_service._is_out_of_scope('Quiero comprar el Regulador Gas Propano'))

    def test_real_product_can_be_selected_by_name_pronoun_typo_and_position(self):
        category = Category.objects.create(name='Reguladores')
        brand = Brand.objects.create(name='Fisher')
        product = Product.objects.create(
            name='Regulador Gas Propano', description='Modelo R18', price=14900,
            category=category, brand=brand, total_stock=3, is_available=True,
        )
        listed = ollama_service.get_bot_response('¿Qué reguladores tienen?')
        self.assertEqual(listed['state']['recent_products'][0]['id'], product.id)
        for phrase in ('Quiero comprar el Regulador Gas Propano', 'quiero comprarlo',
                       'quiero comprar ese regulador', 'quiero comparlo Regulador Gas Propano',
                       'quiero comprar el primero'):
            result = ollama_service.get_bot_response(phrase, conversation_state=listed['state'])
            self.assertTrue(result['needs_agent'], phrase)
            self.assertEqual(result['state']['selected_product_id'], product.id)

    @override_settings(PRODUCT_URL_TEMPLATE='https://shop.example.test/producto/{id}')
    def test_future_category_uses_database_specs_and_public_links(self):
        category = Category.objects.create(name='Hornos especiales', description='Equipos para cocción')
        brand = Brand.objects.create(name='Marca dinámica')
        gas = SpecAttribute.objects.create(name='Tipo de gas', order=1)
        products = []
        for index, value in enumerate(('Natural', 'GLP'), 1):
            product = Product.objects.create(
                name=f'Horno futuro {index}', description='Horno empotrable', price=100000 + index,
                category=category, brand=brand, total_stock=2, is_available=True,
            )
            ProductSpec.objects.create(product=product, attribute=gas, value=value)
            products.append(product)

        question = ollama_service.get_bot_response('¿Cuál horno especial me recomiendas?')
        self.assertIn('tipo de gas', question['response'].lower())
        self.assertEqual(question['state']['asked_attributes'], ['Tipo de gas'])

        result = ollama_service.get_bot_response(
            'Gas natural', conversation_state=question['state'],
        )
        self.assertEqual(len(result['state']['recent_products']), 1)
        self.assertIn(f'https://shop.example.test/producto/{products[0].id}', result['response'])
        self.assertNotIn(f'/producto/{products[1].id}', result['response'])

    def test_unavailable_product_reports_stock(self):
        category = Category.objects.create(name='Reguladores')
        brand = Brand.objects.create(name='Marca prueba')
        product = Product.objects.create(
            name='Regulador Agotado', description='', price=10000,
            category=category, brand=brand, total_stock=0, is_available=True,
        )
        result = ollama_service.get_bot_response('Quiero comprar Regulador Agotado')
        self.assertFalse(result['needs_agent'])
        self.assertIn('no tiene stock', result['response'])

    @patch('crmChat.views.ollama_service.get_bot_response')
    def test_closed_ecommerce_chat_creates_independent_conversation(self, bot):
        bot.return_value = {'response': 'Hola de nuevo', 'needs_agent': False, 'state': {}, 'summary': ''}
        old_message = ChatMessage.objects.create(
            session=ChatSession.objects.create(user_name='Cliente', status='closed'),
            text='Contexto anterior', sender_type='user', direction='inbound',
        )
        session = old_message.session
        response = self.client.post(reverse('bot-chat'), {'message': 'Necesito ayuda', 'session_id': session.id}, format='json')
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'closed')
        self.assertEqual(session.messages.count(), 1)
        new_session = ChatSession.objects.get(pk=response.data['session_id'])
        self.assertNotEqual(new_session.id, session.id)
        self.assertEqual(new_session.status, 'bot')
        self.assertEqual(new_session.messages.filter(sender_type='user').count(), 1)
        self.assertEqual(new_session.messages.filter(sender_type='bot').count(), 2)
        self.assertEqual(new_session.messages.first().text, ollama_service.INITIAL_GREETING)
        history = bot.call_args.kwargs['conversation_history']
        self.assertNotIn('Contexto anterior', [item['content'] for item in history])

    def test_identity_scope_and_commercial_handoff_are_deterministic(self):
        greeting = ollama_service.get_bot_response('Hola')
        self.assertEqual(greeting['response'], ollama_service.INITIAL_GREETING)
        self.assertNotIn('Ollama', greeting['response'])
        outside = ollama_service.get_bot_response('¿Quién es el presidente de Colombia?')
        self.assertIn('productos y servicios de IMPORGAS JJ', outside['response'])
        for phrase in (
            'Quiero cotizar un calentador',
            'Necesito 10 unidades',
            'Necesito precio para una empresa',
            'Quiero hablar con una persona',
            'Cómprame 3 unidades',
            'Quiero comprar este producto',
        ):
            self.assertTrue(ollama_service.get_bot_response(phrase)['needs_agent'], phrase)


class ChatInactivityTests(APITestCase):
    def _session_after_bot_reply(self):
        session = ChatSession.objects.create(user_name='Inactivo', status='bot')
        inbound = ChatMessage.objects.create(session=session, text='Hola', sender_type='user', direction='inbound')
        reply = ChatMessage.objects.create(session=session, text='¿Algo más?', sender_type='bot', direction='outbound', status='sent', reply_to_message=inbound)
        old = timezone.now() - timedelta(minutes=2, seconds=5)
        session.last_customer_message_at = old - timedelta(seconds=5)
        session.last_bot_message_at = old
        session.save(update_fields=['last_customer_message_at', 'last_bot_message_at'])
        return session

    def test_warning_is_unique_and_session_closes_one_minute_later(self):
        session = self._session_after_bot_reply()
        self.assertEqual(close_inactive_bot_sessions()['warned'], 1)
        self.assertEqual(close_inactive_bot_sessions()['warned'], 0)
        self.assertEqual(session.messages.filter(text=INACTIVITY_WARNING_TEXT).count(), 1)
        session.refresh_from_db()
        session.inactivity_warning_at = timezone.now() - timedelta(minutes=1, seconds=1)
        session.save(update_fields=['inactivity_warning_at'])
        self.assertEqual(close_inactive_bot_sessions()['closed'], 1)
        session.refresh_from_db()
        self.assertEqual(session.status, 'closed')

    def test_customer_reply_cancels_pending_close(self):
        session = self._session_after_bot_reply()
        close_inactive_bot_sessions()
        customer = ChatMessage.objects.create(session=session, text='Sí', sender_type='user', direction='inbound')
        session.last_customer_message_at = customer.created_at
        session.save(update_fields=['last_customer_message_at'])
        close_inactive_bot_sessions()
        session.refresh_from_db()
        self.assertEqual(session.status, 'bot')
        self.assertIsNone(session.inactivity_warning_at)

    def test_empty_session_is_never_contacted(self):
        session = ChatSession.objects.create(user_name='Sin mensajes', status='bot')
        close_inactive_bot_sessions()
        self.assertFalse(session.messages.exists())

    @patch('crmChat.tasks.dispatch_outbound_message', side_effect=MetaAPIError('destinatario inválido'))
    def test_failed_warning_does_not_start_close_timer_or_duplicate(self, _dispatch):
        session = self._session_after_bot_reply()
        self.assertEqual(close_inactive_bot_sessions()['warned'], 0)
        self.assertEqual(close_inactive_bot_sessions()['warned'], 0)
        session.refresh_from_db()
        self.assertIsNone(session.inactivity_warning_at)
        self.assertEqual(session.messages.filter(text=INACTIVITY_WARNING_TEXT).count(), 1)

    @patch('crmChat.tasks.ollama_service.get_bot_response')
    @patch('crmChat.tasks.dispatch_outbound_message')
    def test_failed_bot_reply_is_not_retried_or_regenerated(self, dispatch, ollama):
        session = ChatSession.objects.create(user_name='Reintento', status='bot')
        inbound = ChatMessage.objects.create(
            session=session, text='Hola', sender_type='user', direction='inbound',
        )
        reply = ChatMessage.objects.create(
            session=session, text='Respuesta existente', sender_type='bot',
            direction='outbound', status='failed', reply_to_message=inbound,
        )

        result = generate_omnichannel_bot_reply.run(inbound.id)
        reply.refresh_from_db()
        self.assertTrue(result['duplicate'])
        self.assertEqual(reply.status, 'failed')
        dispatch.assert_not_called()
        ollama.assert_not_called()
        self.assertEqual(ChatMessage.objects.filter(reply_to_message=inbound).count(), 1)

    def test_external_inactivity_closes_locally_without_sending_warning(self):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp sin avisos', channel='whatsapp', active=True,
            external_account_id='waba-no-warning', phone_number_id='phone-no-warning',
        )
        session = ChatSession.objects.create(
            user_name='Cliente', status='bot', channel='whatsapp', integration=integration,
            external_thread_id='customer-no-warning',
        )
        inbound = ChatMessage.objects.create(
            session=session, text='Hola', sender_type='user', direction='inbound',
            external_message_id='wamid.no-warning',
        )
        ChatMessage.objects.create(
            session=session, text='Respuesta', sender_type='bot', direction='outbound',
            status='sent', reply_to_message=inbound,
        )
        old = timezone.now() - timedelta(minutes=3, seconds=5)
        session.last_customer_message_at = old - timedelta(seconds=5)
        session.last_bot_message_at = old
        session.save(update_fields=['last_customer_message_at', 'last_bot_message_at'])

        result = close_inactive_bot_sessions()

        session.refresh_from_db()
        self.assertEqual(result, {'warned': 0, 'closed': 1})
        self.assertEqual(session.status, 'closed')
        self.assertFalse(session.messages.filter(metadata__system_event='inactivity_warning').exists())

    @patch('crmChat.tasks.ollama_service.get_bot_response')
    @patch('crmChat.tasks.dispatch_outbound_message')
    def test_external_bot_does_not_reply_when_integration_bot_is_disabled(self, dispatch, ollama):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp bot apagado', channel='whatsapp', active=True,
            external_account_id='waba-bot-off', phone_number_id='phone-bot-off',
            configuration={'bot_enabled': False},
        )
        session = ChatSession.objects.create(
            user_name='Cliente', status='bot', channel='whatsapp', integration=integration,
            external_thread_id='customer-bot-off',
        )
        inbound = ChatMessage.objects.create(
            session=session, text='Hola', sender_type='user', direction='inbound',
            external_message_id='wamid.bot-off',
        )

        result = generate_omnichannel_bot_reply.run(inbound.id)

        self.assertEqual(result, {'skipped': 'bot_disabled'})
        ollama.assert_not_called()
        dispatch.assert_not_called()
        self.assertFalse(ChatMessage.objects.filter(reply_to_message=inbound).exists())

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
        self.assertIsNone(session.conversation_state['budget'])
        self.assertEqual(session.conversation_state['topic'], 'shipping')
        self.assertIn('catálogo actual', responses['¿Cuál me recomiendas?'])
        self.assertIn('No tengo información confirmada', responses['¿Y hacen envíos?'])
        ollama_service.get_bot_response(
            '¿Cómo puedo elegir el modelo adecuado?',
            conversation_history=[
                {'role': 'user' if index % 2 == 0 else 'assistant', 'content': f'Mensaje {index}'}
                for index in range(20)
            ],
        )
        self.assertLessEqual(len(ollama_post.call_args.kwargs['json']['messages']), 12)

        response = self.client.post(reverse('bot-chat'), {
            'message': 'Quiero hablar con un asesor',
            'session_id': session_id,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['needs_agent'])
        session.refresh_from_db()
        self.assertTrue(session.conversation_state['needs_human'])
        self.assertEqual(session.status, 'waiting')

        bot_count = session.messages.filter(sender_type='bot').count()
        response = self.client.post(reverse('bot-chat'), {
            'message': '¿Sigues ahí?', 'session_id': session_id,
        }, format='json')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['message'], '')
        self.assertEqual(session.messages.filter(sender_type='bot').count(), bot_count)


class OmnichannelModelTests(APITestCase):
    @override_settings(
        META_GRAPH_API_URL='https://graph.facebook.test',
        META_CREDENTIALS_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
    )
    @patch('crmChat.apps.meta.services.requests.request')
    def test_graph_error_is_saved_on_integration_without_exposing_token(self, request_mock):
        token = 'private-page-token'
        integration = ChannelIntegration.objects.create(
            name='Facebook error', channel='facebook', active=True,
            external_account_id='page-error', page_id='page-error', graph_api_version='v26.0',
            access_token_encrypted=secret_store.encrypt(token),
        )
        request_mock.return_value = Mock(
            ok=False, status_code=400, content=b'json', headers={},
            json=lambda: {'error': {'code': 100, 'type': 'OAuthException', 'message': 'Campo inválido'}},
        )
        with self.assertRaises(MetaAPIError):
            graph_request(integration, 'GET', 'page-error')
        integration.refresh_from_db()
        self.assertEqual(integration.connection_status, 'error')
        self.assertIn('código 100', integration.last_error)
        self.assertNotIn(token, integration.last_error)

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

    def test_closed_external_conversations_do_not_block_a_new_active_session(self):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp sesiones', channel='whatsapp', active=True,
            external_account_id='waba-sessions', phone_number_id='phone-sessions',
        )
        for _ in range(2):
            ChatSession.objects.create(
                user_name='Cliente', channel='whatsapp', integration=integration,
                external_thread_id='protected-user', status='closed',
            )
        ChatSession.objects.create(
            user_name='Cliente', channel='whatsapp', integration=integration,
            external_thread_id='protected-user', status='bot',
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChatSession.objects.create(
                user_name='Duplicada', channel='whatsapp', integration=integration,
                external_thread_id='protected-user', status='waiting',
            )

    @patch('crmChat.apps.whatsapp.services.send_text')
    def test_whatsapp_free_text_requires_open_24_hour_window(self, send_text):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp ventana', channel='whatsapp', active=True,
            external_account_id='waba-window', phone_number_id='phone-window',
        )
        session = ChatSession.objects.create(
            user_name='Cliente', channel='whatsapp', integration=integration,
            external_thread_id='protected-user-window', status='active',
            last_customer_message_at=timezone.now() - timedelta(hours=25),
        )
        ChatMessage.objects.create(
            session=session, text='Mensaje antiguo', sender_type='user', direction='inbound',
            external_message_id='wamid.old-window',
        )
        outbound = ChatMessage.objects.create(
            session=session, text='Seguimiento', sender_type='agent', direction='outbound', status='queued',
        )
        with self.assertRaisesMessage(MetaAPIError, 'esperará una nueva interacción'):
            dispatch_outbound_message(outbound)
        send_text.assert_not_called()
        outbound.refresh_from_db()
        self.assertEqual(outbound.metadata['error_code'], 'reactive_window_closed')

    @patch('crmChat.apps.meta.services.graph_request')
    def test_whatsapp_template_is_blocked_without_calling_meta(self, graph_request):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp plantilla', channel='whatsapp', active=True,
            external_account_id='waba-template', phone_number_id='phone-template',
        )
        session = ChatSession.objects.create(
            user_name='Cliente', channel='whatsapp', integration=integration,
            external_thread_id='protected-user-template', status='active',
            last_customer_message_at=timezone.now() - timedelta(hours=25),
        )
        ChatMessage.objects.create(
            session=session, text='Mensaje antiguo', sender_type='user', direction='inbound',
            external_message_id='wamid.old-template',
        )
        outbound = ChatMessage.objects.create(
            session=session, text='', sender_type='agent', direction='outbound', status='queued',
            message_type='template',
            metadata={'outbound_payload': {'name': 'seguimiento', 'language_code': 'es'}},
        )
        with self.assertRaisesMessage(MetaAPIError, 'política de cero costos'):
            dispatch_outbound_message(outbound)
        outbound.refresh_from_db()
        self.assertEqual(outbound.status, 'failed')
        self.assertEqual(outbound.metadata['error_code'], 'paid_messaging_disabled')
        graph_request.assert_not_called()

    @patch('crmChat.apps.facebook.services.send_text')
    def test_facebook_message_is_blocked_outside_reactive_window(self, send_text):
        integration = ChannelIntegration.objects.create(
            name='Facebook ventana', channel='facebook', active=True,
            external_account_id='page-window', page_id='page-window',
        )
        session = ChatSession.objects.create(
            user_name='Cliente', channel='facebook', integration=integration,
            external_thread_id='psid-window', status='active',
            last_customer_message_at=timezone.now() - timedelta(hours=25),
        )
        ChatMessage.objects.create(
            session=session, text='Mensaje antiguo', sender_type='user', direction='inbound',
            external_message_id='mid.old-window',
        )
        outbound = ChatMessage.objects.create(
            session=session, text='Seguimiento', sender_type='agent',
            direction='outbound', status='queued',
        )

        with self.assertRaisesMessage(MetaAPIError, 'esperará una nueva interacción'):
            dispatch_outbound_message(outbound)

        send_text.assert_not_called()
        outbound.refresh_from_db()
        self.assertEqual(outbound.metadata['error_code'], 'reactive_window_closed')

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

    @override_settings(
        META_WEBHOOK_VERIFY_TOKEN_INSTAGRAM='ig-special-+%<token>',
        META_WEBHOOK_VERIFY_TOKEN_FACEBOOK='fb-special-token',
        META_WEBHOOK_VERIFY_TOKEN_WHATSAPP='wa-special-token',
    )
    def test_typed_webhooks_use_only_their_channel_token(self):
        instagram = self.client.get('/api/meta/instagram/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'ig-special-+%<token>',
            'hub.challenge': 'instagram-challenge',
        })
        self.assertEqual(instagram.status_code, 200)
        self.assertEqual(instagram.content, b'instagram-challenge')
        self.assertTrue(instagram['Content-Type'].startswith('text/plain'))

        facebook = self.client.get('/api/meta/facebook/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'fb-special-token',
            'hub.challenge': 'facebook-challenge',
        })
        self.assertEqual(facebook.status_code, 200)
        self.assertEqual(facebook.content, b'facebook-challenge')
        self.assertEqual(self.client.get('/api/meta/facebook/webhook/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'ig-special-+%<token>',
            'hub.challenge': 'must-not-return',
        }).status_code, 403)

    @override_settings(META_WEBHOOK_VERIFY_TOKEN_INSTAGRAM='instagram-secret')
    def test_instagram_rejects_invalid_empty_and_non_official_parameters(self):
        for candidate in ('wrong-token', ''):
            response = self.client.get('/api/meta/instagram/webhook/', {
                'hub.mode': 'subscribe',
                'hub.verify_token': candidate,
                'hub.challenge': 'must-not-return',
            })
            self.assertEqual(response.status_code, 403)
            self.assertNotIn(candidate or 'instagram-secret', response.content.decode())
        underscored = self.client.get('/api/meta/instagram/webhook/', {
            'hub_mode': 'subscribe',
            'hub_verify_token': 'instagram-secret',
            'hub_challenge': 'must-not-return',
        })
        self.assertEqual(underscored.status_code, 403)

    def test_unified_webhook_uses_global_token_and_rejects_unknown_payload(self):
        accepted = self.client.get(reverse('meta-webhook'), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'verify-test',
            'hub.challenge': 'global-challenge',
        })
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.content, b'global-challenge')
        self.assertEqual(self.client.get(reverse('meta-webhook'), {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong-global',
            'hub.challenge': 'must-not-return',
        }).status_code, 403)

        body = json.dumps({'object': 'unknown', 'entry': []}).encode()
        signature = 'sha256=' + hmac.new(b'app-secret-test', body, hashlib.sha256).hexdigest()
        response = self.client.post(
            reverse('meta-webhook'), data=body, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(
        META_WEBHOOK_VERIFY_TOKEN='',
        META_WEBHOOK_VERIFY_TOKEN_INSTAGRAM='',
    )
    def test_hashed_integration_token_fallback_is_scoped_to_channel(self):
        token = 'stored-instagram-token'
        ChannelIntegration.objects.create(
            name='Instagram hash', channel='instagram', active=True,
            verify_token_digest=secret_store.digest(token),
        )
        self.assertEqual(self.client.get('/api/meta/instagram/webhook/', {
            'hub.mode': 'subscribe', 'hub.verify_token': token, 'hub.challenge': 'ok',
        }).status_code, 200)
        self.assertEqual(self.client.get('/api/meta/facebook/webhook/', {
            'hub.mode': 'subscribe', 'hub.verify_token': token, 'hub.challenge': 'no',
        }).status_code, 403)

    def test_access_log_redaction_hides_both_meta_parameter_spellings(self):
        token = 'never-log-this-token'
        line = (
            f'GET /api/meta/instagram/webhook/?hub.verify_token={token}'
            f'&hub_verify_token={token}&hub.challenge=123 HTTP/1.1'
        )
        redacted = redact_webhook_tokens(line)
        self.assertNotIn(token, redacted)
        self.assertEqual(redacted.count('[REDACTED]'), 2)

    def test_invalid_signature_is_rejected(self):
        response = self._signed_post(signature='sha256=bad')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(WebhookEvent.objects.exists())

    def test_invalid_payload_and_wrong_channel_alias_return_400(self):
        self.assertEqual(self._signed_post(payload={'object': 'whatsapp_business_account', 'entry': 'invalid'}).status_code, 400)
        body = json.dumps(self.payload, separators=(',', ':')).encode()
        signature = 'sha256=' + hmac.new(b'app-secret-test', body, hashlib.sha256).hexdigest()
        response = self.client.post(
            '/api/meta/instagram/webhook/', data=body, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WebhookEvent.objects.exists())

    @patch('crmChat.apps.meta.views.process_meta_webhook_task.delay')
    def test_signed_whatsapp_alias_accepts_post(self, process_task):
        body = json.dumps(self.payload, separators=(',', ':')).encode()
        signature = 'sha256=' + hmac.new(b'app-secret-test', body, hashlib.sha256).hexdigest()
        response = self.client.post(
            '/api/meta/whatsapp/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 200)
        process_task.assert_called_once()

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
        self.assertEqual(WebhookEvent.objects.get().integration_id, self.integration.id)
        read_receipt.assert_called_once_with(message.id)

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    def test_facebook_and_instagram_signed_events_create_crm_conversations(self, read_receipt):
        cases = (
            ('facebook', 'page-test', 'psid-test', '/api/meta/facebook/webhook/'),
            ('instagram', 'ig-test', 'igsid-test', '/api/meta/instagram/webhook/'),
        )
        for channel, account_id, sender_id, endpoint in cases:
            with self.subTest(channel=channel):
                integration = ChannelIntegration.objects.create(
                    name=f'{channel} pruebas', channel=channel, active=True,
                    external_account_id=account_id,
                    page_id=account_id if channel == 'facebook' else 'page-for-instagram',
                    instagram_account_id=account_id if channel == 'instagram' else '',
                    graph_api_version='v-test', configuration={'bot_enabled': False},
                )
                payload = {
                    'object': 'page' if channel == 'facebook' else 'instagram',
                    'entry': [{
                        'id': account_id,
                        'messaging': [{
                            'sender': {'id': sender_id},
                            'recipient': {'id': account_id},
                            'timestamp': 1_700_000_000_000,
                            'message': {'mid': f'mid.{channel}.test', 'text': f'Prueba {channel}'},
                        }],
                    }],
                }
                body = json.dumps(payload, separators=(',', ':')).encode()
                signature = 'sha256=' + hmac.new(b'app-secret-test', body, hashlib.sha256).hexdigest()
                with self.assertLogs('crmChat', level='INFO') as logs:
                    response = self.client.post(
                        endpoint, data=body, content_type='application/json',
                        HTTP_X_HUB_SIGNATURE_256=signature,
                    )
                self.assertEqual(response.status_code, 200)
                message = ChatMessage.objects.get(external_message_id=f'mid.{channel}.test')
                self.assertEqual(message.session.channel, channel)
                self.assertEqual(message.session.integration_id, integration.id)
                self.assertEqual(message.direction, 'inbound')
                integration.refresh_from_db()
                self.assertEqual(integration.connection_status, 'connected')
                self.assertIsNotNone(integration.last_webhook_at)
                rendered_logs = '\n'.join(logs.output)
                self.assertIn('Webhook Meta recibido', rendered_logs)
                self.assertIn('Mensaje Meta persistido', rendered_logs)
        self.assertEqual(read_receipt.call_count, 2)

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    @patch('crmChat.apps.instagram.services.get_sender_profile')
    def test_instagram_enriches_profile_and_reopens_same_conversation(self, profile, _read_receipt):
        profile.return_value = {
            'id': 'igsid-customer',
            'name': 'Cliente Instagram Real',
            'username': 'cliente_real',
            'profile_pic': 'https://cdn.example.test/profile.jpg',
        }
        integration = ChannelIntegration.objects.create(
            name='Instagram perfil', channel='instagram', active=True,
            external_account_id='ig-profile', instagram_account_id='ig-profile',
            graph_api_version='v-test', configuration={'bot_enabled': False},
        )

        def payload(message_id, text):
            return {
                'object': 'instagram',
                'entry': [{
                    'id': 'ig-profile',
                    'messaging': [{
                        'sender': {'id': 'igsid-customer'},
                        'recipient': {'id': 'ig-profile'},
                        'timestamp': 1_700_000_000_000,
                        'message': {'mid': message_id, 'text': text},
                    }],
                }],
            }

        self.assertEqual(self._signed_post(payload('mid.ig.profile.1', 'Primer mensaje')).status_code, 200)
        session = ChatSession.objects.get(integration=integration)
        session.status = 'closed'
        session.save(update_fields=['status'])

        self.assertEqual(self._signed_post(payload('mid.ig.profile.2', 'Segundo mensaje')).status_code, 200)
        session.refresh_from_db()
        identity = ChannelIdentity.objects.get(integration=integration, external_id='igsid-customer')
        self.assertEqual(ChatSession.objects.filter(integration=integration).count(), 1)
        self.assertEqual(session.status, 'bot')
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(session.user_name, 'Cliente Instagram Real')
        self.assertEqual(identity.display_name, 'Cliente Instagram Real')
        self.assertEqual(identity.contact.name, 'Cliente Instagram Real')
        self.assertEqual(identity.contact.avatar_url, 'https://cdn.example.test/profile.jpg')
        self.assertIsNotNone(identity.contact.last_interaction_at)
        self.assertEqual(profile.call_count, 1)

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    @patch('crmChat.apps.facebook.services.get_sender_profile')
    def test_facebook_enriches_contact_profile_and_last_interaction(self, profile, _read_receipt):
        profile.return_value = {
            'id': 'psid-profile', 'name': 'Cliente Facebook Real',
            'first_name': 'Cliente', 'last_name': 'Facebook',
            'profile_pic': 'https://cdn.example.test/facebook.jpg',
        }
        integration = ChannelIntegration.objects.create(
            name='Facebook perfil', channel='facebook', active=True,
            external_account_id='page-profile', page_id='page-profile',
            graph_api_version='v-test', configuration={'bot_enabled': False},
        )
        payload = {
            'object': 'page',
            'entry': [{'id': 'page-profile', 'messaging': [{
                'sender': {'id': 'psid-profile'}, 'recipient': {'id': 'page-profile'},
                'timestamp': 1_700_000_000_000,
                'message': {'mid': 'mid.fb.profile.1', 'text': 'Hola'},
            }]}],
        }
        self.assertEqual(self._signed_post(payload).status_code, 200)
        identity = ChannelIdentity.objects.get(integration=integration, external_id='psid-profile')
        session = ChatSession.objects.get(integration=integration)
        self.assertEqual(session.user_name, 'Cliente Facebook Real')
        self.assertEqual(identity.display_name, 'Cliente Facebook Real')
        self.assertEqual(identity.contact.avatar_url, 'https://cdn.example.test/facebook.jpg')
        self.assertIsNotNone(identity.contact.last_interaction_at)
        profile.assert_called_once_with(integration, 'psid-profile')

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    def test_whatsapp_requires_matching_waba_and_phone_and_reconnects_to_new_account(self, _receipt):
        self.assertEqual(self._signed_post().status_code, 200)
        old_session = ChatSession.objects.get(channel='whatsapp')
        disconnect_integration(self.integration)
        self.integration.refresh_from_db()
        self.assertFalse(self.integration.active)
        self.assertEqual(old_session.messages.count(), 1)

        rejected = json.loads(json.dumps(self.payload))
        rejected['entry'][0]['changes'][0]['value']['messages'][0]['id'] = 'wamid.old-after-disconnect'
        self.assertEqual(self._signed_post(rejected).status_code, 200)
        self.assertFalse(ChatMessage.objects.filter(external_message_id='wamid.old-after-disconnect').exists())

        new_integration = ChannelIntegration.objects.create(
            name='Número nuevo', channel='whatsapp', active=True,
            external_account_id='waba-2', phone_number_id='phone-2',
        )
        new_payload = json.loads(json.dumps(self.payload))
        new_payload['entry'][0]['id'] = 'waba-2'
        new_payload['entry'][0]['changes'][0]['value']['metadata']['phone_number_id'] = 'phone-2'
        new_payload['entry'][0]['changes'][0]['value']['messages'][0]['id'] = 'wamid.new-account'
        self.assertEqual(self._signed_post(new_payload).status_code, 200)
        new_message = ChatMessage.objects.get(external_message_id='wamid.new-account')
        self.assertEqual(new_message.session.integration_id, new_integration.pk)
        old_session.refresh_from_db()
        self.assertEqual(old_session.integration_id, self.integration.pk)

        mismatched = json.loads(json.dumps(new_payload))
        mismatched['entry'][0]['id'] = 'waba-1'
        mismatched['entry'][0]['changes'][0]['value']['messages'][0]['id'] = 'wamid.mixed-ids'
        self.assertEqual(self._signed_post(mismatched).status_code, 200)
        self.assertFalse(ChatMessage.objects.filter(external_message_id='wamid.mixed-ids').exists())

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    def test_new_inbound_message_creates_new_whatsapp_session_without_old_history(self, _receipt):
        self._signed_post()
        session = ChatSession.objects.get(channel='whatsapp')
        original_count = session.messages.count()
        session.status = 'closed'
        session.save(update_fields=['status'])
        payload = json.loads(json.dumps(self.payload))
        payload['entry'][0]['changes'][0]['value']['messages'][0]['id'] = 'wamid.webhook-2'
        payload['entry'][0]['changes'][0]['value']['messages'][0]['text']['body'] = 'Necesito ayuda otra vez'
        self.assertEqual(self._signed_post(payload).status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'closed')
        self.assertEqual(session.messages.count(), original_count)
        sessions = ChatSession.objects.filter(channel='whatsapp').order_by('id')
        self.assertEqual(sessions.count(), 2)
        new_session = sessions.last()
        self.assertEqual(new_session.status, 'bot')
        self.assertEqual(new_session.external_thread_id, session.external_thread_id)
        self.assertEqual(new_session.messages.count(), 1)

    @patch('crmChat.tasks.send_meta_read_receipt.delay')
    def test_whatsapp_failed_delivery_preserves_meta_error_details(self, _receipt):
        self._signed_post()
        session = ChatSession.objects.get(channel='whatsapp')
        outbound = ChatMessage.objects.create(
            session=session, text='Respuesta', sender_type='bot', direction='outbound',
            status='sent', external_message_id='wamid.outbound-status',
        )
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{'id': 'waba-1', 'changes': [{
                'field': 'messages',
                'value': {
                    'metadata': {'phone_number_id': 'phone-1'},
                    'statuses': [{
                        'id': 'wamid.outbound-status',
                        'status': 'failed',
                        'timestamp': '1700000001',
                        'recipient_id': '573001234567',
                        'errors': [{'code': 131047, 'title': 'Re-engagement message'}],
                    }],
                },
            }]}],
        }
        self.assertEqual(self._signed_post(payload).status_code, 200)
        outbound.refresh_from_db()
        self.assertEqual(outbound.status, 'failed')
        self.assertEqual(outbound.metadata['meta_errors'][0]['code'], 131047)


@override_settings(
    META_APP_ID='facebook-app-test',
    META_APP_SECRET='facebook-secret-test',
    META_GRAPH_API_URL='https://graph.facebook.test',
    META_GRAPH_API_VERSION='v26.0',
    META_REDIRECT_URI='https://crm.example.test/api/meta/callback/',
    META_FACEBOOK_WEBHOOK_URL='https://crm.example.test/api/meta/facebook/webhook/',
    META_INSTAGRAM_WEBHOOK_URL='https://crm.example.test/api/meta/instagram/webhook/',
    META_WEBHOOK_VERIFY_TOKEN='webhook-verify-test',
    META_OAUTH_AUTHORIZE_URL='https://www.facebook.com',
    META_OAUTH_SCOPES=','.join(sorted(REQUIRED_SCOPES)),
    META_OAUTH_FRONTEND_REDIRECT='/admin/chat/integraciones',
    META_CREDENTIALS_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
)
class MetaFacebookInstagramOAuthTests(APITestCase):
    """Prueba OAuth/selección sin ejecutar solicitudes reales contra Meta."""

    def setUp(self):
        cache.clear()
        self.admin_user = Credenciales.objects.create(usuario='oauth_admin', tipo_usuario=1, estado=1)
        self.other_admin = Credenciales.objects.create(usuario='oauth_other', tipo_usuario=1, estado=1)
        self.client.force_authenticate(self.admin_user)

    @patch('crmChat.apps.instagram.services.graph_request')
    def test_instagram_facebook_login_sends_through_linked_page(self, graph_request_mock):
        from crmChat.apps.instagram.services import send_text

        connection = MetaConnection.objects.create(
            created_by=self.admin_user,
            facebook_user_id='facebook-routing',
            access_token_encrypted='encrypted-user-token',
        )
        page = MetaFacebookPage.objects.create(
            connection=connection,
            page_id='page-routing',
            page_name='Página routing',
            page_access_token_encrypted='encrypted-page-token',
        )
        integration = ChannelIntegration.objects.create(
            name='Instagram routing', channel='instagram', active=True,
            instagram_account_id='ig-routing', external_account_id='ig-routing',
            graph_api_version='v-test', meta_connection=connection, meta_facebook_page=page,
        )
        graph_request_mock.return_value = {'message_id': 'mid.sent'}

        send_text(integration, 'igsid-recipient', 'Respuesta reactiva')

        args, kwargs = graph_request_mock.call_args
        self.assertEqual(args[1:3], ('POST', 'page-routing/messages'))
        self.assertIsNone(kwargs['base_url'])
        self.assertEqual(kwargs['json_body']['messaging_type'], 'RESPONSE')
        self.assertEqual(kwargs['json_body']['recipient']['id'], 'igsid-recipient')

    @patch('crmChat.apps.instagram.services.graph_request')
    def test_instagram_login_keeps_native_send_endpoint(self, graph_request_mock):
        from crmChat.apps.instagram.services import send_text

        integration = ChannelIntegration.objects.create(
            name='Instagram Login', channel='instagram', active=True,
            instagram_account_id='ig-native', external_account_id='ig-native',
            graph_api_version='v-test', configuration={},
        )
        graph_request_mock.return_value = {'message_id': 'mid.sent'}

        send_text(integration, 'igsid-recipient', 'Respuesta reactiva')

        args, kwargs = graph_request_mock.call_args
        self.assertEqual(args[1:3], ('POST', 'ig-native/messages'))
        self.assertEqual(kwargs['base_url'], 'https://graph.instagram.com')
        self.assertNotIn('messaging_type', kwargs['json_body'])

    @staticmethod
    def _response(data, ok=True, status_code=200):
        return Mock(ok=ok, status_code=status_code, content=b'json', json=lambda: data)

    @patch('crmChat.apps.meta.oauth.requests.request')
    def test_page_details_reads_tasks_from_managed_pages_inventory(self, request_mock):
        request_mock.return_value = self._response({'data': [{
            'id': 'page-1', 'name': 'Página Uno', 'access_token': 'page-token',
            'tasks': ['MESSAGING'], 'instagram_business_account': {'id': 'instagram-1'},
        }]})
        page = get_page_details('page-1', 'user-token')
        self.assertEqual(page['tasks'], ['MESSAGING'])
        requested_url = request_mock.call_args.args[1]
        requested_fields = request_mock.call_args.kwargs['params']['fields']
        self.assertTrue(requested_url.endswith('/me/accounts'))
        self.assertIn('tasks', requested_fields)

    @patch('crmChat.apps.meta.oauth.requests.request')
    def test_selected_accounts_subscribe_app_objects_and_page_fields(self, request_mock):
        request_mock.return_value = self._response({'success': True})
        ensure_oauth_webhook_subscriptions(
            'page-1', 'page-token', facebook=True, instagram=True,
        )
        self.assertEqual(request_mock.call_count, 3)
        page_app = request_mock.call_args_list[0].kwargs['data']
        instagram_app = request_mock.call_args_list[1].kwargs['data']
        page_activation = request_mock.call_args_list[2].kwargs['data']
        self.assertEqual(page_app['object'], 'page')
        self.assertEqual(page_app['callback_url'], 'https://crm.example.test/api/meta/facebook/webhook/')
        self.assertIn('message_reads', page_app['fields'])
        self.assertNotIn('messaging_reads', page_app['fields'])
        self.assertEqual(instagram_app['object'], 'instagram')
        self.assertEqual(instagram_app['callback_url'], 'https://crm.example.test/api/meta/instagram/webhook/')
        self.assertIn('messages', page_activation['subscribed_fields'])

    def test_oauth_start_generates_unique_state_without_whatsapp_scopes(self):
        first = self.client.get(reverse('meta-connect'))
        second = self.client.get(reverse('meta-connect'))
        self.assertEqual(first.status_code, 200)
        first_query = parse_qs(urlparse(first.data['authorization_url']).query)
        second_query = parse_qs(urlparse(second.data['authorization_url']).query)
        self.assertNotEqual(first_query['state'], second_query['state'])
        self.assertEqual(first_query['redirect_uri'], ['https://crm.example.test/api/meta/callback/'])
        self.assertIn('instagram_manage_messages', first_query['scope'][0])
        self.assertNotIn('whatsapp', first_query['scope'][0])
        self.assertNotIn('facebook-secret-test', first.data['authorization_url'])

    def test_non_administrator_cannot_start_or_list_oauth_connections(self):
        user = Credenciales.objects.create(usuario='oauth_customer', tipo_usuario=2, estado=1)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse('meta-connect')).status_code, 403)
        self.assertEqual(self.client.get(reverse('meta-connections')).status_code, 403)

    @patch('crmChat.apps.meta.oauth.requests.request')
    def test_callback_discovers_pages_and_instagram_and_state_is_single_use(self, request_mock):
        start = self.client.get(reverse('meta-connect'))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        request_mock.side_effect = [
            self._response({'access_token': 'initial-user-token'}),
            self._response({'access_token': 'persistent-user-token'}),
            self._response({'data': {
                'is_valid': True,
                'user_id': 'facebook-user-1',
                'scopes': sorted(REQUIRED_SCOPES),
                'expires_at': 1_900_000_000,
            }}),
            self._response({'data': [{
                'id': 'page-1',
                'name': 'Página Uno',
                'access_token': 'page-token-secret',
                'tasks': ['MESSAGING'],
                'instagram_business_account': {
                    'id': 'instagram-1', 'username': 'empresa', 'name': 'Empresa',
                },
            }]}),
        ]
        callback = self.client.get(reverse('meta-callback'), {'code': 'valid-code', 'state': state})
        self.assertEqual(callback.status_code, 302)
        self.assertIn('meta_oauth=select', callback['Location'])
        connection = MetaConnection.objects.get(facebook_user_id='facebook-user-1')
        self.assertNotIn('persistent-user-token', connection.access_token_encrypted)
        page = MetaFacebookPage.objects.get(page_id='page-1')
        self.assertNotIn('page-token-secret', page.page_access_token_encrypted)
        self.assertTrue(MetaInstagramAccount.objects.filter(instagram_account_id='instagram-1').exists())

        replay = self.client.get(reverse('meta-callback'), {'code': 'valid-code', 'state': state})
        self.assertIn('meta_oauth=invalid_state', replay['Location'])
        self.assertEqual(request_mock.call_count, 4)

    @patch('crmChat.apps.meta.oauth.requests.request')
    def test_invalid_meta_token_is_not_saved(self, request_mock):
        start = self.client.get(reverse('meta-connect'))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        request_mock.side_effect = [
            self._response({'access_token': 'initial'}),
            self._response({'access_token': 'persistent'}),
            self._response({'data': {'is_valid': False}}),
        ]
        response = self.client.get(reverse('meta-callback'), {'code': 'bad-code', 'state': state})
        self.assertIn('meta_oauth=error', response['Location'])
        self.assertFalse(MetaConnection.objects.exists())

    @patch('crmChat.apps.meta.oauth.requests.request')
    def test_meta_http_error_does_not_expose_or_save_token(self, request_mock):
        start = self.client.get(reverse('meta-connect'))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        request_mock.return_value = self._response(
            {'error': {'code': 190, 'type': 'OAuthException', 'message': 'sensitive remote detail'}},
            ok=False,
            status_code=400,
        )
        response = self.client.get(reverse('meta-callback'), {'code': 'rejected-code', 'state': state})
        self.assertIn('meta_oauth=error', response['Location'])
        self.assertNotIn('sensitive', response['Location'])
        self.assertFalse(MetaConnection.objects.exists())

    @patch('crmChat.apps.meta.oauth.ensure_oauth_webhook_subscriptions')
    @patch('crmChat.apps.meta.oauth.get_instagram_account')
    @patch('crmChat.apps.meta.oauth.get_page_details')
    @patch('crmChat.apps.meta.oauth.validate_access_token')
    def test_selection_creates_channel_adapters_and_disconnect_is_non_destructive(
        self, validate_token, page_details, instagram_details, ensure_subscriptions,
    ):
        validate_token.return_value = {'is_valid': True, 'user_id': 'facebook-user-selection', 'scopes': sorted(REQUIRED_SCOPES)}
        page_details.return_value = {
            'id': 'page-selection', 'name': 'Página Selección',
            'access_token': 'fresh-page-token', 'tasks': ['MESSAGING'],
            'instagram_business_account': {'id': 'instagram-selection'},
        }
        instagram_details.return_value = {'id': 'instagram-selection', 'username': 'seleccion'}
        connection = MetaConnection.objects.create(
            created_by=self.admin_user,
            facebook_user_id='facebook-user-selection',
            access_token_encrypted=secret_store.encrypt('user-token'),
            granted_scopes=sorted(REQUIRED_SCOPES),
        )
        page = MetaFacebookPage.objects.create(
            connection=connection,
            page_id='page-selection',
            page_name='Página Selección',
            page_access_token_encrypted=secret_store.encrypt('page-token'),
        )
        instagram = MetaInstagramAccount.objects.create(
            facebook_page=page,
            instagram_account_id='instagram-selection',
            username='seleccion',
        )
        response = self.client.post(reverse('meta-connection-accounts', args=[connection.pk]), {
            'facebook_page_ids': [page.page_id],
            'instagram_account_ids': [instagram.instagram_account_id],
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ChannelIntegration.objects.get(channel='facebook').active)
        instagram_integration = ChannelIntegration.objects.get(channel='instagram')
        self.assertTrue(instagram_integration.active)
        self.assertEqual(instagram_integration.meta_facebook_page, page)
        integrations = self.client.get(reverse('meta-integrations'))
        instagram_payload = next(item for item in integrations.data if item['channel'] == 'instagram')
        self.assertTrue(instagram_payload['has_access_token'])
        self.assertTrue(instagram_payload['managed_by_meta_oauth'])
        ensure_subscriptions.assert_called_once_with(
            page.page_id, 'fresh-page-token', facebook=True, instagram=True,
        )

        disconnected = self.client.delete(reverse('meta-connection-detail', args=[connection.pk]))
        self.assertEqual(disconnected.status_code, 204)
        self.assertEqual(ChannelIntegration.objects.filter(active=True).count(), 0)
        self.assertTrue(ChannelIntegration.objects.filter(channel='facebook', external_account_id=page.page_id).exists())
        self.assertTrue(ChannelIntegration.objects.filter(channel='instagram', external_account_id=instagram.instagram_account_id).exists())
        connection.refresh_from_db()
        page.refresh_from_db()
        self.assertEqual(connection.access_token_encrypted, '')
        self.assertEqual(page.page_access_token_encrypted, '')

    @patch('crmChat.apps.meta.oauth.get_page_details')
    @patch('crmChat.apps.meta.oauth.validate_access_token')
    @patch('crmChat.apps.meta.views.MetaConnectionAccountsView.get_throttles', return_value=[])
    def test_selection_rejects_page_without_messaging_task_and_other_user_token(self, _throttles, validate_token, page_details):
        connection = MetaConnection.objects.create(
            created_by=self.admin_user, facebook_user_id='owner-one',
            access_token_encrypted=secret_store.encrypt('user-token'),
        )
        page = MetaFacebookPage.objects.create(
            connection=connection, page_id='page-available',
            page_access_token_encrypted=secret_store.encrypt('page-token'),
        )
        url = reverse('meta-connection-accounts', args=[connection.pk])
        selection = {'facebook_page_ids': [page.page_id]}
        validate_token.return_value = {'is_valid': True, 'user_id': 'someone-else', 'scopes': sorted(REQUIRED_SCOPES)}
        self.assertEqual(self.client.post(url, selection, format='json').status_code, 400)
        page_details.assert_not_called()
        self.assertFalse(ChannelIntegration.objects.filter(channel='facebook', active=True).exists())

        validate_token.return_value['user_id'] = 'owner-one'
        page_details.return_value = {'id': page.page_id, 'access_token': 'new-page-token', 'tasks': []}
        response = self.client.post(url, selection, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('tarea de mensajería', response.data['detail'])
        self.assertFalse(ChannelIntegration.objects.filter(channel='facebook', active=True).exists())

    def test_connection_cannot_be_read_or_disconnected_by_another_admin(self):
        connection = MetaConnection.objects.create(
            created_by=self.admin_user,
            facebook_user_id='private-facebook-user',
            access_token_encrypted=secret_store.encrypt('private-token'),
        )
        self.client.force_authenticate(self.other_admin)
        self.assertEqual(self.client.get(reverse('meta-connection-accounts', args=[connection.pk])).status_code, 404)
        self.assertEqual(self.client.delete(reverse('meta-connection-detail', args=[connection.pk])).status_code, 404)

    def test_disconnect_invalidates_pending_oauth_state(self):
        start = self.client.get(reverse('meta-connect'))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        connection = MetaConnection.objects.create(
            created_by=self.admin_user, facebook_user_id='account-to-disconnect',
            access_token_encrypted=secret_store.encrypt('old-user-token'),
        )
        self.assertEqual(self.client.delete(reverse('meta-connection-detail', args=[connection.pk])).status_code, 204)
        with patch('crmChat.apps.meta.oauth.requests.request') as graph_request:
            callback = self.client.get(reverse('meta-callback'), {'code': 'stale-code', 'state': state})
            self.assertIn('meta_oauth=invalid_state', callback['Location'])
            graph_request.assert_not_called()

    def test_cancelled_callback_does_not_create_connection(self):
        response = self.client.get(reverse('meta-callback'), {'error': 'access_denied'})
        self.assertIn('meta_oauth=denied', response['Location'])
        self.assertFalse(MetaConnection.objects.exists())


@override_settings(
    META_APP_ID='whatsapp-app-id',
    META_APP_SECRET='whatsapp-app-secret',
    META_GRAPH_API_URL='https://graph.facebook.test',
    META_GRAPH_API_VERSION='v26.0',
    META_WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID='coexistence-config-id',
    META_WHATSAPP_EMBEDDED_SIGNUP_VERSION='4',
    META_CREDENTIALS_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
)
class WhatsAppCoexistenceTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = Credenciales.objects.create(usuario='coexistence_admin', tipo_usuario=1, estado=1)
        self.client.force_authenticate(self.admin)

    def test_configuration_is_admin_only_and_contains_no_secret(self):
        response = self.client.get(reverse('whatsapp-coexistence-config'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['app_id'], 'whatsapp-app-id')
        self.assertEqual(response.data['config_id'], 'coexistence-config-id')
        self.assertEqual(response.data['feature_type'], 'whatsapp_business_app_onboarding')
        self.assertNotIn('secret', json.dumps(response.data).lower())

        user = Credenciales.objects.create(usuario='coexistence_customer', tipo_usuario=2, estado=1)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse('whatsapp-coexistence-config')).status_code, 403)

    @patch('crmChat.apps.whatsapp.coexistence.validate_integration_connection')
    @patch('crmChat.apps.whatsapp.coexistence.graph_request')
    @patch('crmChat.apps.whatsapp.coexistence.validate_whatsapp_token_permissions')
    @patch('crmChat.apps.whatsapp.coexistence.requests.get')
    def test_signup_connects_existing_business_app_without_sending_messages(
        self, token_request, validate_token, graph_request, validate_connection,
    ):
        configuration = self.client.get(reverse('whatsapp-coexistence-config')).data
        token_request.return_value = Mock(
            ok=True, status_code=200, content=b'json',
            json=lambda: {'access_token': 'coexistence-private-token'},
        )
        graph_request.side_effect = [
            {
                'id': '1111111111', 'name': 'IMPORGAS JJ',
                'owner_business_info': {'id': '3333333333', 'name': 'IMPORGAS JJ'},
            },
            {'data': [{
                'id': '2222222222', 'display_phone_number': '+57 300 111 2233',
                'verified_name': 'IMPORGAS JJ', 'platform_type': 'CLOUD_API',
            }]},
            {'success': True},
        ]
        validate_connection.return_value = {
            'valid': True, 'remote_id': '2222222222',
            'display_phone_number': '+57 300 111 2233', 'name': 'IMPORGAS JJ',
        }
        response = self.client.post(reverse('whatsapp-coexistence-complete'), {
            'state': configuration['state'],
            'code': 'one-use-authorization-code',
            'event': 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
            'waba_id': '1111111111',
            'phone_number_id': '2222222222',
            'business_id': '3333333333',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['integration']['whatsapp_coexistence'])
        integration = ChannelIntegration.objects.get(channel='whatsapp')
        self.assertTrue(integration.active)
        self.assertEqual(integration.external_account_id, '1111111111')
        self.assertEqual(integration.phone_number_id, '2222222222')
        self.assertTrue(integration.configuration['coexistence'])
        self.assertFalse(integration.configuration['bot_enabled'])
        self.assertEqual(secret_store.decrypt(integration.access_token_encrypted), 'coexistence-private-token')
        self.assertNotIn('coexistence-private-token', json.dumps(response.data))
        validate_token.assert_called_once_with(integration)
        self.assertEqual(graph_request.call_args_list[0].args[2], '1111111111')
        self.assertEqual(graph_request.call_args_list[1].args[2], '1111111111/phone_numbers')
        self.assertEqual(graph_request.call_args_list[2].args[1:3], ('POST', '1111111111/subscribed_apps'))
        self.assertFalse(any('/messages' in str(call) for call in graph_request.call_args_list))
        self.assertTrue(ChatAuditEvent.objects.filter(action='whatsapp.coexistence_connected').exists())

        replay = self.client.post(reverse('whatsapp-coexistence-complete'), {
            'state': configuration['state'], 'code': 'replayed-code',
            'event': 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
            'waba_id': '1111111111', 'phone_number_id': '2222222222',
        }, format='json')
        self.assertEqual(replay.status_code, 400)
        self.assertIn('expiró', replay.data['detail'])
        self.assertEqual(token_request.call_count, 1)

    @patch('crmChat.apps.whatsapp.coexistence.graph_request')
    @patch('crmChat.apps.whatsapp.coexistence.validate_whatsapp_token_permissions')
    @patch('crmChat.apps.whatsapp.coexistence.requests.get')
    def test_failed_subscription_stays_inactive_and_records_safe_error(
        self, token_request, _validate_token, graph_request,
    ):
        configuration = self.client.get(reverse('whatsapp-coexistence-config')).data
        token_request.return_value = Mock(
            ok=True, status_code=200, content=b'json', json=lambda: {'access_token': 'private-token'},
        )
        graph_request.side_effect = [
            {
                'id': '4444444444', 'name': 'IMPORGAS JJ',
                'owner_business_info': {'id': '6666666666', 'name': 'IMPORGAS JJ'},
            },
            {'data': [{'id': '5555555555', 'display_phone_number': '+57 300 000 0000'}]},
            {'success': False},
        ]
        response = self.client.post(reverse('whatsapp-coexistence-complete'), {
            'state': configuration['state'], 'code': 'valid-code',
            'event': 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
            'waba_id': '4444444444', 'phone_number_id': '5555555555',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        integration = ChannelIntegration.objects.get(external_account_id='4444444444')
        self.assertFalse(integration.active)
        self.assertEqual(integration.connection_status, 'error')
        self.assertNotIn('private-token', integration.last_error)
        self.assertNotIn('private-token', json.dumps(response.data))

    @patch('crmChat.apps.whatsapp.coexistence.graph_request')
    @patch('crmChat.apps.whatsapp.coexistence.validate_whatsapp_token_permissions')
    @patch('crmChat.apps.whatsapp.coexistence.requests.get')
    def test_business_id_must_own_the_authorized_waba(
        self, token_request, _validate_token, graph_request,
    ):
        configuration = self.client.get(reverse('whatsapp-coexistence-config')).data
        token_request.return_value = Mock(
            ok=True, status_code=200, content=b'json', json=lambda: {'access_token': 'private-token'},
        )
        graph_request.return_value = {
            'id': '7777777777',
            'owner_business_info': {'id': '8888888888', 'name': 'Negocio autorizado'},
        }
        response = self.client.post(reverse('whatsapp-coexistence-complete'), {
            'state': configuration['state'], 'code': 'valid-code',
            'event': 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
            'waba_id': '7777777777', 'phone_number_id': '9999999999',
            'business_id': '6666666666',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no es el propietario', response.data['detail'])
        integration = ChannelIntegration.objects.get(external_account_id='7777777777')
        self.assertFalse(integration.active)
        self.assertFalse(any('/messages' in str(call) for call in graph_request.call_args_list))

    @override_settings(META_WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID='')
    def test_missing_configuration_returns_explicit_safe_503(self):
        response = self.client.get(reverse('whatsapp-coexistence-config'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['error'], 'configuration_missing')
        self.assertEqual(response.data['phase'], 'configuration')
        self.assertIn('META_WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID', response.data['detail'])
        self.assertNotIn('whatsapp-app-secret', json.dumps(response.data))

    @patch('crmChat.apps.whatsapp.coexistence.requests.get')
    def test_meta_code_exchange_error_is_diagnostic_and_hides_code(self, token_request):
        configuration = self.client.get(reverse('whatsapp-coexistence-config')).data
        token_request.return_value = Mock(
            ok=False,
            status_code=400,
            content=b'json',
            headers={'x-fb-request-id': 'safe-request-reference'},
            json=lambda: {
                'error': {
                    'code': 100,
                    'error_subcode': 36008,
                    'message': 'Authorization code one-use-secret-code is invalid.',
                },
            },
        )
        response = self.client.post(reverse('whatsapp-coexistence-complete'), {
            'state': configuration['state'], 'code': 'one-use-secret-code',
            'event': 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
            'waba_id': '1111111111', 'phone_number_id': '2222222222',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['phase'], 'code_exchange')
        self.assertEqual(response.data['http_status'], 400)
        self.assertEqual(response.data['meta_code'], 100)
        self.assertEqual(response.data['meta_subcode'], 36008)
        self.assertEqual(response.data['request_id'], 'safe-request-reference')
        self.assertNotIn('one-use-secret-code', json.dumps(response.data))
        self.assertFalse(ChannelIntegration.objects.exists())


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

    def test_whatsapp_protected_user_id_is_normalized(self):
        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{'id': 'waba-1', 'changes': [{
                'field': 'messages',
                'value': {
                    'metadata': {'phone_number_id': 'phone-1'},
                    'contacts': [{'user_id': 'protected-user-1', 'profile': {'name': 'Cliente'}}],
                    'messages': [{
                        'from_user_id': 'protected-user-1', 'id': 'wamid.protected-1',
                        'timestamp': '1700000000', 'type': 'text', 'text': {'body': 'Hola'},
                    }],
                },
            }]}],
        }
        event = normalize_payload(payload)[0]
        self.assertEqual(event.sender_id, 'protected-user-1')
        self.assertEqual(event.sender_name, 'Cliente')

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
        cache.clear()
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

    def test_client_cannot_activate_an_unvalidated_integration(self):
        response = self.client.post(reverse('meta-integrations'), {
            'name': 'WhatsApp pendiente', 'channel': 'whatsapp',
            'external_account_id': 'waba-pending', 'phone_number_id': 'phone-pending',
            'active': True, 'access_token': 'secret-token',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        integration = ChannelIntegration.objects.get(pk=response.data['id'])
        self.assertFalse(integration.active)
        self.assertEqual(integration.connection_status, 'pending')
        self.assertNotIn('secret-token', json.dumps(response.data))

    @override_settings(META_APP_ID='meta-app', META_APP_SECRET='meta-secret', META_GRAPH_API_URL='https://graph.facebook.test')
    @patch('crmChat.apps.meta.services.graph_request')
    @patch('crmChat.apps.meta.services.requests.get')
    def test_whatsapp_activation_checks_token_permissions_and_waba_phone_relation(self, token_request, graph_request):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp por validar', channel='whatsapp',
            external_account_id='waba-valid', phone_number_id='phone-valid',
            graph_api_version='v26.0', access_token_encrypted=secret_store.encrypt('token-private'),
        )
        token_request.return_value = Mock(ok=True, content=b'json', json=lambda: {'data': {
            'is_valid': True, 'app_id': 'meta-app',
            'scopes': ['whatsapp_business_management', 'whatsapp_business_messaging'],
        }})
        graph_request.side_effect = [
            {'data': [{'id': 'phone-valid', 'display_phone_number': '+57 300 123 4567'}]},
            {'id': 'phone-valid', 'display_phone_number': '+57 300 123 4567', 'verified_name': 'Empresa'},
            {'data': [{'whatsapp_business_api_data': {'id': 'meta-app'}}]},
        ]
        response = self.client.post(reverse('meta-integration-validate', args=[integration.pk]), {'activate': True}, format='json')
        self.assertEqual(response.status_code, 200)
        integration.refresh_from_db()
        self.assertTrue(integration.active)
        self.assertEqual(integration.connection_status, 'pending')
        self.assertEqual(integration.display_phone_number, '+57 300 123 4567')
        self.assertIsNotNone(integration.last_validated_at)
        self.assertEqual(graph_request.call_args_list[0].args[2], 'waba-valid/phone_numbers')
        self.assertNotIn('token-private', json.dumps(response.data))

    @override_settings(META_APP_ID='meta-app', META_APP_SECRET='meta-secret', META_GRAPH_API_URL='https://graph.facebook.test')
    @patch('crmChat.apps.meta.services.graph_request')
    @patch('crmChat.apps.meta.services.requests.get')
    def test_whatsapp_rejects_token_without_messaging_scope_and_wrong_phone(self, token_request, graph_request):
        integration = ChannelIntegration.objects.create(
            name='WhatsApp inválido', channel='whatsapp',
            external_account_id='waba-invalid', phone_number_id='phone-other',
            graph_api_version='v26.0', access_token_encrypted=secret_store.encrypt('token-private'),
        )
        token_request.return_value = Mock(ok=True, content=b'json', json=lambda: {'data': {
            'is_valid': True, 'app_id': 'meta-app', 'scopes': ['whatsapp_business_management'],
        }})
        denied = self.client.post(reverse('meta-integration-validate', args=[integration.pk]), {'activate': True}, format='json')
        self.assertEqual(denied.status_code, 400)
        graph_request.assert_not_called()
        integration.refresh_from_db()
        self.assertFalse(integration.active)

        self.assertEqual(integration.connection_status, 'error')

        token_request.return_value = Mock(ok=True, content=b'json', json=lambda: {'data': {
            'is_valid': True, 'app_id': 'meta-app',
            'scopes': ['whatsapp_business_management', 'whatsapp_business_messaging'],
        }})
        graph_request.return_value = {'data': [{'id': 'phone-someone-else'}]}
        denied = self.client.post(reverse('meta-integration-validate', args=[integration.pk]), {'activate': True}, format='json')
        self.assertEqual(denied.status_code, 400)
        self.assertIn('no pertenece', denied.data['detail'])
        integration.refresh_from_db()
        self.assertFalse(integration.active)

        graph_request.side_effect = [
            {'data': [{'id': 'phone-other'}]},
            {'id': 'phone-other', 'display_phone_number': '+57 300 000 0000'},
            {'data': []},
        ]
        denied = self.client.post(reverse('meta-integration-validate', args=[integration.pk]), {'activate': True}, format='json')
        self.assertEqual(denied.status_code, 400)
        self.assertIn('no está suscrita', denied.data['detail'])
        integration.refresh_from_db()
        self.assertFalse(integration.active)

    def test_active_whatsapp_phone_cannot_be_attached_to_two_accounts(self):
        ChannelIntegration.objects.create(
            name='Cuenta A', channel='whatsapp', active=True,
            external_account_id='waba-a', phone_number_id='phone-shared',
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChannelIntegration.objects.create(
                name='Cuenta B', channel='whatsapp', active=True,
                external_account_id='waba-b', phone_number_id='phone-shared',
            )

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
        INSTAGRAM_OAUTH_AUTHORIZE_URL='https://www.instagram.com/oauth/authorize',
        INSTAGRAM_OAUTH_SCOPES='instagram_business_basic,instagram_business_manage_messages',
    )
    def test_instagram_disconnect_invalidates_pending_oauth_state(self):
        integration = ChannelIntegration.objects.create(
            name='Instagram por desconectar', channel='instagram', app_id='instagram-app-id',
            app_secret_encrypted=secret_store.encrypt('instagram-app-secret'),
        )
        start = self.client.post(reverse('instagram-oauth-start', args=[integration.pk]))
        state = parse_qs(urlparse(start.data['authorization_url']).query)['state'][0]
        self.assertEqual(self.client.delete(reverse('meta-integration-detail', args=[integration.pk])).status_code, 204)
        with patch('crmChat.apps.instagram.services.requests.post') as token_request:
            callback = self.client.get(reverse('instagram-oauth-callback'), {'code': 'old-code', 'state': state})
            self.assertIn('instagram_oauth=invalid_state', callback['Location'])
            token_request.assert_not_called()

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
        get.side_effect = [
            Mock(ok=True, status_code=200, content=b'json', json=lambda: {
                'access_token': 'long-lived-token', 'expires_in': 5_184_000,
            }),
            Mock(ok=True, status_code=200, content=b'json', json=lambda: {
                'id': 'ig-professional-123', 'username': 'empresa', 'account_type': 'BUSINESS',
            }),
        ]

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
