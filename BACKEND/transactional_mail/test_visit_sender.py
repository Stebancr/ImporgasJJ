"""Only From changes; all messages use locmem and synthetic recipients."""
import hashlib
import io
import os
import smtplib
import subprocess
import sys
from datetime import timedelta
from types import SimpleNamespace
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from dotenv import dotenv_values
from AppVisits.views import _persist_visit_pdf
from . import tests as fixtures
from .configuration import sender_for, VisitSenderConfigurationError
from .models import Delivery
from .service import send


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', TRANSACTIONAL_EMAIL_ENABLED=True,
    SERVER_EMAIL_APLICACION='technical@example.invalid', DEBUG=True,
    FRONTEND_PUBLIC_URL='http://localhost', PUBLIC_API_URL='http://localhost/api',
    TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS=['qa@example.invalid'])
class VisitSenderTests(APITestCase):
    setUp = fixtures.TransactionalTests.setUp
    registration = fixtures.TransactionalTests.registration

    def ready_visit(self):
        _persist_visit_pdf(self.visit.pk)
        self.visit.refresh_from_db()
        return self.registration('visit', self.visit)

    def test_real_mime_from_and_entire_content_unchanged(self):
        delivery = self.ready_visit()
        with patch('django.core.signing.time.time', return_value=1700000000):
            with patch('transactional_mail.service.sender_for', return_value='Old sender <old@example.invalid>'):
                self.assertTrue(send(delivery.pk))
            before = mail.outbox[-1]
            delivery.refresh_from_db()
            with self.visit.pdf_final.open('rb') as document:
                pdf_before = document.read()
            document_name = self.visit.pdf_final.name
            message_id = delivery.message_id
            # Test-only rewind of the same logical event to compare identical data.
            Delivery.objects.filter(pk=delivery.pk).update(state='pending', next_attempt_at=None)
            self.assertTrue(send(delivery.pk))
            after = mail.outbox[-1]
        parsed = BytesParser(policy=policy.default).parsebytes(after.message().as_bytes())
        sender = parsed['From'].addresses[0]
        self.assertEqual(sender.display_name, 'Servicio Técnico ImporGas JJ')
        self.assertEqual(sender.addr_spec, 'technical@example.invalid')
        for field in ('subject', 'body', 'to', 'cc', 'bcc', 'reply_to', 'extra_headers'):
            self.assertEqual(getattr(before, field), getattr(after, field), field)
        self.assertEqual(before.alternatives, after.alternatives)
        leaves = lambda message: [(part.get_content_type(), part.get_payload(decode=True),
            part.get_filename(), part.get('Content-ID')) for part in message.message().walk() if not part.is_multipart()]
        self.assertEqual(leaves(before), leaves(after))
        delivery.refresh_from_db()
        self.assertEqual(delivery.message_id, message_id)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.pdf_final.name, document_name)
        with self.visit.pdf_final.open('rb') as document:
            self.assertEqual(hashlib.sha256(document.read()).digest(), hashlib.sha256(pdf_before).digest())
        self.assertEqual(Delivery.objects.filter(kind='visit').count(), 1)

    def test_missing_empty_invalid_and_injected_sender_never_fall_back(self):
        for address in ('', ' ', 'invalid', 'Other <other@example.invalid>', 'bad\r\nBcc:bad@example.invalid'):
            with self.subTest(address_class='invalid'), override_settings(SERVER_EMAIL_APLICACION=address):
                with self.assertRaises(VisitSenderConfigurationError) as error:
                    sender_for('visit')
                self.assertIn('SERVER_EMAIL_APLICACION', str(error.exception))
                if len(address) > 1:
                    self.assertNotIn(address, str(error.exception))

    def test_absent_setting_is_a_clear_configuration_error(self):
        with patch('transactional_mail.configuration.settings', SimpleNamespace()):
            with self.assertRaises(VisitSenderConfigurationError):
                sender_for('visit')

    def test_configuration_failure_preserves_completed_visit_pdf_and_retries_same_event(self):
        delivery = self.ready_visit()
        original_pdf = self.visit.pdf_final.name
        original_hash = self.visit.pdf_sha256
        for debug in (True, False):
            with override_settings(SERVER_EMAIL_APLICACION='', DEBUG=debug), self.assertLogs('transactional_mail.service', level='WARNING') as logs:
                self.assertFalse(send(delivery.pk))
            self.assertIn('SERVER_EMAIL_APLICACION', ' '.join(logs.output))
            delivery.refresh_from_db()
            self.assertEqual(delivery.state, 'failed')
            self.assertEqual(delivery.last_error, 'visit_sender_configuration_invalid_SERVER_EMAIL_APLICACION')
            self.visit.refresh_from_db()
            self.assertEqual(self.visit.estado, self.visit.ESTADO_FINALIZADA)
            self.assertEqual(self.visit.pdf_final.name, original_pdf)
            self.assertEqual(self.visit.pdf_sha256, original_hash)
            Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        self.assertEqual(len(mail.outbox), 0)
        self.owner.tipo_usuario = 1; self.owner.save()
        self.client.force_authenticate(self.owner)
        with patch('transactional_mail.tasks.deliver.apply_async'):
            self.assertEqual(self.client.post(f'/mail/deliveries/{delivery.pk}/retry/').status_code, 202)
        self.assertTrue(send(delivery.pk))
        self.assertFalse(send(delivery.pk))
        self.assertFalse(self.registration_again())
        self.assertEqual(Delivery.objects.filter(kind='visit').count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def registration_again(self):
        from .service import queue
        with patch('transactional_mail.tasks.deliver.apply_async'):
            return queue('visit', self.visit.pk)

    def test_provider_sender_rejection_is_sanitized_and_retry_keeps_event_and_from(self):
        delivery = self.ready_visit()
        with patch('transactional_mail.service.EmailMultiAlternatives.send', side_effect=smtplib.SMTPSenderRefused(550, b'PRIVATE_PROVIDER_REPLY', 'private@example.invalid')):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.last_error, 'smtp_sender_rejected_550')
        self.assertNotIn('PRIVATE', delivery.last_error)
        Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        self.assertTrue(send(delivery.pk))
        self.assertFalse(send(delivery.pk))
        self.assertIn('technical@example.invalid', mail.outbox[-1].from_email)
        self.assertEqual(Delivery.objects.filter(kind='visit').count(), 1)

    def test_other_senders_ignore_visit_configuration(self):
        with override_settings(SERVER_EMAIL_APLICACION='', DEFAULT_FROM_EMAIL='Sales <sales@example.invalid>', SERVER_EMAIL='server@example.invalid'):
            delivery = self.registration('order', self.order)
            self.assertTrue(send(delivery.pk))
            self.assertEqual(mail.outbox[-1].from_email, 'Sales <sales@example.invalid>')
            self.assertEqual(sender_for('order'), 'Sales <sales@example.invalid>')

    def test_provider_outage_keeps_visit_and_pdf_and_retries_with_same_sender(self):
        delivery = self.ready_visit()
        pdf_hash = self.visit.pdf_sha256
        with patch('transactional_mail.service.EmailMultiAlternatives.send', side_effect=smtplib.SMTPConnectError(421, b'PRIVATE_PROVIDER_REPLY')):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.state, 'failed')
        self.assertEqual(delivery.last_error, 'smtp_temporarily_unavailable_421')
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.estado, self.visit.ESTADO_FINALIZADA)
        self.assertEqual(self.visit.pdf_sha256, pdf_hash)
        Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        self.assertTrue(send(delivery.pk))
        self.assertIn('technical@example.invalid', mail.outbox[-1].from_email)
        self.assertEqual(Delivery.objects.filter(kind='visit').count(), 1)

    def test_password_reset_uses_no_reply_and_server_alert_keeps_its_sender(self):
        from django.urls import reverse
        from usuarios.models import Usuario
        profile = Usuario.objects.create(cedula='qa-reset-sender', nombre_completo='QA', correo='qa@example.invalid')
        self.owner.usuario_rel = profile; self.owner.save()
        from django.core.cache import cache
        from usuarios.password_recovery import deliver
        cache.clear()
        with override_settings(SERVER_EMAIL_NOREPLY='reset@example.invalid', DEFAULT_FROM_EMAIL='Sales <sales@example.invalid>', SERVER_EMAIL='server@example.invalid', ADMINS=[('QA', 'qa@example.invalid')]), patch('usuarios.password_recovery.enqueue', side_effect=deliver), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('customer-password-reset-request'), {'email': profile.correo}, format='json')
            self.assertEqual(response.status_code, 200)
        self.assertIn('reset@example.invalid', mail.outbox[-1].from_email)
        with override_settings(SERVER_EMAIL='server@example.invalid', ADMINS=[('QA', 'qa@example.invalid')]):
            mail.mail_admins('Synthetic server alert', 'Synthetic body')
            self.assertEqual(mail.outbox[-1].from_email, 'server@example.invalid')

    def test_dotenv_and_raw_compose_quotes_are_removed_without_changing_smtp(self):
        for raw in ("'technical@example.invalid'", '"technical@example.invalid"', 'technical@example.invalid'):
            self.assertEqual(dotenv_values(stream=io.StringIO('SERVER_EMAIL_APLICACION='+raw))['SERVER_EMAIL_APLICACION'], 'technical@example.invalid')
            result = subprocess.check_output([sys.executable, '-c',
                'from core import settings; print(settings.SERVER_EMAIL_APLICACION)'],
                env={**os.environ, 'SERVER_EMAIL_APLICACION': raw}, text=True)
            self.assertEqual(result.strip(), 'technical@example.invalid')

    def test_interrupted_worker_does_not_blindly_resend_a_visit(self):
        from .tasks import recover_pending
        delivery = self.ready_visit()
        Delivery.objects.filter(pk=delivery.pk).update(state='sending', started_at=timezone.now()-timedelta(minutes=6))
        with patch('transactional_mail.tasks.deliver.delay') as enqueue:
            recover_pending.run()
            enqueue.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual(delivery.state, 'uncertain')
        self.assertFalse(send(delivery.pk))
        self.assertEqual(len(mail.outbox), 0)

    def test_smtp_probe_selects_visit_sender_without_data_or_recipients(self):
        from django.core.management import call_command
        with patch('transactional_mail.management.commands.check_transactional_smtp.validate_smtp'), \
                patch('transactional_mail.management.commands.check_transactional_smtp.smtplib.SMTP') as connection:
            smtp = connection.return_value.__enter__.return_value
            smtp.mail.return_value = (250, b'PRIVATE_REPLY_NOT_PRINTED')
            output = io.StringIO()
            call_command('check_transactional_smtp', technical_visits=True, stdout=output)
            smtp.mail.assert_called_once_with('technical@example.invalid')
            smtp.rcpt.assert_not_called(); smtp.data.assert_not_called(); smtp.sendmail.assert_not_called()
            smtp.rset.assert_called_once()
            self.assertNotIn('PRIVATE_REPLY', output.getvalue())
