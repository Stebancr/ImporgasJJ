import re

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from usuarios.models import Credenciales, Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CustomerAccountTests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(
            cedula='account-123', nombre_completo='Cliente Ejemplo',
            correo='account@example.com', telefono='3001234567', sede='Interna',
        )
        self.user = Credenciales.objects.create(
            usuario='account@example.com', usuario_rel=profile, tipo_usuario=0, estado=1,
        )
        self.user.set_password('Old-safe-password-123')
        self.user.save(update_fields=['password'])

    def test_customer_profile_omits_sede_and_change_password_validates_current(self):
        self.client.force_authenticate(self.user)
        profile = self.client.get(reverse('perfil'))
        self.assertEqual(profile.status_code, 200)
        self.assertNotIn('sede', profile.data)
        payload = {
            'current_password': 'wrong', 'new_password': 'New-safe-password-456',
            'confirm_password': 'New-safe-password-456',
        }
        self.assertEqual(self.client.post(reverse('customer-password-change'), payload, format='json').status_code, 400)
        payload['current_password'] = 'Old-safe-password-123'
        payload['confirm_password'] = 'different'
        self.assertEqual(self.client.post(reverse('customer-password-change'), payload, format='json').status_code, 400)
        payload['confirm_password'] = payload['new_password']
        self.assertEqual(self.client.post(reverse('customer-password-change'), payload, format='json').status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))

    def test_customer_profile_edit_ignores_sede_and_updates_login_email(self):
        self.client.force_authenticate(self.user)
        result = self.client.put(reverse('perfil'), {
            'nombre_completo': 'Nuevo Nombre', 'correo': 'nuevo@example.com',
            'telefono': '3007654321', 'sede': 'No permitida',
        }, format='json')
        self.assertEqual(result.status_code, 200)
        self.user.refresh_from_db()
        self.user.usuario_rel.refresh_from_db()
        self.assertEqual(self.user.usuario, 'nuevo@example.com')
        self.assertEqual(self.user.usuario_rel.sede, 'Interna')

    def test_password_change_revokes_only_this_customers_jwt(self):
        tokens = self.client.post(reverse('token_obtain_pair'), {
            'usuario': 'account@example.com', 'password': 'Old-safe-password-123',
        }, format='json')
        self.assertEqual(tokens.status_code, 200)
        access, refresh = tokens.data['access'], tokens.data['refresh']
        authenticated = APIClient()
        authenticated.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(authenticated.get(reverse('perfil')).status_code, 200)
        change = authenticated.post(reverse('customer-password-change'), {
            'current_password': 'Old-safe-password-123',
            'new_password': 'New-safe-password-456',
            'confirm_password': 'New-safe-password-456',
        }, format='json')
        self.assertEqual(change.status_code, 200)
        self.assertEqual(authenticated.get(reverse('perfil')).status_code, 401)
        self.assertEqual(self.client.post(reverse('token_refresh'), {'refresh': refresh}, format='json').status_code, 401)
        self.assertEqual(self.client.post(reverse('token_obtain_pair'), {
            'usuario': 'account@example.com', 'password': 'New-safe-password-456',
        }, format='json').status_code, 200)

    def test_reset_email_is_generic_and_token_is_one_use(self):
        url = reverse('customer-password-reset-request')
        missing = self.client.post(url, {'email': 'missing@example.com'}, format='json')
        existing = self.client.post(url, {'email': 'account@example.com'}, format='json')
        self.assertEqual(missing.status_code, existing.status_code)
        self.assertEqual(missing.data, existing.data)
        self.assertEqual(len(mail.outbox), 1)
        uid, token = re.search(r'/restablecer-contrasena/([^/]+)/([^\s/]+)', mail.outbox[0].body).groups()
        payload = {'uid': uid, 'token': token, 'new_password': 'Reset-safe-password-456',
                   'confirm_password': 'Reset-safe-password-456'}
        confirm_url = reverse('customer-password-reset-confirm')
        self.assertEqual(self.client.post(confirm_url, {**payload, 'token': 'bad-token'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(confirm_url, payload, format='json').status_code, 200)
        self.assertEqual(self.client.post(confirm_url, payload, format='json').status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_expired_token_is_rejected(self):
        self.client.post(reverse('customer-password-reset-request'), {'email': 'account@example.com'}, format='json')
        uid, token = re.search(r'/restablecer-contrasena/([^/]+)/([^\s/]+)', mail.outbox[0].body).groups()
        result = self.client.post(reverse('customer-password-reset-confirm'), {
            'uid': uid, 'token': token, 'new_password': 'Reset-safe-password-456',
            'confirm_password': 'Reset-safe-password-456',
        }, format='json')
        self.assertEqual(result.status_code, 400)
