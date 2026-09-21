import base64
import hashlib
import hmac
import json
import tempfile
import time
import uuid
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from usuarios.models import Credenciales
from crmChat.models import ChannelIntegration, ChatAttachment, ChatMessage, ChatSession
from crmChat.apps.whatsapp_web.services import send_message


TEST_SECRET = 'test-internal-secret-with-at-least-32-bytes'


@override_settings(
    CRM_INTERNAL_SERVICE_TOKEN=TEST_SECRET,
    WHATSAPP_GATEWAY_CONNECTION_ID='primary',
    WHATSAPP_GATEWAY_REQUEST_MAX_AGE=300,
    WHATSAPP_GATEWAY_BOT_ENABLED=False,
)
class WhatsAppWebInternalAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def signed_post(self, path, payload, *, secret=TEST_SECRET, timestamp=None, request_id=None):
        raw = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()
        timestamp = str(timestamp if timestamp is not None else int(time.time()))
        request_id = request_id or str(uuid.uuid4())
        signature = hmac.new(secret.encode(), f'{timestamp}.{request_id}.'.encode() + raw, hashlib.sha256).hexdigest()
        return self.client.generic(
            'POST', path, raw, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {secret}',
            HTTP_X_WHATSAPP_GATEWAY_TIMESTAMP=timestamp,
            HTTP_X_WHATSAPP_GATEWAY_REQUEST_ID=request_id,
            HTTP_X_WHATSAPP_GATEWAY_SIGNATURE=signature,
        )

    def connect(self, **extra):
        return self.signed_post('/internal/whatsapp/status/', {
            'connection_id': 'primary', 'status': 'connected', 'phone_number': '573001112233', **extra,
        })

    def incoming(self, **extra):
        payload = {
            'connection_id': 'primary', 'idempotency_key': f'primary:573001112233@s.whatsapp.net:{uuid.uuid4()}',
            'remote_jid': '573001112233@s.whatsapp.net', 'number': '573001112233', 'push_name': 'Cliente',
            'message_id': str(uuid.uuid4()), 'timestamp': int(time.time()), 'type': 'text', 'text': 'Hola',
            'quoted_message_id': '', 'is_group': False,
        }
        payload.update(extra)
        return self.signed_post('/internal/whatsapp/webhook/', payload), payload

    def test_internal_endpoint_rejects_missing_signature(self):
        response = self.client.post('/internal/whatsapp/status/', {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_internal_endpoint_rejects_old_timestamp(self):
        response = self.signed_post('/internal/whatsapp/status/', {}, timestamp=int(time.time()) - 301)
        self.assertEqual(response.status_code, 403)

    def test_internal_endpoint_rejects_replayed_request(self):
        request_id = str(uuid.uuid4())
        first = self.signed_post('/internal/whatsapp/status/', {'connection_id': 'primary', 'status': 'connected'}, request_id=request_id)
        second = self.signed_post('/internal/whatsapp/status/', {'connection_id': 'primary', 'status': 'connected'}, request_id=request_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 403)

    def test_status_creates_and_updates_experimental_integration(self):
        self.assertEqual(self.connect(last_connected_at='2026-09-19T12:00:00Z').status_code, 200)
        integration = ChannelIntegration.objects.get(channel='whatsapp_web', external_account_id='primary')
        self.assertTrue(integration.active)
        self.assertTrue(integration.configuration['experimental'])
        self.assertEqual(integration.display_phone_number, '573001112233')
        response = self.signed_post('/internal/whatsapp/status/', {'connection_id': 'primary', 'status': 'disconnected'})
        self.assertEqual(response.status_code, 200)
        integration.refresh_from_db()
        self.assertFalse(integration.active)

    def test_incoming_text_is_normalized_and_idempotent(self):
        self.connect()
        response, payload = self.incoming()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ChatSession.objects.get().channel, 'whatsapp_web')
        message = ChatMessage.objects.get()
        self.assertEqual(message.text, 'Hola')
        duplicate = self.signed_post('/internal/whatsapp/webhook/', payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertFalse(duplicate.data['created'])
        self.assertEqual(ChatMessage.objects.count(), 1)

    def test_device_jid_is_normalized_and_real_message_id_is_the_only_dedup_key(self):
        self.connect()
        response, payload = self.incoming(
            remote_jid='573001112233:0@s.whatsapp.net',
            source_jid='573001112233:0@s.whatsapp.net',
            idempotency_key='untrusted-first-key',
            message_id='same-whatsapp-id',
        )
        self.assertEqual(response.status_code, 201)
        session = ChatSession.objects.get()
        self.assertEqual(session.external_thread_id, '573001112233@s.whatsapp.net')
        message = ChatMessage.objects.get()
        self.assertEqual(message.external_message_id, 'ww:primary:same-whatsapp-id')
        payload['idempotency_key'] = 'different-retry-key'
        duplicate = self.signed_post('/internal/whatsapp/webhook/', payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(ChatMessage.objects.count(), 1)

    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay')
    def test_mobile_and_history_messages_are_synchronized_without_running_ollama(self, delay):
        self.connect()
        mobile, _ = self.incoming(origin='mobile', event_source='notify', message_id='mobile-1')
        history, _ = self.incoming(origin='customer', event_source='history', message_id='history-1')
        self.assertEqual(mobile.status_code, 201)
        self.assertEqual(history.status_code, 201)
        mobile_message = ChatMessage.objects.get(metadata__gateway_message_id='mobile-1')
        self.assertEqual(mobile_message.direction, 'outbound')
        self.assertEqual(mobile_message.sender_name, 'Celular')
        self.assertEqual(mobile_message.metadata['origin'], 'mobile')
        delay.assert_not_called()

    def test_crm_echo_updates_existing_message_instead_of_creating_a_duplicate(self):
        self.connect()
        integration = ChannelIntegration.objects.get(channel='whatsapp_web')
        session = ChatSession.objects.create(
            integration=integration, channel='whatsapp_web',
            external_thread_id='573001112233@s.whatsapp.net', status='active',
        )
        original = ChatMessage.objects.create(
            session=session, text='Respuesta', sender_type='agent', direction='outbound', status='queued',
            metadata={'client_message_id': '11111111-1111-1111-1111-111111111111', 'origin': 'crm'},
        )
        response, _ = self.incoming(
            origin='crm', message_id='crm-external-1',
            client_message_id='11111111-1111-1111-1111-111111111111',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatMessage.objects.count(), 1)
        original.refresh_from_db()
        self.assertEqual(original.status, 'sent')
        self.assertEqual(original.external_message_id, 'ww:primary:crm-external-1')

    def test_new_live_message_reopens_latest_session_and_preserves_history(self):
        self.connect()
        first, payload = self.incoming(message_id='first-id')
        self.assertEqual(first.status_code, 201)
        session = ChatSession.objects.get()
        session.status = 'closed'
        session.save(update_fields=['status'])
        payload.update(message_id='second-id', idempotency_key='retry-does-not-matter', text='Segundo')
        second = self.signed_post('/internal/whatsapp/webhook/', payload)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(ChatSession.objects.count(), 1)
        session.refresh_from_db()
        self.assertEqual(session.status, 'bot')
        self.assertEqual(session.messages.count(), 2)

    def test_group_and_non_user_jids_are_ignored(self):
        self.connect()
        group, _ = self.incoming(remote_jid='120363000000@g.us', is_group=True)
        broadcast, _ = self.incoming(remote_jid='status@broadcast')
        self.assertEqual(group.status_code, 200)
        self.assertEqual(broadcast.status_code, 200)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_lid_conversation_is_preserved_when_phone_mapping_is_unavailable(self):
        self.connect()
        response, _ = self.incoming(
            remote_jid='123456789012345@lid', source_jid='123456789012345@lid', number='',
        )
        self.assertEqual(response.status_code, 201)
        session = ChatSession.objects.get()
        self.assertEqual(session.external_thread_id, '123456789012345@lid')
        self.assertEqual(session.channel, 'whatsapp_web')

    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay')
    def test_bot_is_only_queued_when_explicitly_enabled(self, delay):
        self.connect()
        self.incoming()
        delay.assert_not_called()
        integration = ChannelIntegration.objects.get(channel='whatsapp_web')
        integration.configuration = {**integration.configuration, 'bot_enabled': True}
        integration.save(update_fields=['configuration'])
        response, _ = self.incoming()
        self.assertEqual(response.status_code, 201)
        delay.assert_called_once()

    def test_whatsapp_contact_fallback_and_later_push_name_update(self):
        self.connect()
        first, payload = self.incoming(push_name='', message_id='fallback-name-1')
        self.assertEqual(first.status_code, 201)
        session = ChatSession.objects.get()
        self.assertEqual(session.contact.name, 'Usuario de WhatsApp')
        self.assertEqual(session.user_name, 'Usuario de WhatsApp')

        payload.update(message_id='fallback-name-2', push_name='Nombre Real')
        second = self.signed_post('/internal/whatsapp/webhook/', payload)
        self.assertEqual(second.status_code, 201)
        session.refresh_from_db()
        session.contact.refresh_from_db()
        self.assertEqual(session.contact.name, 'Nombre Real')
        self.assertEqual(session.user_name, 'Nombre Real')

    def test_media_is_stored_and_attached_without_public_url(self):
        media_root = tempfile.mkdtemp(prefix='whatsapp-web-test-')
        with self.settings(MEDIA_ROOT=media_root):
            self.connect()
            media = self.signed_post('/internal/whatsapp/media/', {
                'connection_id': 'primary', 'mime_type': 'image/png', 'file_name': '../../foto.png',
                'data_base64': base64.b64encode(b'png-data').decode(),
            })
            self.assertEqual(media.status_code, 201)
            response, _ = self.incoming(type='image', text='Foto', media={'media_id': media.data['media_id']})
            self.assertEqual(response.status_code, 201)
            attachment = ChatAttachment.objects.get()
            self.assertEqual(attachment.original_name, 'foto.png')
            self.assertTrue(attachment.metadata['protected'])


@override_settings(CRM_INTERNAL_SERVICE_TOKEN=TEST_SECRET, WHATSAPP_GATEWAY_CONNECTION_ID='primary')
class WhatsAppWebAdminAndOutboundTests(APITestCase):
    def setUp(self):
        self.admin = Credenciales.objects.create(usuario='gateway_admin', tipo_usuario=1, estado=1)
        self.customer = Credenciales.objects.create(usuario='gateway_customer', tipo_usuario=2, estado=1)

    def test_gateway_admin_endpoints_reject_customer(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/crm-chat/whatsapp-web/status/').status_code, 403)
        self.assertEqual(self.client.post('/crm-chat/whatsapp-web/realtime-token/').status_code, 403)

    def test_realtime_token_is_short_lived_and_contains_no_service_secret(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/crm-chat/whatsapp-web/realtime-token/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['expires_in'], 120)
        self.assertNotIn(TEST_SECRET, response.data['token'])

    def test_admin_can_enable_reactive_bot_and_customer_cannot(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.patch('/crm-chat/whatsapp-web/status/', {'bot_enabled': True}, format='json').status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.patch('/crm-chat/whatsapp-web/status/', {'bot_enabled': True}, format='json')
        self.assertEqual(response.status_code, 200)
        integration = ChannelIntegration.objects.get(channel='whatsapp_web', external_account_id='primary')
        self.assertTrue(integration.configuration['bot_enabled'])

    @patch('crmChat.apps.whatsapp_web.views.gateway_request')
    def test_admin_command_is_proxied_and_audited(self, gateway):
        gateway.return_value = {'status': 'connecting'}
        self.client.force_authenticate(self.admin)
        response = self.client.post('/crm-chat/whatsapp-web/commands/qr/')
        self.assertEqual(response.status_code, 202)
        gateway.assert_called_once_with('/internal/whatsapp/connect/', {'connection_id': 'primary', 'force_qr': True})

    @patch('crmChat.apps.whatsapp_web.services.gateway_request')
    def test_outbound_payload_is_single_recipient_and_has_no_null_fields(self, gateway):
        integration = ChannelIntegration.objects.create(
            name='Gateway', channel='whatsapp_web', active=True, external_account_id='primary',
        )
        session = ChatSession.objects.create(
            integration=integration, channel='whatsapp_web', external_thread_id='573001112233@s.whatsapp.net',
        )
        message = ChatMessage.objects.create(
            session=session, text='Respuesta', sender_type='agent', direction='outbound', message_type='text',
        )
        gateway.return_value = {'external_message_id': 'wa-1', 'status': 'sent'}
        result = send_message(message, {})
        self.assertEqual(result['external_message_id'], 'ww:primary:wa-1')
        self.assertEqual(result['gateway_message_id'], 'wa-1')
        payload = gateway.call_args.args[1]
        self.assertEqual(payload['to'], '573001112233@s.whatsapp.net')
        self.assertNotIn('url', payload)
        self.assertNotIn('reply_to', payload)
        message.refresh_from_db()
        self.assertEqual(message.metadata['client_message_id'], payload['client_message_id'])
        self.assertEqual(message.client_message_id, payload['client_message_id'])

    @patch('crmChat.apps.whatsapp_web.services.gateway_request')
    def test_outbound_rotates_stale_gateway_operation_after_database_restore(self, gateway):
        integration = ChannelIntegration.objects.create(
            name='Gateway', channel='whatsapp_web', active=True, external_account_id='primary',
        )
        session = ChatSession.objects.create(
            integration=integration, channel='whatsapp_web', external_thread_id='573001112233@s.whatsapp.net',
        )
        ChatMessage.objects.create(
            session=session, text='Histórico', sender_type='agent', direction='outbound',
            external_message_id='ww:primary:stale-external-id',
            metadata={'gateway_message_id': 'stale-external-id', 'origin': 'crm'},
        )
        message = ChatMessage.objects.create(
            session=session, text='Respuesta nueva', sender_type='agent', direction='outbound',
        )
        gateway.side_effect = [
            {'external_message_id': 'stale-external-id', 'status': 'sent'},
            {'external_message_id': 'fresh-external-id', 'status': 'sent'},
        ]

        result = send_message(message, {})

        self.assertEqual(result['external_message_id'], 'ww:primary:fresh-external-id')
        self.assertEqual(gateway.call_count, 2)
        first_client_id = gateway.call_args_list[0].args[1]['client_message_id']
        second_client_id = gateway.call_args_list[1].args[1]['client_message_id']
        self.assertNotEqual(first_client_id, second_client_id)
        message.refresh_from_db()
        self.assertEqual(message.client_message_id, second_client_id)
