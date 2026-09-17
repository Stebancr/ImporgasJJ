from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from usuarios.models import Credenciales, Usuario
from usuarios.terms import CURRENT_TERMS_VERSION


class PublicTermsRegistrationTests(APITestCase):
    def setUp(self):
        self.payload = {
            'usuario': 'cliente@example.com', 'password': 'safe-test-password',
            'cedula': '123456789', 'nombre_completo': 'Cliente Ejemplo',
            'correo': 'cliente@example.com',
        }

    def test_registration_requires_current_explicit_acceptance(self):
        for acceptance, version in ((None, None), (False, CURRENT_TERMS_VERSION), (True, 'old-version')):
            with self.subTest(acceptance=acceptance, version=version):
                data = {**self.payload, 'terms_accepted': acceptance, 'terms_version': version}
                response = self.client.post(reverse('register-users'), data, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Usuario.objects.exists())
                self.assertFalse(Credenciales.objects.exists())

    def test_registration_records_version_and_timestamp_and_can_log_in(self):
        response = self.client.post(reverse('register-users'), {
            **self.payload, 'terms_accepted': True, 'terms_version': CURRENT_TERMS_VERSION,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        profile = Usuario.objects.get(cedula=self.payload['cedula'])
        self.assertEqual(profile.terms_version, CURRENT_TERMS_VERSION)
        self.assertIsNotNone(profile.terms_accepted_at)
        self.assertLessEqual(profile.terms_accepted_at, timezone.now())
        token = self.client.post(reverse('token_obtain_pair'), {
            'usuario': self.payload['usuario'], 'password': self.payload['password'],
        }, format='json')
        self.assertEqual(token.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        profile_response = self.client.get(reverse('perfil'))
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data['terms_version'], CURRENT_TERMS_VERSION)

    def test_existing_user_can_accept_current_version(self):
        profile = Usuario.objects.create(cedula='legacy', nombre_completo='Cliente Anterior')
        user = Credenciales.objects.create(usuario='legacy', usuario_rel=profile, estado=1, tipo_usuario=0)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.post(reverse('terms-accept'), {
            'terms_accepted': False, 'terms_version': CURRENT_TERMS_VERSION,
        }, format='json').status_code, 400)
        response = self.client.post(reverse('terms-accept'), {
            'terms_accepted': True, 'terms_version': CURRENT_TERMS_VERSION,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.terms_version, CURRENT_TERMS_VERSION)
        self.assertIsNotNone(profile.terms_accepted_at)

    def test_public_cannot_create_administrator(self):
        response = self.client.post(reverse('register'), {
            **self.payload, 'tipo_usuario': 4,
        }, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Credenciales.objects.exists())
