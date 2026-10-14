"""Regression tests use isolated PostgreSQL and mocked channel transports only."""
import tempfile
import uuid
import subprocess
import wave
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
from threading import Barrier, Event
from unittest.mock import patch
from unittest import skipUnless

from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections, connection
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from pypdf import PdfWriter
from rest_framework.test import APITestCase, APIClient

from usuarios.models import Credenciales
from .attachment_validation import validate_chat_upload
from .bot_concurrency import ConversationBusy, conversation_lease
from .models import (BotConversationLease, ChannelIntegration, ChatAttachment, ChatAuditEvent,
                     ChatMessage, ChatSession, QuickReply, QuickReplyPreference)
from .tasks import generate_omnichannel_bot_reply, recover_stalled_chat_tasks
from .apps.meta.services import MetaAPIError
from .ollama_service import ollama_service


def image():
    data = BytesIO()
    Image.new('RGB', (4, 4), 'red').save(data, format='PNG')
    return SimpleUploadedFile('imagen.png', data.getvalue(), content_type='image/png')


def pdf():
    data = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(200, 200)
    writer.write(data)
    return SimpleUploadedFile('informe.pdf', data.getvalue(), content_type='application/pdf')


@skipUnless(connection.vendor == 'postgresql', 'Run with CRM_TEST_POSTGRES=1 to verify database row locks.')
class ConversationConcurrencyTests(TransactionTestCase):
    def message(self, session, text):
        return ChatMessage.objects.create(session=session, text=text, sender_type='user', direction='inbound', status='queued')

    def run_task(self, message_id):
        close_old_connections()
        try:
            return generate_omnichannel_bot_reply.run(message_id)
        finally:
            connections.close_all()

    @patch('crmChat.tasks.ollama_service.get_bot_response')
    def test_two_sessions_run_in_parallel_and_keep_context_and_order(self, provider):
        first = ChatSession.objects.create(status='bot', conversation_state={'owner': 'A'})
        other = ChatSession.objects.create(status='bot', conversation_state={'owner': 'B'})
        a1, a2 = self.message(first, 'A1'), self.message(first, 'A2')
        b1 = self.message(other, 'B1')
        barrier = Barrier(2)
        calls = {}
        def respond(text, **kwargs):
            calls[text] = kwargs
            if text in ('A1', 'B1'):
                barrier.wait(timeout=5)  # A global lock would fail this test.
            return {'response': 'Respuesta ' + text, 'state': kwargs['conversation_state'], 'summary': text}
        provider.side_effect = respond
        with self.assertRaises(ConversationBusy):
            self.run_task(a2.pk)
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.run_task, m.pk) for m in (a1, b1)]
            for future in futures:
                self.assertIn('message_id', future.result(timeout=8))
        self.run_task(a2.pk)
        self.assertEqual(calls['A2']['conversation_state']['owner'], 'A')
        self.assertEqual(calls['B1']['conversation_state']['owner'], 'B')
        self.assertIn('Respuesta A1', [m['content'] for m in calls['A2']['conversation_history']])
        self.assertNotIn('B1', [m['content'] for m in calls['A2']['conversation_history']])
        self.assertNotIn('A2', [m['content'] for m in calls['A1']['conversation_history']])
        self.assertEqual(self.run_task(a1.pk), {'duplicate': True})
        self.assertEqual(ChatMessage.objects.filter(reply_to_message=a1).count(), 1)
        self.assertFalse(BotConversationLease.objects.exists())

    @patch('crmChat.tasks.ollama_service.get_bot_response')
    def test_same_session_lease_excludes_second_inference_and_releases_after_failure(self, provider):
        session = ChatSession.objects.create(status='bot')
        inbound = self.message(session, 'Consulta')
        with conversation_lease(session.pk):
            with self.assertRaises(ConversationBusy):
                self.run_task(inbound.pk)
        provider.return_value = {'error': 'timeout'}
        with self.assertRaises(RuntimeError):
            self.run_task(inbound.pk)
        inbound.refresh_from_db()
        self.assertEqual(inbound.status, 'failed')
        self.assertFalse(ChatMessage.objects.filter(reply_to_message=inbound).exists())
        self.assertFalse(BotConversationLease.objects.exists())
        provider.return_value = {'response': 'Recuperada', 'state': {}, 'summary': ''}
        self.run_task(inbound.pk)
        self.run_task(inbound.pk)
        self.assertEqual(ChatMessage.objects.filter(reply_to_message=inbound).count(), 1)

    @patch('crmChat.tasks.generate_omnichannel_bot_reply.delay')
    def test_hard_timeout_recovery_is_bounded_and_does_not_send(self, enqueue):
        session = ChatSession.objects.create(status='bot')
        inbound = self.message(session, 'Pendiente')
        ChatMessage.objects.filter(pk=inbound.pk).update(created_at=timezone.now()-timedelta(minutes=4), status='processing')
        BotConversationLease.objects.create(session=session, owner='dead', expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(recover_stalled_chat_tasks()['recovered'], 1)
        self.assertEqual(recover_stalled_chat_tasks()['recovered'], 1)
        self.assertEqual(recover_stalled_chat_tasks()['recovered'], 0)
        inbound.refresh_from_db()
        self.assertEqual(inbound.status, 'failed')
        self.assertEqual(enqueue.call_count, 2)
        self.assertFalse(ChatMessage.objects.filter(sender_type='bot').exists())


class ChatbotUpgradeAPITests(APITestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.temp.name, FRONTEND_PUBLIC_URL='https://crm.example.com')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.temp.cleanup)
        self.admin = Credenciales.objects.create(usuario='upgrade-admin', tipo_usuario=4, estado=1)
        self.agent = Credenciales.objects.create(usuario='upgrade-agent', tipo_usuario=1, estado=1)
        self.customer = Credenciales.objects.create(usuario='upgrade-customer', tipo_usuario=2, estado=1)
        self.client.force_authenticate(self.admin)
        self.session = ChatSession.objects.create(status='active', channel='ecommerce', user_name='Cliente de prueba')

    def external(self, channel):
        integration = ChannelIntegration.objects.create(name='Prueba', channel=channel, active=True,
            external_account_id='test-'+channel, configuration={'bot_enabled': True})
        session = ChatSession.objects.create(channel=channel, status='active', integration=integration,
            external_thread_id='test-recipient', last_customer_message_at=timezone.now())
        ChatMessage.objects.create(session=session, text='Mensaje sintético', sender_type='user', direction='inbound', external_message_id='in-'+channel)
        return session

    def send_file(self, session, upload, client_id=None, **extra):
        return self.client.post(reverse('crm-messages', kwargs={'pk': session.pk}),
            {'file': upload, 'client_message_id': client_id or str(uuid.uuid4()), **extra}, format='multipart')

    def test_template_crud_variables_favorites_and_edit_before_send(self):
        response = self.client.post('/crm-chat/templates/', {'name': 'Saludo', 'category': 'Ventas',
            'channels': ['ecommerce'], 'text': 'Hola {{nombre_cliente}}, soy {{nombre_agente}}.'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data['id']
        self.assertEqual(self.client.get('/crm-chat/templates/', {'search': 'Ventas'}).data[0]['id'], pk)
        preview = f'/crm-chat/templates/{pk}/preview/'
        self.assertEqual(self.client.post(preview, {'session_id': self.session.pk, 'variables': {}}, format='json').status_code, 400)
        values = {'nombre_cliente': 'Cliente', 'nombre_agente': 'Asesor'}
        rendered = self.client.post(preview, {'session_id': self.session.pk, 'variables': values}, format='json')
        self.assertEqual(rendered.data['text'], 'Hola Cliente, soy Asesor.')
        self.assertFalse(ChatMessage.objects.exists())  # Preview never sends.
        self.client.post(f'/crm-chat/templates/{pk}/favorite/')
        self.assertTrue(self.client.get('/crm-chat/templates/').data[0]['favorite'])
        message = self.client.post(reverse('crm-messages', kwargs={'pk': self.session.pk}),
            {'text': 'Hola Cliente, soy Asesor. ¿Cómo te ayudo?', 'template_id': pk, 'template_variables': values,
             'client_message_id': str(uuid.uuid4())}, format='json')
        self.assertEqual(message.status_code, 201, message.data)
        self.assertEqual(message.data['template_id'], pk)
        self.assertIsNotNone(QuickReplyPreference.objects.get(template_id=pk, user=self.admin).last_used_at)
        self.assertTrue(ChatAuditEvent.objects.filter(action='template.used').exists())
        self.assertEqual(self.client.patch(f'/crm-chat/templates/{pk}/', {'active': False}, format='json').status_code, 200)
        self.assertEqual(self.client.post(preview, {'session_id': self.session.pk, 'variables': values}, format='json').status_code, 400)
        self.client.force_authenticate(self.agent)
        self.assertEqual(self.client.post('/crm-chat/templates/', {'name': 'No permitido'}, format='json').status_code, 403)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/crm-chat/templates/').status_code, 403)

    def test_template_attachment_is_private_and_compatible(self):
        res = self.client.post('/crm-chat/templates/', {'name': 'Ficha', 'text': 'Documento',
            'channels': '["facebook"]', 'file': pdf()}, format='multipart')
        self.assertEqual(res.status_code, 201, res.data)
        url = res.data['attachment_url'].removeprefix('/api')
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        res = self.client.post('/crm-chat/templates/', {'name': 'No IG PDF', 'text': 'Archivo',
            'channels': '["instagram"]', 'file': pdf()}, format='multipart')
        self.assertEqual(res.status_code, 400)

    @patch('crmChat.apps.whatsapp_web.services.send_message')
    def test_whatsapp_files_confirmed_and_retry_idempotent(self, transport):
        session = self.external('whatsapp_web')
        transport.side_effect = [{'external_message_id': 'out-image'}, {'external_message_id': 'out-pdf'}]
        key = str(uuid.uuid4())
        first = self.send_file(session, image(), key)
        second = self.send_file(session, image(), key)
        document = self.send_file(session, pdf())
        self.assertEqual((first.status_code, second.status_code, document.status_code), (201, 200, 201))
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(ChatAttachment.objects.count(), 2)
        self.assertTrue(all(a.metadata['sha256'] for a in ChatAttachment.objects.all()))
        retry = self.client.post(f'/crm-chat/sessions/{session.pk}/messages/{first.data["id"]}/retry/')
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(transport.call_count, 2)
        self.assertTrue(transport.call_args.args[1]['url'].startswith('http://backend:8000/api/'))

    @patch('crmChat.apps.facebook.services.send_attachment')
    def test_facebook_document_maps_to_file_and_public_url(self, transport):
        transport.return_value = {'message_id': 'facebook-file-confirmed'}
        session = self.external('facebook')
        response = self.send_file(session, pdf())
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(transport.call_args.args[2], 'file')
        self.assertTrue(transport.call_args.args[3].startswith('https://crm.example.com/'))
        self.assertEqual(response.data['status'], 'sent')

    @patch('crmChat.apps.instagram.services.send_image')
    def test_instagram_image_confirmed_document_rejected_and_meta_error_persisted(self, transport):
        session = self.external('instagram')
        transport.return_value = {'message_id': 'instagram-image-confirmed'}
        response = self.send_file(session, image())
        self.assertEqual(response.status_code, 201, response.data)
        before = ChatMessage.objects.count()
        self.assertEqual(self.send_file(session, pdf()).status_code, 400)
        self.assertEqual(ChatMessage.objects.count(), before)
        transport.side_effect = MetaAPIError('Permiso de mensajería ausente', http_status=400, meta_code=3)
        failed = self.send_file(session, image())
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(failed.data['message']['status'], 'failed')
        session.integration.refresh_from_db()
        self.assertIn('Permiso', session.integration.last_error)

    def test_ecommerce_ownership_and_queue_not_synchronous(self):
        self.client.force_authenticate(None)
        with patch('crmChat.tasks.generate_omnichannel_bot_reply.delay') as enqueue, self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('bot-chat'), {'message': 'Hola'}, format='json')
        self.assertEqual(response.status_code, 202)
        enqueue.assert_called_once_with(response.data['user_message_id'])
        session = ChatSession.objects.get(pk=response.data['session_id'])
        url = reverse('bot-session-messages', kwargs={'session_id': session.pk})
        self.assertEqual(self.client.get(url).status_code, 200)
        stranger = APIClient()
        self.assertEqual(stranger.get(url).status_code, 403)
        self.assertEqual(stranger.post(reverse('bot-chat'), {'session_id': session.pk, 'message': 'No autorizado'}, format='json').status_code, 403)

    @override_settings(OLLAMA_ECOMMERCE_ENABLED=False)
    def test_disabled_ecommerce_bot_keeps_customer_session_access(self):
        self.client.force_authenticate(None)
        with patch('crmChat.tasks.generate_omnichannel_bot_reply.delay') as enqueue:
            response = self.client.post(reverse('bot-chat'), {'message': 'Necesito un asesor'}, format='json')
            session_id = response.data['session_id']
            self.assertEqual(response.status_code, 202)
            self.assertEqual(self.client.get(reverse('bot-session-messages', kwargs={'session_id': session_id})).status_code, 200)
            self.assertEqual(self.client.post(reverse('bot-chat'), {'session_id': session_id, 'message': 'Sigo esperando'}, format='json').status_code, 202)
            enqueue.assert_not_called()

    def test_heater_short_answers_fill_context_without_repeating(self):
        state = {'category': 'Calentadores', 'product': 'calentador', 'pending_question': {'key': 'use_case'}}
        state = ollama_service.update_state('baño', state)
        self.assertEqual(state['use_case'], 'hogar')
        state['pending_question'] = {'key': 'bathrooms'}
        state = ollama_service.update_state('dos', state)
        self.assertEqual(state['bathrooms'], 2)
        state['pending_question'] = {'key': 'property_type'}
        state = ollama_service.update_state('apartamento', state)
        self.assertEqual(state['property_type'], 'apartamento')

    def test_active_pdf_and_fake_image_are_rejected(self):
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.add_js('app.alert(1)')
        data = BytesIO(); writer.write(data)
        with self.assertRaises(ValueError):
            validate_chat_upload(SimpleUploadedFile('activo.pdf', data.getvalue(), content_type='application/pdf'))
        with self.assertRaises(ValueError):
            validate_chat_upload(SimpleUploadedFile('fake.png', b'\x89PNG\r\n\x1a\nnot-an-image', content_type='image/png'))

    @patch('crmChat.apps.facebook.services.send_attachment')
    def test_audio_and_video_real_content_validation_and_transport(self, transport):
        transport.side_effect = [{'message_id': 'audio-confirmed'}, {'message_id': 'video-confirmed'}]
        session = self.external('facebook')
        audio = BytesIO()
        with wave.open(audio, 'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
            wav.writeframes(b'\x00\x00' * 8000)
        response = self.send_file(session, SimpleUploadedFile('sonido.wav', audio.getvalue(), content_type='audio/wav'))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(transport.call_args.args[2], 'audio')
        video_path = os.path.join(self.temp.name, 'test.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=16x16:d=0.2',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', video_path], check=True, timeout=10)
        with open(video_path, 'rb') as video:
            upload = SimpleUploadedFile('video.mp4', video.read(), content_type='video/mp4')
        response = self.send_file(session, upload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(transport.call_args.args[2], 'video')
        with self.assertRaises(ValueError):
            validate_chat_upload(SimpleUploadedFile('falso.mp4', b'not a video', content_type='video/mp4'))

    @patch('crmChat.apps.facebook.services.send_attachment')
    def test_uncertain_delivery_is_not_replayed_and_window_is_enforced(self, transport):
        session = self.external('facebook')
        transport.return_value = {}  # Provider did not confirm a message id.
        response = self.send_file(session, image())
        self.assertEqual(response.status_code, 502)
        message_id = response.data['message']['id']
        self.assertFalse(response.data['message']['retry_allowed'])
        retry = self.client.post(f'/crm-chat/sessions/{session.pk}/messages/{message_id}/retry/')
        self.assertEqual(retry.status_code, 409)
        self.assertEqual(transport.call_count, 1)
        session.last_customer_message_at = timezone.now()-timedelta(hours=25)
        session.save(update_fields=['last_customer_message_at'])
        response = self.send_file(session, pdf())
        self.assertEqual(response.status_code, 502)
        self.assertIn('ventana', response.data['error'])
        self.assertEqual(transport.call_count, 1)
