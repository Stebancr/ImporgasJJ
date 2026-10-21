import os
from unittest.mock import patch
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from scripts.smtp_delivery_canary import guard, deliver_canary, MARKER
from usuarios.models import Usuario, Credenciales, PasswordResetDelivery
from usuarios.password_recovery import email_hash


@override_settings(DEBUG=True, FRONTEND_PUBLIC_URL='http://localhost',
    PASSWORD_RESET_ALLOWED_RECIPIENTS=['canary@example.invalid'],
    SERVER_EMAIL_NOREPLY='reset@example.invalid', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SMTPCanaryTests(TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'SMTP_CANARY_ENABLED':'1'})
        env.start(); self.addCleanup(env.stop)
        profile = Usuario.objects.create(cedula='canary-test', nombre_completo='Synthetic QA', correo='canary@example.invalid')
        self.user = Credenciales.objects.create(usuario=profile.correo, usuario_rel=profile)
        self.user.set_password('Synthetic-canary-only-942!'); self.user.save()
        self.event = PasswordResetDelivery.objects.create(user=self.user, recipient_hash=email_hash(profile.correo),
            version=0, last_error=MARKER)

    def test_actual_service_local_backend_prefix_headers_and_once(self):
        self.assertTrue(deliver_canary.run(str(self.event.pk)))
        self.assertFalse(deliver_canary.run(str(self.event.pk)))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertTrue(message.subject.startswith('[PRUEBA DESARROLLO] '))
        self.assertEqual(message.to, ['canary@example.invalid']); self.assertFalse(message.cc); self.assertFalse(message.bcc)
        self.assertEqual(message.extra_headers['Message-ID'], f'<smtp-dev-{self.event.pk}@imporgasjj.com>')
        from usuarios.password_recovery import SUBJECT
        self.assertFalse(SUBJECT.startswith('[PRUEBA'))

    def test_production_disabled_flag_external_frontend_and_multiple_recipients_refused(self):
        for values in [{'DEBUG':False}, {'FRONTEND_PUBLIC_URL':'http://localhost.evil.invalid'},
                       {'PASSWORD_RESET_ALLOWED_RECIPIENTS':['a@example.invalid','b@example.invalid']}]:
            with override_settings(**values), self.assertRaises(ImproperlyConfigured):
                guard()
        with patch.dict(os.environ, {'SMTP_CANARY_ENABLED':'0'}), self.assertRaises(ImproperlyConfigured):
            guard()

    def test_non_qa_event_refused(self):
        self.event.last_error = ''; self.event.save()
        self.assertFalse(deliver_canary.run(str(self.event.pk)))
        self.assertFalse(mail.outbox)

    def test_other_recipient_refused(self):
        with override_settings(PASSWORD_RESET_ALLOWED_RECIPIENTS=['other@example.invalid']):
            self.assertFalse(deliver_canary.run(str(self.event.pk)))
        self.assertFalse(mail.outbox)
