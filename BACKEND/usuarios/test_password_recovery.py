import re
import smtplib
import ssl
from email.utils import parseaddr
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from .models import Usuario, Credenciales, PasswordResetDelivery
from .password_recovery import deliver, sender, build_email, tokens


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   SERVER_EMAIL_NOREPLY='reset@example.invalid', FRONTEND_PUBLIC_URL='http://localhost', DEBUG=True, ALLOWED_HOSTS=['*'])
class PasswordRecoveryTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.profile = Usuario.objects.create(cedula='reset-test-only', nombre_completo='Cliente Recuperacion', correo='recover@example.invalid')
        self.user = Credenciales.objects.create(usuario=self.profile.correo, usuario_rel=self.profile, estado=1, tipo_usuario=0)
        self.user.set_password('Old-synthetic-secret-245!'); self.user.save()
        self.enqueue = patch('usuarios.password_recovery.enqueue', side_effect=deliver)
        self.enqueue.start(); self.addCleanup(self.enqueue.stop)

    def request_email(self, email=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('customer-password-reset-request'), {'email': email or self.profile.correo}, format='json')

    def link(self):
        value = re.search(r'https?://[^\s]+#uid=[^\s]+', mail.outbox[-1].body).group()
        fields = parse_qs(urlsplit(value).fragment)
        return {'uid': fields['uid'][0], 'token': fields['token'][0]}

    def confirm(self, link, password='New-synthetic-secret-457!', confirmation=None):
        return self.client.post(reverse('customer-password-reset-confirm'), {**link, 'new_password': password,
            'confirm_password': password if confirmation is None else confirmation}, format='json')

    def test_unknown_inactive_and_existing_have_identical_responses(self):
        known = self.request_email()
        cache.clear()
        missing = self.request_email('unknown@example.invalid')
        self.user.estado = 0; self.user.save(); cache.clear()
        inactive = self.request_email()
        for result in [missing, inactive]:
            self.assertEqual(result.status_code, known.status_code)
            self.assertEqual(result.data, known.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_email_and_empty(self):
        for value in ['', 'not-email', ['list'], 'x\r\nBcc:bad@example.invalid']:
            self.assertEqual(self.client.post(reverse('customer-password-reset-request'), {'email': value}, format='json').status_code, 400)

    def test_case_normalization_and_no_duplicate_send(self):
        self.request_email('  RECOVER@EXAMPLE.INVALID  ')
        self.request_email()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PasswordResetDelivery.objects.count(), 1)

    def test_three_per_email_per_hour_neutral_and_ip_limit(self):
        for index in range(4):
            cache.delete('reset:cooldown:' + __import__('usuarios.password_recovery', fromlist=['email_hash']).email_hash(self.profile.correo))
            response = self.request_email()
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 3)
        cache.clear()
        for index in range(10):
            self.assertEqual(self.request_email(f'unknown{index}@example.invalid').status_code, 200)
        self.assertEqual(self.request_email('eleventh@example.invalid').status_code, 429)

    def test_real_mime_sender_structure_logo_and_configured_absolute_link(self):
        with override_settings(DEFAULT_FROM_EMAIL='sales@example.invalid', SERVER_EMAIL_APLICACION='technical@example.invalid'):
            self.request_email()
        message = mail.outbox[0]
        self.assertEqual(parseaddr(str(message.message()['From']))[1], 'reset@example.invalid')
        self.assertEqual(message.to, [self.profile.correo]); self.assertFalse(message.cc); self.assertFalse(message.bcc)
        self.assertEqual(message.subject, 'Restablece tu contraseña de ImporGas JJ')
        self.assertTrue(message.alternatives); self.assertTrue(message.attachments)
        self.assertIn('60 minutos', message.body)
        self.assertIn('http://localhost/restablecer-contrasena#uid=', message.body)
        self.assertIn('cid:imporgas-logo', message.alternatives[0].content)
        self.assertNotIn('Old-synthetic', message.body)
        self.assertEqual(str(message.message()['From']).split('<')[0].strip(), 'ImporGas JJ - No responder')

    def test_host_and_redirect_input_cannot_change_link(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('customer-password-reset-request'), {'email': self.profile.correo, 'redirect': 'https://attacker.invalid'}, format='json', HTTP_HOST='attacker.invalid')
        self.assertNotIn('attacker.invalid', mail.outbox[0].body)

    def test_validate_confirm_login_reuse_and_old_jwt_revoked(self):
        login = self.client.post(reverse('token_obtain_pair'), {'usuario': self.user.usuario, 'password': 'Old-synthetic-secret-245!'}, format='json')
        self.assertEqual(login.status_code, 200)
        self.request_email(); link = self.link()
        self.assertEqual(self.client.post(reverse('customer-password-reset-validate'), link, format='json').status_code, 200)
        self.assertEqual(self.confirm(link).status_code, 200)
        self.assertEqual(self.confirm(link).status_code, 400)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, 'New-synthetic-secret-457!')
        self.assertTrue(self.user.check_password('New-synthetic-secret-457!'))
        self.assertFalse(self.user.check_password('Old-synthetic-secret-245!'))
        self.assertEqual(self.client.post(reverse('token_obtain_pair'), {'usuario': self.user.usuario, 'password': 'New-synthetic-secret-457!'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(reverse('token_obtain_pair'), {'usuario': self.user.usuario, 'password': 'Old-synthetic-secret-245!'}, format='json').status_code, 401)
        self.assertEqual(self.client.post(reverse('token_refresh'), {'refresh': login.data['refresh']}, format='json').status_code, 401)
        old_session = APIClient()
        old_session.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['access'])
        self.assertEqual(old_session.get(reverse('perfil')).status_code, 401)

    def test_new_request_invalidates_old_token(self):
        self.request_email(); first = self.link(); cache.clear()
        self.request_email(); second = self.link()
        self.assertEqual(self.confirm(first).status_code, 400)
        self.assertEqual(self.confirm(second).status_code, 200)

    def test_expiration_tampering_wrong_user_and_malformed_payloads(self):
        self.request_email(); link = self.link()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertEqual(self.confirm(link).status_code, 400)
        for wrong in [{**link, 'token': link['token']+'x'}, {**link, 'uid':'OTk5OTk5'}, {'uid':[], 'token':{}}, {'uid':'bad','token':'bad'}]:
            self.assertEqual(self.confirm(wrong).status_code, 400)

    def test_security_changes_invalidate_link(self):
        for field, value in [('estado', 0), ('tipo_usuario', 1), ('password_version', 1), ('usuario', 'changed@example.invalid')]:
            self.user.refresh_from_db(); token = tokens.make_token(self.user)
            original = getattr(self.user, field); setattr(self.user, field, value)
            self.assertFalse(tokens.check_token(self.user, token)); setattr(self.user, field, original)
        token = tokens.make_token(self.user)
        self.user.usuario_rel.correo = 'changed@example.invalid'
        self.assertFalse(tokens.check_token(self.user, token))

    def test_password_policies_and_mismatch_keep_token_valid(self):
        self.request_email(); link = self.link()
        for password in ['short', 'password123', '1234567891011', 'recover@example.invalid']:
            self.assertEqual(self.confirm(link, password).status_code, 400)
        self.assertEqual(self.confirm(link, confirmation='mismatch').status_code, 400)
        self.assertEqual(self.confirm(link).status_code, 200)

    def test_missing_empty_invalid_sender_records_failure_without_fallback(self):
        for value in ['', 'not-email', 'a@example.invalid\r\nBcc: bad@example.invalid']:
            cache.clear()
            with override_settings(SERVER_EMAIL_NOREPLY=value):
                self.assertEqual(self.request_email().status_code, 200)
            event = PasswordResetDelivery.objects.latest('created_at')
            self.assertEqual(event.state, 'failed')
            self.assertEqual(event.last_error, 'configuration_SERVER_EMAIL_NOREPLY')
        self.assertFalse(mail.outbox)

    def test_provider_errors_are_sanitized_and_not_duplicated(self):
        failures = [(ssl.SSLCertVerificationError('PRIVATE'), 'smtp_tls_certificate'),
                    (smtplib.SMTPSenderRefused(550, b'PRIVATE', 'private@example.invalid'), 'smtp_sender_rejected'),
                    (smtplib.SMTPAuthenticationError(535, b'PRIVATE'), 'smtp_authentication'),
                    (TimeoutError('PRIVATE'), 'smtp_delivery_uncertain'),
                    (smtplib.SMTPConnectError(421, b'PRIVATE'), 'mail_unavailable')]
        for error, code in failures:
            cache.clear()
            with patch('usuarios.password_recovery.EmailMultiAlternatives.send', side_effect=error):
                self.request_email()
            event = PasswordResetDelivery.objects.latest('created_at')
            self.assertEqual(event.last_error, code)
            self.assertFalse(deliver(event.pk))
            self.assertNotIn('PRIVATE', event.last_error)

    def test_queue_failure_response_stays_neutral(self):
        self.enqueue.stop()
        with patch('usuarios.tasks.deliver_password_reset.apply_async', side_effect=RuntimeError('PRIVATE')):
            result = self.request_email()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(PasswordResetDelivery.objects.get().last_error, 'queue_unavailable')

    def test_email_rate_limit_cache_failure_does_not_send(self):
        with patch('usuarios.password_recovery.cache.add', side_effect=RuntimeError('PRIVATE')):
            response = self.request_email()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(mail.outbox)

    def test_no_raw_email_token_or_password_persisted_in_audit(self):
        self.request_email()
        data = str(PasswordResetDelivery.objects.values().get())
        self.assertNotIn(self.profile.correo, data)
        self.assertNotIn(self.link()['token'], data)
        self.assertNotIn('synthetic-secret', data)

    def test_delivery_task_idempotence_and_superseded_queue(self):
        self.enqueue.stop()
        with patch('usuarios.password_recovery.enqueue'):
            self.request_email(); event = PasswordResetDelivery.objects.get()
            cache.clear(); self.request_email()
        self.assertFalse(deliver(event.pk))
        latest = PasswordResetDelivery.objects.latest('created_at')
        self.assertTrue(deliver(latest.pk)); self.assertFalse(deliver(latest.pk))
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', PASSWORD_RESET_ALLOWED_RECIPIENTS=[])
    def test_development_allowlist_blocks_unapproved_real_recipients(self):
        with patch('usuarios.password_recovery.EmailMultiAlternatives.send') as smtp:
            self.request_email(); smtp.assert_not_called()
        self.assertEqual(PasswordResetDelivery.objects.get().state, 'failed')

    def test_production_url_requires_https(self):
        with override_settings(DEBUG=False, FRONTEND_PUBLIC_URL='http://localhost'):
            with self.assertRaises(ImproperlyConfigured):
                build_email(self.user)

    def test_sender_does_not_change_other_senders(self):
        from transactional_mail.configuration import sender_for
        with override_settings(DEFAULT_FROM_EMAIL='sales@example.invalid', SERVER_EMAIL_APLICACION='tech@example.invalid', SERVER_EMAIL='server@example.invalid'):
            self.assertIn('reset@example.invalid', sender())
            self.assertEqual(sender_for('order'), 'sales@example.invalid')
            self.assertIn('tech@example.invalid', sender_for('visit'))

    def test_inactive_profile_and_ambiguous_email_never_receive_mail(self):
        self.profile.estado = 0; self.profile.save()
        self.request_email()
        self.assertFalse(mail.outbox)
        self.profile.estado = 1; self.profile.save(); cache.clear()
        other = Usuario.objects.create(cedula='duplicate-reset', nombre_completo='QA', correo=self.profile.correo)
        Credenciales.objects.create(usuario='different-login', usuario_rel=other)
        self.request_email()
        self.assertFalse(mail.outbox)

    def test_forwarded_for_cannot_rotate_ip_limit(self):
        with patch('usuarios.password_recovery.request_reset'):
            for index in range(11):
                response = self.client.post(reverse('customer-password-reset-request'), {'email':'unknown@example.invalid'},
                    format='json', HTTP_X_FORWARDED_FOR=f'203.0.113.{index}')
        self.assertEqual(response.status_code, 429)

    def test_no_secret_in_success_or_failure_logs(self):
        with self.assertLogs('usuarios.password_recovery', level='INFO') as recorded:
            self.request_email()
        text = str(recorded.output)
        self.assertNotIn(self.profile.correo, text)
        self.assertNotIn(self.link()['token'], text)
        self.assertNotIn('synthetic-secret', text)

    def test_raw_dotenv_sender_quotes_are_normalized(self):
        import os
        import subprocess
        import sys
        for value in ["'reset@example.invalid'", '"reset@example.invalid"', 'reset@example.invalid']:
            output = subprocess.check_output([sys.executable, '-c',
                'from core import settings; print(settings.SERVER_EMAIL_NOREPLY)'],
                env={**os.environ, 'SERVER_EMAIL_NOREPLY': value}, text=True)
            self.assertEqual(output.strip(), 'reset@example.invalid')

    def test_smtp_probe_never_sends_message_or_changes_other_sender(self):
        import io
        from django.core.management import call_command
        with patch('transactional_mail.management.commands.check_transactional_smtp.validate_smtp'), \
                patch('transactional_mail.management.commands.check_transactional_smtp.smtplib.SMTP') as connection:
            smtp = connection.return_value.__enter__.return_value
            smtp.mail.return_value = (250, b'PRIVATE')
            output = io.StringIO()
            call_command('check_transactional_smtp', password_reset=True, technical_visits=False, stdout=output)
            smtp.mail.assert_called_once_with('reset@example.invalid')
            smtp.rcpt.assert_not_called(); smtp.data.assert_not_called(); smtp.sendmail.assert_not_called()
            self.assertNotIn('PRIVATE', output.getvalue())

    def test_controlled_command_refuses_existing_account_without_password_change(self):
        from django.core.management import call_command, CommandError
        password = self.user.password
        with patch('usuarios.password_recovery.EmailMultiAlternatives.send') as smtp:
            with self.assertRaises(CommandError):
                call_command('test_password_recovery_smtp', recipient=self.profile.correo, send=True)
            smtp.assert_not_called()
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, password)
        self.assertEqual(Credenciales.objects.count(), 1)

    @override_settings(DEBUG=False)
    def test_controlled_command_rejects_production(self):
        from django.core.management import call_command, CommandError
        with self.assertRaises(CommandError):
            call_command('test_password_recovery_smtp', recipient=self.profile.correo, send=True)
