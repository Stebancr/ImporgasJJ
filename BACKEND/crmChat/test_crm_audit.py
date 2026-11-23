"""Synthetic contract, network safety and bounded-history regressions."""
import socket
import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from usuarios.models import Credenciales
from .models import ChannelIntegration, ChatMessage, ChatSession
from .apps.meta.services import MetaAPIError, dispatch_outbound_message, graph_request, send_read_receipt
from .transport_safety import assert_provider_io_allowed


class CRMAuditTests(APITestCase):
    def setUp(self):
        self.agent = Credenciales.objects.create(usuario='audit-agent', estado=1, tipo_usuario=1)
        self.client.force_authenticate(self.agent)
        self.session = ChatSession.objects.create(channel='ecommerce', status='active')

    def messages_url(self, session=None):
        return f'/crm-chat/sessions/{(session or self.session).pk}/messages/'

    def external(self, channel):
        integration = ChannelIntegration.objects.create(name='Synthetic audit', channel=channel, active=True)
        session = ChatSession.objects.create(channel=channel, integration=integration, status='active',
            external_thread_id='synthetic-destination', last_customer_message_at=timezone.now())
        ChatMessage.objects.create(session=session, text='Consulta sintética', sender_type='user',
            direction='inbound', external_message_id=f'inbound:{channel}')
        return session

    @override_settings(CRM_TEST_MODE=True, CRM_EXTERNAL_SEND_ENABLED=True)
    @patch('requests.sessions.Session.request', side_effect=AssertionError('REAL HTTP FORBIDDEN'))
    def test_simulation_all_external_channels_is_idempotent_and_not_connected(self, http):
        for channel in ('whatsapp', 'whatsapp_web', 'facebook', 'instagram'):
            with self.subTest(channel=channel):
                session = self.external(channel)
                response = self.client.post(self.messages_url(session), {
                    'text': 'Respuesta de desarrollo 😃\nhttps://example.invalid',
                    'client_message_id': str(uuid.uuid4()),
                })
                self.assertEqual(response.status_code, 201, response.data)
                self.assertTrue(response.data['simulated'])
                message = ChatMessage.objects.get(pk=response.data['id'])
                external_id = message.external_message_id
                dispatch_outbound_message(message)
                self.assertEqual(message.external_message_id, external_id)
                self.assertTrue(external_id.startswith('crm-simulated:'))
                session.integration.refresh_from_db()
                self.assertEqual(session.integration.connection_status, 'pending')
                self.assertEqual(send_read_receipt(message), {'simulated': True})
        http.assert_not_called()

    @override_settings(CRM_TEST_MODE=False, CRM_EXTERNAL_SEND_ENABLED=False)
    @patch('requests.sessions.Session.request')
    def test_disabled_send_fails_without_network_and_keeps_message(self, http):
        session = self.external('facebook')
        response = self.client.post(self.messages_url(session), {'text': 'Solo prueba'})
        self.assertEqual(response.status_code, 502)
        message = session.messages.get(sender_type='agent')
        self.assertEqual(message.status, 'failed')
        self.assertFalse(message.metadata['delivery_uncertain'])
        http.assert_not_called()

    def test_switch_truth_table(self):
        for enabled, test_mode, allowed in ((False, False, False), (False, True, False),
                                          (True, True, False), (True, False, True)):
            with self.subTest(enabled=enabled, test_mode=test_mode), override_settings(
                    CRM_EXTERNAL_SEND_ENABLED=enabled, CRM_TEST_MODE=test_mode):
                if allowed:
                    assert_provider_io_allowed()
                else:
                    with self.assertRaisesMessage(MetaAPIError, 'CRM_EXTERNAL_IO_DISABLED'):
                        assert_provider_io_allowed()

    @override_settings(CRM_TEST_MODE=True, CRM_EXTERNAL_SEND_ENABLED=True)
    @patch('requests.sessions.Session.request')
    def test_direct_provider_boundaries_are_blocked_even_if_send_enabled(self, http):
        from .apps.meta.oauth import _request
        from .apps.whatsapp.coexistence import exchange_signup_code
        from .apps.instagram.services import exchange_authorization_code
        from .apps.whatsapp_web.services import gateway_request
        from .apps.meta.services import validate_whatsapp_token_permissions
        from .tasks import _open_public_stream
        for operation in (
            lambda: graph_request(Mock(), 'POST', '/messages'),
            lambda: _request('GET', 'https://graph.facebook.com/test'),
            lambda: exchange_signup_code('synthetic-code'),
            lambda: exchange_authorization_code(Mock(), 'synthetic-code'),
            lambda: gateway_request('/internal/whatsapp/send/', {}),
            lambda: validate_whatsapp_token_permissions(Mock()),
            lambda: _open_public_stream('https://fbcdn.net/a.png', {}),
        ):
            with self.assertRaisesMessage(MetaAPIError, 'CRM_EXTERNAL_IO_DISABLED'):
                operation()
        http.assert_not_called()

    def test_message_pages_are_bounded_complete_and_handle_out_of_order_events(self):
        rows = ChatMessage.objects.bulk_create([
            ChatMessage(session=self.session, text=f'History {i}', sender_type='user') for i in range(250)])
        # A high ID can have an old provider timestamp. Cursor must follow timeline, not ID alone.
        ChatMessage.objects.filter(pk=rows[-1].pk).update(external_timestamp=timezone.now()-timedelta(days=1))
        found = []
        before = None
        for expected in (100, 100, 50):
            response = self.client.get(self.messages_url(), {'before': before} if before else {})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['messages']), expected)
            found.extend(m['id'] for m in response.data['messages'])
            before = response.data['before']
        self.assertFalse(response.data['has_more'])
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(set(found), {r.pk for r in rows})

    def test_foreign_or_invalid_cursor_is_rejected(self):
        other = ChatSession.objects.create()
        message = ChatMessage.objects.create(session=other, text='Private')
        for params in ({'before': message.pk}, {'before': 'bad'}, {'limit': 'bad'}):
            self.assertEqual(self.client.get(self.messages_url(), params).status_code, 400)

    def test_session_pages_reach_conversations_beyond_first_hundred(self):
        ChatSession.objects.bulk_create([ChatSession(user_name=f'Synthetic {i}') for i in range(250)])
        found = []
        for offset, expected in ((0, 100), (100, 100), (200, 51)):
            response = self.client.get('/crm-chat/sessions/', {'offset': offset})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), expected)
            found.extend(item['id'] for item in response.data)
        self.assertEqual(len(found), len(set(found)))
        for offset in ('bad', -1):
            self.assertEqual(self.client.get('/crm-chat/sessions/', {'offset': offset}).status_code, 400)

    def test_history_query_count_does_not_grow_with_page_size(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        ChatMessage.objects.bulk_create([ChatMessage(session=self.session, text=str(i)) for i in range(100)])
        counts = []
        for limit in (5, 100):
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(self.messages_url(), {'limit': limit})
                self.assertEqual(response.status_code, 200)
            counts.append(len(queries))
        self.assertEqual(counts[0], counts[1])

    @patch('crmChat.apps.meta.services.secret_store.decrypt', return_value='synthetic-access-token')
    @patch('crmChat.apps.meta.services.requests.request')
    def test_invalid_provider_json_is_controlled_and_does_not_expose_body(self, request, decrypt):
        integration = Mock(access_token_encrypted='encrypted', graph_api_version='v1')
        response = Mock(content=b'private provider response')
        request.return_value = response
        response.json.side_effect = ValueError('private provider response')
        with self.assertRaisesMessage(MetaAPIError, 'Meta devolvió una respuesta inválida.') as error:
            graph_request(integration, 'POST', '/messages')
        self.assertEqual(error.exception.phase, 'delivery_confirmation')

    def test_audit_runner_blocks_external_socket(self):
        from django.conf import settings
        if settings.TEST_RUNNER != 'crmChat.audit_runner.AuditRunner':
            self.skipTest('Explicit isolated audit runner required')
        with socket.socket() as connection:
            with self.assertRaisesMessage(AssertionError, 'CRM_AUDIT_EXTERNAL_NETWORK_BLOCKED'):
                connection.connect(('203.0.113.1', 443))

    @override_settings(CRM_ASYNC_OUTBOUND_ENABLED=True, CRM_TEST_MODE=True)
    @patch('crmChat.tasks.send_outbound_message.apply_async')
    @patch('crmChat.views.dispatch_outbound_message')
    def test_http_send_queues_after_commit_without_waiting_for_provider(self, dispatch, queue):
        session = self.external('facebook')
        body = {'text': 'Synthetic async', 'client_message_id': str(uuid.uuid4())}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.messages_url(session), body)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['status'], 'queued')
            queue.assert_not_called()
        queue.assert_called_once()
        response = self.client.post(self.messages_url(session), body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(session.messages.filter(sender_type='agent').count(), 1)
        queue.assert_called_once()
        dispatch.assert_not_called()

    @override_settings(CRM_ASYNC_OUTBOUND_ENABLED=True, CRM_TEST_MODE=True)
    @patch('crmChat.tasks.send_outbound_message.apply_async', side_effect=OSError('broker unavailable'))
    def test_broker_failure_preserves_retryable_message(self, queue):
        session = self.external('instagram')
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.messages_url(session), {'text': 'Keep me'})
        message = ChatMessage.objects.get(pk=response.data['id'])
        self.assertEqual(message.text, 'Keep me')
        self.assertEqual(message.status, 'failed')
        self.assertEqual(message.metadata['error_code'], 'queue_unavailable')
        queue.side_effect = None
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'{self.messages_url(session)}{message.pk}/retry/')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(session.messages.filter(sender_type='agent').count(), 1)

    @override_settings(CRM_TEST_MODE=True)
    def test_worker_repeated_task_is_idempotent(self):
        from .tasks import send_outbound_message
        session = self.external('whatsapp_web')
        message = ChatMessage.objects.create(session=session, text='Worker test',
            sender_type='agent', direction='outbound', status='queued')
        first = send_outbound_message.run(message.pk)
        second = send_outbound_message.run(message.pk)
        self.assertEqual(first, second)
        self.assertTrue(first['simulated'])
        self.assertEqual(session.messages.filter(sender_type='agent').count(), 1)

    @override_settings(CRM_ASYNC_OUTBOUND_ENABLED=True)
    @patch('crmChat.tasks.enqueue_outbound')
    def test_stranded_queued_messages_recover_with_bounded_attempts(self, queue):
        from .tasks import recover_stalled_chat_tasks, send_outbound_message
        message = ChatMessage.objects.create(session=self.session, text='Keep queued',
            sender_type='agent', direction='outbound', status='queued')
        ChatMessage.objects.filter(pk=message.pk).update(created_at=timezone.now()-timedelta(minutes=5))
        for _ in range(2):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(recover_stalled_chat_tasks.run()['recovered'], 1)
        self.assertEqual(queue.call_count, 2)
        self.assertEqual(recover_stalled_chat_tasks.run()['recovered'], 0)
        message.refresh_from_db()
        self.assertEqual(message.status, 'failed')
        self.assertEqual(send_outbound_message.run(message.pk)['skipped'], 'not_queued')
