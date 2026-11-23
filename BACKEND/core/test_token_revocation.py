"""Synthetic credentials only: never load or submit historical tokens."""
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from rest_framework.test import APITestCase
from usuarios.models import Credenciales, Usuario


class PasswordVersionPreventiveRevocationTests(APITestCase):
    def test_increment_revokes_access_refresh_without_changing_password_or_role(self):
        profile = Usuario.objects.create(
            cedula='revocation-fixture', nombre_completo='Synthetic QA',
            correo='revocation@example.invalid', estado=1)
        account = Credenciales(usuario='revocation-fixture', usuario_rel=profile,
                                tipo_usuario=0, estado=1)
        password = 'Synthetic@Revocation937!'
        account.set_password(password)
        account.save()
        original = (account.password, account.tipo_usuario, account.estado)
        credentials = {'usuario': account.usuario, 'password': password}
        self.client.defaults['REMOTE_ADDR'] = '192.0.2.149'
        issued = self.client.post('/auth/token/', credentials, format='json')
        self.assertEqual(issued.status_code, 200)
        access, refresh = issued.data['access'], issued.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.client.credentials()
        renewed = self.client.post('/auth/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(renewed.status_code, 200)
        with transaction.atomic():
            locked = Credenciales.objects.select_for_update().get(pk=account.pk)
            locked.password_version = F('password_version') + 1
            locked.save(update_fields=['password_version'])
        account.refresh_from_db()
        self.assertEqual((account.password, account.tipo_usuario, account.estado), original)
        for token in (access, renewed.data['access']):
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)
        fresh = self.client.post('/auth/token/', credentials, format='json')
        self.assertEqual(fresh.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {fresh.data['access']}")
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/token/refresh/', {'refresh': fresh.data['refresh']}, format='json').status_code, 200)
