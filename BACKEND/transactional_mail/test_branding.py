"""Brand identity contracts; transport, senders and business content stay independent."""
import struct
from email.mime.application import MIMEApplication
from pathlib import Path
from unittest.mock import patch
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from .branding import LOGO_PATH, attach_logo, logo_context


@override_settings(EMAIL_LOGO_URL='', FRONTEND_PUBLIC_URL='https://www.imporgasjj.com',
                   EXTERNAL_PRODUCT_URL_TEMPLATE='https://www.imporgasjj.com/producto/{id}')
class EmailBrandingTests(SimpleTestCase):
    def test_default_inline_png_has_real_mime_and_proportions(self):
        context = logo_context()
        html = render_to_string('transactional_mail/brand_header.html', context)
        self.assertIn('alt="ImporGas JJ"', html)
        self.assertIn('src="cid:imporgas-logo"', html)
        message = EmailMultiAlternatives('subject', 'plain text', 'sender@example.invalid', ['qa@example.invalid'])
        message.attach_alternative(html, 'text/html')
        attach_logo(message, context)
        mime = message.message()
        self.assertEqual(mime.get_content_subtype(), 'related')
        images = [part for part in mime.walk() if part.get_content_type() == 'image/png']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['Content-ID'], '<imporgas-logo>')
        self.assertEqual(images[0].get_payload(decode=True), LOGO_PATH.read_bytes())
        self.assertEqual(struct.unpack('>II', LOGO_PATH.read_bytes()[16:24]), (600, 432))
        self.assertNotIn('<img', message.body)

    def test_deployed_first_party_https_url(self):
        with override_settings(EMAIL_LOGO_URL='https://www.imporgasjj.com/email/logo-imporgas.png'):
            context = logo_context()
        self.assertFalse(context['email_logo_inline'])
        message = EmailMultiAlternatives()
        attach_logo(message, context)
        self.assertFalse(message.attachments)
        self.assertIn('https://www.imporgasjj.com/email/', render_to_string('transactional_mail/brand_header.html', context))

    def test_unsafe_or_malformed_urls_fall_back_without_breaking_mail(self):
        for value in ['http://www.imporgasjj.com/logo.png', 'https://localhost/logo.png',
                      'https://127.0.0.1/logo.png', 'https://third-party.invalid/logo.png',
                      'https://user:secret@www.imporgasjj.com/logo.png',
                      'https://www.imporgasjj.com/logo.png?token=private',
                      'https://www.imporgasjj.com/logo.png#fragment', 'https://[malformed']:
            with self.subTest(value=value), override_settings(EMAIL_LOGO_URL=value):
                self.assertEqual(logo_context()['email_logo_src'], 'cid:imporgas-logo')

    def test_missing_asset_uses_readable_brand_without_broken_image(self):
        with patch('transactional_mail.branding.LOGO_PATH') as path:
            path.is_file.return_value = False
            context = logo_context()
        html = render_to_string('transactional_mail/brand_header.html', context)
        self.assertNotIn('<img', html)
        self.assertIn('ImporGas JJ', html)

    def test_existing_attachments_remain_intact(self):
        message = EmailMultiAlternatives()
        document = MIMEApplication(b'%PDF-QA', _subtype='pdf')
        message.attach(document)
        attach_logo(message, logo_context())
        self.assertEqual(message.attachments[0], document)
        self.assertEqual(message.message().get_content_subtype(), 'mixed')

    def test_all_runtime_html_templates_share_header_and_base(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ['transactional_mail/templates/transactional_mail/message.html',
                         'usuarios/templates/usuarios/password_reset.html']:
            template = (root / relative).read_text(encoding='utf-8')
            self.assertIn('extends "transactional_mail/base.html"', template)
            self.assertIn('include "transactional_mail/brand_header.html"', template)
        for relative in ['transactional_mail/templates/transactional_mail/message.txt',
                         'usuarios/templates/usuarios/password_reset.txt']:
            text = (root / relative).read_text(encoding='utf-8')
            self.assertNotIn('<img', text)
            self.assertNotIn('email_logo', text)
