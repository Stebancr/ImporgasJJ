import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
from unittest import skipUnless

import requests
from django.db import connection, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from ecommerce.models import Location
from .models import ChatSession, ChatMessage, ChannelIntegration, BotConversationLease
from .ollama_service import ollama_service
from .tasks import generate_omnichannel_bot_reply, close_inactive_bot_sessions, recover_stalled_chat_tasks


@override_settings(CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=False)
class SimplifiedResponseTests(TestCase):
    def test_commercial_variations_never_query_catalog_or_ollama(self):
        phrases = ['Quiero comprar un calentador', 'Necesito un regulador', '¿Cuánto cuesta?',
                   'Quiero cotizar', 'Me interesa ese producto', '¿Cómo puedo comprarlo?',
                   'Necesito un repuesto', 'Quiero hacer el pedido', '¿Tienen disponible?',
                   'Quiero hablar con un vendedor', 'Quisiera reservar un servicio',
                   'Necesito una válvula', 'Busco una manguera', 'Quiero accesorios',
                   'Necesito una visita técnica', 'Quiero instalarlo', '¿Es compatible?',
                   '¿Qué garantía tiene?', 'Hola, ¿cuál me recomiendas?']
        with patch('crmChat.ollama_service._http_session') as http:
            for phrase in phrases:
                with self.subTest(phrase=phrase), self.assertNumQueries(0):
                    result = ollama_service.get_bot_response(phrase, conversation_state={'product': 'PRIVADO ZX', 'recent_products': [{'id': 42}]})
                    self.assertTrue(result['needs_agent'])
                    self.assertNotRegex(result['response'], r'PRIVADO|https?://|\$|duchas|baños|tipo de gas')
                    self.assertEqual(result['state']['recent_products'], [{'id': 42}])
            http.assert_not_called()

    def test_greeting_and_ecommerce_do_not_repeat(self):
        first = ollama_service.get_bot_response('Hola', channel='facebook')
        self.assertEqual(first['response'], ollama_service.INITIAL_GREETING)
        second = ollama_service.get_bot_response('Hola', conversation_state=first['state'], channel='facebook')
        self.assertNotIn(ollama_service.INITIAL_GREETING, second['response'])
        self.assertNotIn(ollama_service.INITIAL_GREETING, ollama_service.get_bot_response('Hola')['response'])

    def test_institutional_uses_only_existing_locations(self):
        Location.objects.create(name='Sede QA', city='Ciudad QA', address='Dirección QA', phone='0000000000', hours_weekday='08:00–17:00')
        with CaptureQueriesContext(connection) as queries:
            result = ollama_service.get_bot_response('¿Qué horarios manejan?')
        self.assertIn('08:00–17:00', result['response'])
        self.assertFalse(result['needs_agent'])
        self.assertTrue(all('locations' in query['sql'] for query in queries))

    def test_missing_verified_information_transfers(self):
        self.assertTrue(ollama_service.get_bot_response('¿Dónde quedan?')['needs_agent'])

    def test_context_reference_transfers_without_catalog(self):
        result = ollama_service.get_bot_response('Me interesa ese', conversation_history=[{'role': 'assistant', 'content': 'Producto histórico privado'}])
        self.assertTrue(result['needs_agent'])
        self.assertNotIn('histórico', result['response'])

    @patch('crmChat.ollama_service._http_session')
    def test_ambiguous_intent_uses_context_but_never_generated_answer(self, http):
        response = http.return_value.post.return_value
        response.json.return_value = {'message': {'content': '{"intent":"commercial"}'}}
        result = ollama_service.get_bot_response('el de antes', conversation_history=[{'role': 'user', 'content': 'Necesidad anterior'}])
        self.assertTrue(result['needs_agent'])
        self.assertIn('Necesidad anterior', http.return_value.post.call_args.kwargs['json']['messages'][1]['content'])
        self.assertEqual(http.return_value.post.call_args.kwargs['timeout'], (3, 8))
        response.json.return_value = {'message': {'content': 'Producto inventado $100 https://mal.example'}}
        result = ollama_service.get_bot_response('otra cosa ambigua')
        self.assertTrue(result['needs_agent'])
        self.assertNotIn('inventado', result['response'])

    @patch('crmChat.ollama_service._http_session')
    def test_timeout_and_provider_error_handoff(self, http):
        for error in (requests.Timeout(), requests.ConnectionError()):
            http.return_value.post.side_effect = error
            result = ollama_service.get_bot_response('algo ambiguo')
            self.assertTrue(result['needs_agent'])
            self.assertIsNone(result['error'])

    def test_flag_reactivates_unchanged_recommendation_implementation(self):
        with override_settings(CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=True), patch.object(ollama_service, '_get_recommendation_response', return_value={'legacy': True}) as legacy:
            self.assertEqual(ollama_service.get_bot_response('Necesito un calentador'), {'legacy': True})
            legacy.assert_called_once()


@override_settings(CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=False)
class SimplifiedTaskTests(TestCase):
    def message(self, channel='ecommerce', text='Quiero comprar', **kwargs):
        integration = None
        if channel != 'ecommerce':
            integration = ChannelIntegration.objects.create(channel=channel, name='QA', active=True, configuration={'bot_enabled': True})
        session = ChatSession.objects.create(channel=channel, integration=integration, status='bot', last_customer_message_at=timezone.now())
        return ChatMessage.objects.create(session=session, text=text, direction='inbound', sender_type='user', status='queued', external_message_id='qa-'+str(uuid.uuid4()), **kwargs)

    @patch('crmChat.tasks.dispatch_outbound_message')
    @patch('crmChat.tasks.publish_crm_event')
    @patch('crmChat.assignment.assign_session_automatically')
    def test_all_channels_transfer_once_and_keep_customer_message(self, assign, event, send):
        for channel in ('ecommerce', 'facebook', 'instagram', 'whatsapp_web'):
            inbound = self.message(channel)
            result = generate_omnichannel_bot_reply.run(inbound.pk)
            reply = ChatMessage.objects.get(pk=result['message_id'])
            inbound.session.refresh_from_db()
            self.assertEqual(inbound.session.status, 'waiting')
            self.assertEqual(reply.text.count(ollama_service.INITIAL_GREETING), int(channel != 'ecommerce'))
            self.assertTrue(inbound.session.messages.filter(pk=inbound.pk).exists())
            self.assertEqual(generate_omnichannel_bot_reply.run(inbound.pk), {'duplicate': True})
            later = ChatMessage.objects.create(session=inbound.session, text='¿Me atienden?', direction='inbound', sender_type='user', status='queued', external_message_id='later-'+channel)
            self.assertIn('skipped', generate_omnichannel_bot_reply.run(later.pk))
        self.assertEqual(send.call_count, 4)
        self.assertEqual(assign.call_count, 4)
        self.assertEqual(sum(call.args[0] == 'session.pending' for call in event.call_args_list), 4)
        self.assertFalse(BotConversationLease.objects.exists())

    @patch('crmChat.tasks.dispatch_outbound_message', side_effect=RuntimeError('channel unavailable'))
    @patch('crmChat.assignment.assign_session_automatically')
    def test_channel_failure_does_not_cancel_transfer_or_duplicate(self, assign, send):
        inbound = self.message()
        with self.assertRaises(RuntimeError):
            generate_omnichannel_bot_reply.run(inbound.pk)
        inbound.session.refresh_from_db()
        self.assertEqual(inbound.session.status, 'waiting')
        assign.assert_called_once()
        self.assertFalse(BotConversationLease.objects.exists())
        generate_omnichannel_bot_reply.run(inbound.pk)
        self.assertEqual(send.call_count, 1)

    @patch('crmChat.tasks.dispatch_outbound_message')
    def test_agent_and_linked_phone_messages_do_not_trigger_bot(self, send):
        for origin in ('crm', 'whatsapp_app'):
            inbound = self.message()
            inbound.sender_type = 'agent'; inbound.direction = 'outbound'
            inbound.metadata = {'origin': origin}; inbound.save()
            self.assertEqual(generate_omnichannel_bot_reply.run(inbound.pk), {'skipped': 'not_a_customer_message'})
        send.assert_not_called()

    @patch('crmChat.tasks.dispatch_outbound_message')
    def test_waiting_for_advisor_never_sends_inactivity_warning_or_closes(self, send):
        inbound = self.message()
        generate_omnichannel_bot_reply.run(inbound.pk)
        ChatSession.objects.filter(pk=inbound.session_id).update(last_bot_message_at=timezone.now()-timedelta(minutes=10))
        close_inactive_bot_sessions.run()
        inbound.session.refresh_from_db()
        self.assertEqual(inbound.session.status, 'waiting')
        self.assertEqual(send.call_count, 1)

    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay')
    def test_abandoned_worker_job_recovers_then_transfers_once(self, enqueue):
        inbound = self.message()
        ChatMessage.objects.filter(pk=inbound.pk).update(status='processing', created_at=timezone.now()-timedelta(minutes=4))
        self.assertEqual(recover_stalled_chat_tasks.run()['recovered'], 1)
        enqueue.assert_called_once_with(inbound.pk)
        with patch('crmChat.tasks.dispatch_outbound_message') as send:
            generate_omnichannel_bot_reply.run(inbound.pk)
            generate_omnichannel_bot_reply.run(inbound.pk)
            send.assert_called_once()


@skipUnless(connection.vendor == 'postgresql', 'Requires Docker PostgreSQL row locks')
@override_settings(CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=False)
class SimplifiedConcurrencyTests(TransactionTestCase):
    def test_eight_sessions_preserve_order_and_single_transfer(self):
        sessions = [ChatSession.objects.create(status='bot', conversation_state={'qa_owner': index}) for index in range(8)]
        messages = [ChatMessage.objects.create(session=session, text='Quiero comprar', sender_type='user', direction='inbound', status='queued') for session in sessions]
        later = [ChatMessage.objects.create(session=session, text='Necesito un repuesto', sender_type='user', direction='inbound', status='queued') for session in sessions]
        def run(message):
            close_old_connections()
            start = time.perf_counter()
            try:
                generate_omnichannel_bot_reply.run(message.pk)
                return time.perf_counter() - start
            finally:
                close_old_connections()
        with patch('crmChat.tasks.dispatch_outbound_message') as send, ThreadPoolExecutor(max_workers=8) as pool:
            durations = list(pool.map(run, messages))
            list(pool.map(run, later))
            self.assertEqual(send.call_count, 8)
        for index, session in enumerate(sessions):
            session.refresh_from_db()
            self.assertEqual(session.conversation_state['qa_owner'], index)
            self.assertEqual(session.status, 'waiting')
            self.assertEqual(session.messages.filter(sender_type='bot').count(), 1)
        self.assertFalse(BotConversationLease.objects.exists())
        self.assertFalse(ChatMessage.objects.filter(status__in=('queued', 'processing'), direction='inbound').exists())
        print('SIMPLIFIED_BENCHMARK sessions=8 average=%.4fs max=%.4fs pending_inbound=0 duplicates=0' % (sum(durations)/len(durations), max(durations)))
