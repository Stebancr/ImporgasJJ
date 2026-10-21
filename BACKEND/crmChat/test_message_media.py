"""Isolated media/format regressions: no provider or customer traffic."""
import tempfile
import uuid
from unittest.mock import patch, Mock

from django.core.cache import cache
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from rest_framework.test import APITestCase
from usuarios.models import Credenciales
from .models import ChatSession, ChatMessage, ChatAttachment, ChannelIntegration
from .message_format import format_for_channel, validate_message_text
from .test_chatbot_upgrade import image, pdf
from .apps.whatsapp_web.views import _attach_gateway_media
from .tasks import _download_meta_attachment, download_meta_attachment, _assert_public_https


class MessageFormatTests(SimpleTestCase):
    def test_channel_transformations_preserve_links_and_lines(self):
        text = '**Hola**\n_Cliente_\n- Uno 😃\nhttps://example.com/a_b?x=1&y=2'
        for channel in ('facebook', 'instagram'):
            self.assertEqual(format_for_channel(text, channel),
                'Hola\nCliente\n- Uno 😃\nhttps://example.com/a_b?x=1&y=2')
        self.assertTrue(format_for_channel(text, 'whatsapp_web').startswith('*Hola*\n_Cliente_'))
        self.assertEqual(format_for_channel(text, 'ecommerce'), text)

    def test_legacy_html_and_unresolved_variables(self):
        self.assertEqual(format_for_channel('<b>Hola</b><br>Cliente<script>alert(1)</script>', 'facebook'), 'Hola\nCliente')
        with self.assertRaises(ValueError):
            validate_message_text('Hola {{desconocida}}', 'ecommerce')
        with self.assertRaises(ValueError):
            validate_message_text('a' * 1001, 'instagram')

    def test_untrusted_media_sources_are_rejected_before_network(self):
        for url in ('http://fbcdn.net/a', 'https://localhost/a', 'https://example.com/a',
                    'https://fbcdn.net.evil.test/a', 'https://user:pass@fbcdn.net/a', 'https://fbcdn.net:8443/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _assert_public_https(url)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class CustomerRealtimeTests(TransactionTestCase):
    def test_owner_receives_only_own_session_and_stranger_is_rejected(self):
        from asgiref.sync import async_to_sync
        from channels.testing import WebsocketCommunicator
        from channels.routing import URLRouter
        from channels.layers import get_channel_layer
        from django.urls import path
        from .consumers import CustomerChatConsumer
        owner = Credenciales.objects.create(usuario='ws-owner', tipo_usuario=2, estado=1)
        other = Credenciales.objects.create(usuario='ws-other', tipo_usuario=2, estado=1)
        session = ChatSession.objects.create(channel='ecommerce', user_id_ref=owner.pk)
        app = URLRouter([path('ws/<int:session_id>/', CustomerChatConsumer.as_asgi())])

        async def scenario():
            socket = WebsocketCommunicator(app, f'/ws/{session.pk}/', subprotocols=['crm-chat'])
            socket.scope['user'] = owner
            self.assertTrue((await socket.connect())[0])
            layer = get_channel_layer()
            await layer.group_send(f'crm_session_{session.pk + 1}', {'type': 'crm.event', 'payload': {'type': 'other'}})
            self.assertTrue(await socket.receive_nothing(timeout=.05))
            await layer.group_send(f'crm_session_{session.pk}', {'type': 'crm.event', 'payload': {'type': 'attachment.ready'}})
            self.assertEqual((await socket.receive_json_from())['type'], 'attachment.ready')
            await socket.disconnect()
            stranger = WebsocketCommunicator(app, f'/ws/{session.pk}/', subprotocols=['crm-chat'])
            stranger.scope['user'] = other
            self.assertFalse((await stranger.connect())[0])
            await stranger.disconnect()
        async_to_sync(scenario)()


class MediaFlowTests(APITestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        settings = override_settings(MEDIA_ROOT=temp.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = Credenciales.objects.create(usuario='media-owner', tipo_usuario=2, estado=1)
        self.other = Credenciales.objects.create(usuario='media-other', tipo_usuario=2, estado=1)
        self.client.force_authenticate(self.user)
        self.session = ChatSession.objects.create(channel='ecommerce', status='active', user_id_ref=self.user.pk)
        self.url = f'/crm-chat/sessions/{self.session.pk}/messages/'

    def test_customer_upload_persistence_idempotency_and_authorization(self):
        for factory in (image, pdf):
            identifier = str(uuid.uuid4())
            result = self.client.post(self.url, {'text': '**Documento**\nPara revisar',
                'client_message_id': identifier, 'file': factory()}, format='multipart')
            self.assertEqual(result.status_code, 201, result.data)
            attachment = result.data['attachments'][0]
            self.assertEqual(attachment['state'], 'stored')
            self.assertEqual(result.data['normalized_type'], 'mixed')
            duplicate = self.client.post(self.url, {'text': '**Documento**\nPara revisar',
                'client_message_id': identifier, 'file': factory()}, format='multipart')
            self.assertEqual(duplicate.data['id'], result.data['id'])
            self.assertEqual(ChatMessage.objects.get(pk=result.data['id']).attachments.count(), 1)
            path = attachment['url'].removeprefix('/api')
            self.assertEqual(self.client.get(path).status_code, 200)
            self.client.force_authenticate(self.other)
            self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.client.force_authenticate(self.user)
        reloaded = self.client.get(self.url).data['messages']
        self.assertEqual(len(reloaded), 2)
        self.assertTrue(all(row['attachments'][0]['url'] for row in reloaded))

    def test_gateway_failed_file_recovers_without_duplicate(self):
        message = ChatMessage.objects.create(session=self.session, sender_type='user')
        _attach_gateway_media(message, {'media_error': 'https://secret.invalid/token'})
        placeholder = message.attachments.get()
        self.assertNotIn('secret', placeholder.metadata['error'])
        cache.set('whatsapp-web-media:qa-recovery', {'name': 'test.png', 'mime_type': 'image/png',
            'size': 10, 'path': 'crm_gateway/test', 'sha256': 'test'})
        _attach_gateway_media(message, {'media': {'media_id': 'qa-recovery'}})
        _attach_gateway_media(message, {'media': {'media_id': 'qa-recovery'}})
        self.assertEqual(message.attachments.count(), 1)
        placeholder.refresh_from_db()
        self.assertEqual(placeholder.metadata['state'], 'stored')
        self.assertEqual(ChatMessage.objects.count(), 1)

    def test_meta_download_validates_stores_and_publishes(self):
        integration = ChannelIntegration.objects.create(channel='facebook', name='Synthetic', active=True)
        self.session.integration = integration
        self.session.channel = 'facebook'
        self.session.save()
        message = ChatMessage.objects.create(session=self.session, sender_type='user')
        attachment = ChatAttachment.objects.create(message=message, metadata={'url': 'https://media.fbcdn.net/qa'})
        response = Mock(headers={'Content-Type': 'application/octet-stream'})
        response.iter_content.return_value = [image().read()]
        with patch('crmChat.tasks._open_public_stream', return_value=('https://media.fbcdn.net/qa', response)), patch('crmChat.tasks.publish_crm_event') as event:
            _download_meta_attachment(attachment.pk)
            self.assertTrue(_download_meta_attachment(attachment.pk)['duplicate'])
        attachment.refresh_from_db()
        self.assertEqual(attachment.mime_type, 'image/png')
        self.assertEqual(attachment.metadata['state'], 'stored')
        self.assertTrue(attachment.file.storage.exists(attachment.file.name))
        event.assert_called_once()

    def test_failed_download_preserves_message_without_secret_error(self):
        message = ChatMessage.objects.create(session=self.session, sender_type='user', text='Conservar')
        attachment = ChatAttachment.objects.create(message=message)
        with patch('crmChat.tasks._download_meta_attachment', side_effect=ValueError('secret-url-token')):
            result = download_meta_attachment.run(attachment.pk)
        self.assertTrue(result['failed'])
        attachment.refresh_from_db()
        self.assertEqual(attachment.metadata['state'], 'rejected')
        self.assertNotIn('secret', attachment.metadata['error'])
        self.assertTrue(ChatMessage.objects.filter(pk=message.pk).exists())
