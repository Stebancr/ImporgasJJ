"""Inbox contract exercised in an isolated database, never live conversations."""
from datetime import timedelta
from unittest.mock import patch
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid

from django.db import connection, close_old_connections
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from usuarios.models import Credenciales
from .models import AssignmentQueue, ChannelIntegration, ChatMessage, ChatSession
from .realtime import publish_crm_event
from .tasks import generate_omnichannel_bot_reply, recover_stalled_chat_tasks


class SessionFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Credenciales.objects.create(usuario='filter-qa-admin', tipo_usuario=4, estado=1)
        self.customer = Credenciales.objects.create(usuario='filter-qa-customer', tipo_usuario=2, estado=1)
        self.client.force_authenticate(self.admin)
        self.queue = AssignmentQueue.objects.create(name='QA filter queue')
        self.sessions = {}
        for channel, _ in ChannelIntegration.CHANNEL_CHOICES:
            session = ChatSession.objects.create(channel=channel, user_name='QA '+channel, status='waiting',
                queue=self.queue, priority='high', unread_by_agent=2, last_customer_message_at=timezone.now())
            ChatMessage.objects.create(session=session, text='QA '+channel, sender_type='user', direction='inbound')
            self.sessions[channel] = session
        self.url = reverse('crm-session-list')
        self.count_url = reverse('crm-pending-count')

    def test_each_channel_and_all_match_api_and_counters_without_writes(self):
        before = list(ChatSession.objects.order_by('pk').values())
        for channel in ['all', *self.sessions]:
            with self.subTest(channel=channel):
                response = self.client.get(self.url, {'channel': channel})
                expected = 5 if channel == 'all' else 1
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data), expected)
                self.assertEqual({s['channel'] for s in response.data}, set(self.sessions) if channel == 'all' else {channel})
                counts = self.client.get(self.count_url, {'channel': channel})
                self.assertEqual(counts.data, {'total': expected, 'count': expected, 'unread': 2*expected})
                print('FILTER channel=%s expected=%s obtained=%s channels=%s PASS' %
                      (channel, expected, len(response.data), sorted({s['channel'] for s in response.data})))
        self.assertEqual(before, list(ChatSession.objects.order_by('pk').values()))

    def test_combined_filters_and_empty_result(self):
        params = {'channel': 'instagram', 'status': 'waiting', 'search': 'QA insta',
                  'priority': 'high', 'queue': self.queue.pk, 'unanswered': 'true'}
        self.assertEqual([s['id'] for s in self.client.get(self.url, params).data], [self.sessions['instagram'].pk])
        self.assertEqual(self.client.get(self.count_url, params).data, {'total': 1, 'count': 1, 'unread': 2})
        for patch_value in ({'search': 'does-not-exist'}, {'status': 'closed'}, {'priority': 'low'}, {'queue': self.queue.pk+100}):
            self.assertEqual(self.client.get(self.url, {**params, **patch_value}).data, [])
            self.assertEqual(self.client.get(self.count_url, {**params, **patch_value}).data, {'total': 0, 'count': 0, 'unread': 0})
        ChatSession.objects.filter(pk=self.sessions['instagram'].pk).update(last_agent_message_at=timezone.now())
        self.assertEqual(self.client.get(self.url, params).data, [])

    def test_invalid_filters_controlled_for_list_and_counts(self):
        for params in ({'channel': 'WhatsApp'}, {'channel': 'whatsapp-web'}, {'status': 'invalid'},
                       {'priority': 'invalid'}, {'queue': 'abc'}, {'queue': '-1'}, {'unanswered': 'invalid'}):
            for url in (self.url, self.count_url):
                self.assertEqual(self.client.get(url, params).status_code, 400)

    def test_permissions(self):
        self.client.force_authenticate(self.customer)
        for url in (self.url, self.count_url):
            self.assertEqual(self.client.get(url, {'channel': 'facebook'}).status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_single_query_and_deterministic_last_activity(self):
        instagram = self.sessions['instagram']
        ChatMessage.objects.create(session=instagram, text='Old external activity', external_timestamp=timezone.now()-timedelta(days=1))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url)
        self.assertEqual(len(queries), 1)
        self.assertEqual(next(s for s in response.data if s['channel'] == 'instagram')['last_message'], 'QA instagram')
        self.assertEqual([s['id'] for s in response.data], sorted([s.pk for s in self.sessions.values()], reverse=True))

    @patch('crmChat.views.publish_crm_event')
    def test_read_close_take_priority_queue_publish_and_counts(self, event):
        session = self.sessions['facebook']
        with self.captureOnCommitCallbacks(execute=True):
            messages = self.client.get(reverse('crm-messages', kwargs={'pk': session.pk}))
        self.assertEqual({m['text'] for m in messages.data['messages']}, {'QA facebook'})
        self.assertEqual(self.client.get(self.count_url, {'channel': 'facebook'}).data['unread'], 0)
        event.assert_called_with('session.read', session_id=session.pk)
        detail = reverse('crm-session-detail', kwargs={'pk': session.pk})
        for values in ({'take': True}, {'priority': 'urgent'}, {'queue_id': self.queue.pk}, {'status': 'closed'}):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.client.patch(detail, values, format='json').status_code, 200)
            event.assert_called_with('session.updated', session_id=session.pk)
        self.assertEqual(self.client.get(self.count_url, {'channel': 'facebook'}).data['count'], 0)
        self.assertEqual(self.client.get(self.url, {'channel': 'facebook', 'status': 'waiting'}).data, [])

    def test_deleted_or_closed_session_is_controlled(self):
        missing = reverse('crm-messages', kwargs={'pk': 999999})
        self.assertEqual(self.client.get(missing).status_code, 404)
        session = self.sessions['facebook']
        ChatSession.objects.filter(pk=session.pk).update(status='closed')
        response = self.client.post(reverse('crm-messages', kwargs={'pk': session.pk}), {'text': 'QA'}, format='json')
        self.assertEqual(response.status_code, 400)


class BrokerFailureTests(TestCase):
    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay', side_effect=ConnectionError('private broker address'))
    def test_broker_outage_preserves_request_and_recovers(self, enqueue):
        client = APIClient()
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(reverse('bot-chat'), {'message': 'Hola QA'}, format='json')
        self.assertEqual(response.status_code, 202)
        inbound = ChatMessage.objects.get(pk=response.data['user_message_id'])
        self.assertEqual(inbound.status, 'queued')
        self.assertNotIn('private', inbound.metadata['error'])
        self.assertFalse(inbound.session.messages.filter(sender_type='bot').exists())
        ChatMessage.objects.filter(pk=inbound.pk).update(created_at=timezone.now()-timedelta(minutes=4))
        with patch('crmChat.tasks.generate_omnichannel_bot_reply.delay') as restored:
            self.assertEqual(recover_stalled_chat_tasks.run()['recovered'], 1)
            restored.assert_called_once_with(inbound.pk)

    @patch('crmChat.realtime.get_channel_layer')
    def test_redis_realtime_outage_does_not_fail_committed_operation(self, layer):
        layer.return_value.group_send.side_effect = ConnectionError('private address')
        with self.assertLogs('crmChat.realtime', level='WARNING') as logs:
            publish_crm_event('session.updated', session_id=123)
        self.assertNotIn('private address', ''.join(logs.output))
        self.assertIn('ConnectionError', ''.join(logs.output))


class EcommerceInboxEventsTests(TestCase):
    @patch('crmChat.views.publish_crm_event')
    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay')
    def test_bot_requests_are_idempotent_notify_once_and_keep_unread(self, enqueue, event):
        client = APIClient()
        payload = {'message': 'Hola QA', 'client_message_id': str(uuid.uuid4())}
        with self.captureOnCommitCallbacks(execute=True):
            first = client.post(reverse('bot-chat'), payload, format='json')
            duplicate = client.post(reverse('bot-chat'), payload, format='json')
        self.assertEqual(first.status_code, 202)
        self.assertEqual(duplicate.data['user_message_id'], first.data['user_message_id'])
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 1)
        session = ChatSession.objects.get()
        self.assertEqual(session.unread_by_agent, 1)
        enqueue.assert_called_once()
        event.assert_called_once_with('message.created', session_id=session.pk, message_id=first.data['user_message_id'])
        stranger = APIClient()
        self.assertEqual(stranger.post(reverse('bot-chat'), payload, format='json').status_code, 403)
        invalid = client.post(reverse('bot-chat'), {'message': 'QA', 'client_message_id': 'invalid'}, format='json')
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(ChatMessage.objects.count(), 1)

    @patch('crmChat.views.publish_crm_event')
    def test_post_handoff_customer_message_updates_unanswered_once(self, event):
        customer = Credenciales.objects.create(usuario='qa-handoff-customer', tipo_usuario=2, estado=1)
        admin = Credenciales.objects.create(usuario='qa-handoff-admin', tipo_usuario=4, estado=1)
        client = APIClient()
        client.force_authenticate(customer)
        session = ChatSession.objects.create(channel='ecommerce', user_id_ref=customer.pk, status='active',
            last_agent_message_at=timezone.now(), last_customer_message_at=timezone.now()-timedelta(minutes=1))
        payload = {'text': 'Seguimiento QA', 'client_message_id': str(uuid.uuid4())}
        with self.captureOnCommitCallbacks(execute=True):
            first = client.post(reverse('crm-messages', kwargs={'pk':session.pk}), payload, format='json')
            duplicate = client.post(reverse('crm-messages', kwargs={'pk':session.pk}), payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(ChatMessage.objects.count(), 1)
        session.refresh_from_db()
        self.assertEqual(session.unread_by_agent, 1)
        client.force_authenticate(admin)
        response = client.get(reverse('crm-session-list'), {'channel':'ecommerce', 'unanswered':'true'})
        self.assertEqual([row['id'] for row in response.data], [session.pk])
        event.assert_called_once()


@skipUnless(connection.vendor == 'postgresql', 'Docker PostgreSQL row-lock test')
class CrossChannelMemoryTests(TransactionTestCase):
    @patch('crmChat.tasks.dispatch_outbound_message')
    @patch('crmChat.tasks.ollama_service.get_bot_response')
    def test_facebook_and_instagram_parallel_memories_never_mix(self, provider, transport):
        barrier = Barrier(2)
        messages, calls = [], {}
        for channel in ('facebook', 'instagram'):
            integration = ChannelIntegration.objects.create(name='QA '+channel, channel=channel, active=True, configuration={'bot_enabled': True})
            session = ChatSession.objects.create(channel=channel, integration=integration,
                conversation_state={'owner': channel}, conversation_summary='Private '+channel)
            ChatMessage.objects.create(session=session, sender_type='bot', direction='outbound', text='Context '+channel)
            messages.append(ChatMessage.objects.create(session=session, sender_type='user', direction='inbound',
                text='Question '+channel, external_message_id='qa-'+channel, status='queued'))
        def respond(text, **kwargs):
            calls[kwargs['channel']] = kwargs
            barrier.wait(timeout=5)
            return {'response': 'QA response', 'state': kwargs['conversation_state'], 'summary': kwargs['summary']}
        provider.side_effect = respond
        def run(pk):
            close_old_connections()
            try:
                return generate_omnichannel_bot_reply.run(pk)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(run, [message.pk for message in messages]))
        for channel, other in [('facebook', 'instagram'), ('instagram', 'facebook')]:
            self.assertEqual(calls[channel]['conversation_state']['owner'], channel)
            self.assertEqual(calls[channel]['summary'], 'Private '+channel)
            self.assertIn('Context '+channel, [item['content'] for item in calls[channel]['conversation_history']])
            self.assertNotIn('Context '+other, [item['content'] for item in calls[channel]['conversation_history']])
