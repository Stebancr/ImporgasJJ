import shutil
import tempfile
import uuid
from urllib.parse import urlparse
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from usuarios.models import Credenciales
from .models import ChannelIntegration, ChatAttachment, ChatMessage, ChatSession, CRMContact


class MobileCRMMessageTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix='crm-mobile-tests-')
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
            FRONTEND_PUBLIC_URL='https://www.imporgasjj.com',
        )
        self.settings_override.enable()
        self.agent = Credenciales.objects.create(usuario='mobile_agent', tipo_usuario=1, estado=1)
        self.other = Credenciales.objects.create(usuario='mobile_other', tipo_usuario=2, estado=1)
        self.session = ChatSession.objects.create(user_name='Cliente móvil', status='active', channel='ecommerce')
        self.url = reverse('crm-messages', kwargs={'pk': self.session.id})
        self.client.force_authenticate(self.agent)

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_mobile_text_is_outbound_realtime_ready_and_idempotent(self):
        client_id = str(uuid.uuid4())
        payload = {'text': 'Respuesta desde celular', 'origin': 'mobile', 'client_message_id': client_id}

        first = self.client.post(self.url, payload, format='multipart')
        second = self.client.post(self.url, payload, format='multipart')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(ChatMessage.objects.filter(client_message_id=client_id).count(), 1)
        message = ChatMessage.objects.get(client_message_id=client_id)
        self.assertEqual(message.direction, 'outbound')
        self.assertEqual(message.sender_type, 'agent')
        self.assertEqual(message.metadata['origin'], 'mobile')
        self.assertEqual(first.data['origin'], 'mobile')

    def test_image_upload_is_validated_and_requires_authorization_to_read(self):
        image = SimpleUploadedFile(
            'evidencia.png',
            b'\x89PNG\r\n\x1a\n' + b'valid-test-content',
            content_type='image/png',
        )
        response = self.client.post(self.url, {
            'text': 'Adjunto', 'origin': 'mobile',
            'client_message_id': str(uuid.uuid4()), 'file': image,
        }, format='multipart')

        self.assertEqual(response.status_code, 201)
        attachment = ChatAttachment.objects.get(message_id=response.data['id'])
        self.assertEqual(attachment.mime_type, 'image/png')
        self.assertTrue(attachment.metadata['protected'])
        self.assertEqual(response.data['attachments'][0]['url'], f'/api/crm-chat/attachments/{attachment.id}/')

        protected_url = reverse('crm-attachment', kwargs={'pk': attachment.id})
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(protected_url).status_code, 403)
        self.client.force_authenticate(self.agent)
        downloaded = self.client.get(protected_url)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded['Cache-Control'], 'private, no-store')

    def test_disguised_file_is_rejected_without_creating_message(self):
        invalid = SimpleUploadedFile('documento.pdf', b'<script>alert(1)</script>', content_type='application/pdf')
        response = self.client.post(self.url, {
            'origin': 'mobile', 'client_message_id': str(uuid.uuid4()), 'file': invalid,
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('no coincide', response.data['error'])
        self.assertFalse(ChatMessage.objects.exists())

    @patch('crmChat.views.dispatch_outbound_message')
    def test_external_attachment_uses_short_lived_canonical_delivery_url(self, dispatch):
        integration = ChannelIntegration.objects.create(
            name='Facebook controlado', channel='facebook', active=True,
            external_account_id='page-mobile-test', page_id='page-mobile-test',
        )
        external_session = ChatSession.objects.create(
            user_name='Cliente externo', status='active', channel='facebook',
            integration=integration, external_thread_id='recipient-test',
        )
        pdf = SimpleUploadedFile('ficha.pdf', b'%PDF-1.4\ncontrolled', content_type='application/pdf')
        response = self.client.post(reverse('crm-messages', kwargs={'pk': external_session.id}), {
            'origin': 'mobile', 'client_message_id': str(uuid.uuid4()), 'file': pdf,
        }, format='multipart')
        self.assertEqual(response.status_code, 201)
        message = ChatMessage.objects.get(pk=response.data['id'])
        delivery_url = message.metadata['outbound_payload']['url']
        self.assertTrue(delivery_url.startswith('https://www.imporgasjj.com/api/crm-chat/attachments/'))
        self.assertNotIn('localhost', delivery_url)
        self.assertNotIn('backend', delivery_url)
        dispatch.assert_called_once_with(message)

        parsed = urlparse(delivery_url)
        internal_path = parsed.path.removeprefix('/api') + f'?{parsed.query}'
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(internal_path).status_code, 200)

    def test_mobile_agent_can_list_contacts_but_customer_cannot(self):
        CRMContact.objects.create(name='Contacto móvil', phone='3000000000')
        response = self.client.get(reverse('crm-contact-list'), {'search': 'móvil'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'Contacto móvil')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(reverse('crm-contact-list')).status_code, 403)

    def test_api_root_is_available_for_public_health_checks(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse('api-root'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
