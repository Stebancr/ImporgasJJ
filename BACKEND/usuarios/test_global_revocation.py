import io
import json
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.contrib.sessions.models import Session
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from auth.serializers import TokenLMSSerializer
from auth.session_security import current_version
from usuarios.models import Credenciales, Usuario, AuthSession, GlobalAuthState, AuthRevocation


class GlobalRevocationTests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(cedula='epoch-fixture', nombre_completo='Synthetic QA', correo='epoch@example.invalid')
        self.user = Credenciales.objects.create(usuario='epoch-fixture', usuario_rel=profile, tipo_usuario=4, estado=1)
        self.user.set_password('Synthetic@Epoch937!')
        self.user.save()
        self.pair = TokenLMSSerializer.get_token(self.user)
        self.access = str(self.pair.access_token)
        self.credentials = {'usuario': self.user.usuario, 'password': 'Synthetic@Epoch937!'}
        self.original = (self.user.password, self.user.tipo_usuario, self.user.estado, self.user.usuario_rel_id)
        self.client.defaults['REMOTE_ADDR'] = '192.0.2.140'

    def authorize(self, token=None):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + (token or self.access))

    def revoke(self, operation='synthetic-release'):
        output = io.StringIO()
        call_command('revoke_all_sessions', reason='test_release', operation_id=operation, actor_id=self.user.pk, stdout=output)
        self.assertNotIn(self.access, output.getvalue())
        self.assertNotIn(self.user.usuario, output.getvalue())
        return json.loads(output.getvalue())

    def test_global_access_refresh_revocation_and_same_password_login(self):
        self.authorize()
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/token/refresh/', {'refresh': str(self.pair)}).status_code, 200)
        result = self.revoke()
        self.assertEqual(result['global_auth_version'], 2)
        self.authorize()
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/token/refresh/', {'refresh': str(self.pair)}).status_code, 401)
        login = self.client.post('/auth/token/', self.credentials)
        self.assertEqual(login.status_code, 200)
        self.authorize(login.data['access'])
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual((self.user.password, self.user.tipo_usuario, self.user.estado, self.user.usuario_rel_id), self.original)

    def test_legacy_and_missing_individual_version_are_rejected(self):
        legacy = RefreshToken.for_user(self.user)
        self.authorize(str(legacy.access_token))
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        del self.pair['password_version']
        self.authorize(str(self.pair.access_token))
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)

    def test_idempotent_operation_and_new_independent_operation(self):
        self.assertEqual(self.revoke(), self.revoke())
        self.assertEqual(current_version(), 2)
        self.assertEqual(AuthRevocation.objects.count(), 1)
        self.assertEqual(self.revoke('second-release')['global_auth_version'], 3)

    def test_drf_legacy_rejected_new_issue_revoked_and_rotated(self):
        legacy = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {legacy.key}')
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.authorize()
        issued = self.client.post('/auth/personal-token/')
        self.assertEqual(issued.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {issued.data['token']}")
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        result = self.revoke()
        self.assertEqual(result['drf_tokens_revoked'], 1)
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.assertEqual(Token.objects.count(), 0)

    def test_django_session_and_historical_session(self):
        session_client = APIClient()
        session_client.force_login(self.user)
        self.assertEqual(session_client.get(reverse('perfil')).status_code, 200)
        self.revoke()
        self.assertEqual(session_client.get(reverse('perfil')).status_code, 401)
        session_client.force_login(self.user)
        self.assertEqual(session_client.get(reverse('perfil')).status_code, 200)
        session = session_client.session
        del session['global_auth_version']
        session.save()
        self.assertEqual(session_client.get(reverse('perfil')).status_code, 401)

    def test_logout_invalidates_refresh_and_access(self):
        self.authorize()
        self.assertEqual(self.client.post('/auth/logout/').status_code, 204)
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/token/refresh/', {'refresh': str(self.pair)}).status_code, 401)

    def test_individual_version_and_inactive_accounts(self):
        Credenciales.objects.filter(pk=self.user.pk).update(password_version=1)
        self.authorize()
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 401)
        self.client.credentials()
        Credenciales.objects.filter(pk=self.user.pk).update(estado=0)
        self.assertEqual(self.client.post('/auth/token/', self.credentials).status_code, 401)

    def test_gateway_introspection_and_revocation(self):
        from django.test import override_settings
        from crmChat.apps.whatsapp_web.auth import signed_headers
        with override_settings(CRM_INTERNAL_SERVICE_TOKEN='synthetic-transport-' * 4):
            self.authorize()
            response = self.client.post('/crm-chat/whatsapp-web/realtime-token/')
            self.assertEqual(response.status_code, 200)
            body = json.dumps({'token': response.data['token']}).encode()
            headers = signed_headers(body)
            internal = APIClient()
            validate = lambda: internal.post('/internal/whatsapp/realtime/validate/', body, content_type='application/json',
                **{'HTTP_' + k.upper().replace('-', '_'): v for k, v in signed_headers(body).items()})
            self.assertTrue(validate().data['valid'])
            self.revoke()
            self.assertFalse(validate().data['valid'])

    def test_other_users_passwords_and_profiles_unchanged(self):
        other = Credenciales.objects.create(usuario='other-synthetic', password='unusable-fixture', tipo_usuario=0)
        before = list(Credenciales.objects.order_by('pk').values())
        profiles = list(Usuario.objects.order_by('pk').values())
        self.revoke()
        self.assertEqual(before, list(Credenciales.objects.order_by('pk').values()))
        self.assertEqual(profiles, list(Usuario.objects.order_by('pk').values()))
        profile = Usuario.objects.create(cedula='new-epoch-fixture', nombre_completo='Synthetic new account')
        new = Credenciales.objects.create(usuario='post-release-user', estado=1, usuario_rel=profile)
        new.set_password('Synthetic@NewEpoch937!')
        new.save()
        fresh = TokenLMSSerializer.get_token(new)
        self.authorize(str(fresh.access_token))
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
