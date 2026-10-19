from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TransactionTestCase, override_settings
from .models import Credenciales, Usuario, Cargo


class AdministrativeAccountsTests(APITestCase):
    def account(self, name, role=0, state=1):
        profile = Usuario.objects.create(cedula=name, nombre_completo=name, correo=name+'@example.invalid', estado=state)
        credentials = Credenciales(usuario=name, usuario_rel=profile, tipo_usuario=role, estado=state)
        credentials.set_password('Previous@Secure937!')
        credentials.save()
        return credentials

    def setUp(self):
        self.client.defaults['REMOTE_ADDR'] = '192.0.2.91'
        self.admin = self.account('super-admin', 4)
        self.worker = self.account('worker', 3)
        self.customer = self.account('customer')
        self.inactive = self.account('inactive', state=0)
        self.client.force_authenticate(self.admin)

    def detail(self, user):
        return reverse('register-detail', kwargs={'usuario_id': user.usuario_rel_id})

    def state(self, user, value):
        return self.client.patch(reverse('cambiar-estado-usuario', kwargs={'usuario_id':user.usuario_rel_id}), {'estado':value}, format='json')

    def test_list_inactive_search_and_pagination(self):
        url = reverse('lista-usuarios')
        self.assertEqual(self.client.get(url, {'estado':'0'}).data['results'][0]['id'], self.inactive.usuario_rel_id)
        self.assertEqual(self.client.get(url, {'estado':'1'}).data['count'], 3)
        self.assertEqual(self.client.get(url, {'estado':'todos', 'search':'inactive', 'page_size':1}).data['count'], 1)
        self.assertEqual(len(self.client.get(url, {'estado':'todos', 'page':2,'page_size':2}).data['results']), 2)
        self.assertEqual(self.client.get(url, {'page':'invalid'}).status_code, 400)

    def test_create_edit_preserves_password_and_history(self):
        payload = {'usuario':'new-user','cedula':'new-doc','nombre_completo':'Nuevo Usuario',
            'correo':'new@example.invalid','password':'New@Secure7291!','confirm_password':'New@Secure7291!','tipo_usuario':3}
        result = self.client.post(reverse('register'), payload, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        account = Credenciales.objects.get(pk=result.data['usuario_id'])
        self.assertTrue(account.check_password(payload['password']))
        original_password = account.password
        cargo = Cargo.objects.create(nombrecargo='Técnico')
        edited = self.client.put(self.detail(account), {'nombre_completo':'Nombre actualizado', 'cedula':'updated-doc', 'cargo':cargo.pk, 'password':''}, format='json')
        self.assertEqual(edited.status_code, 200, edited.data)
        account.refresh_from_db()
        self.assertEqual(account.password, original_password)
        self.assertEqual(account.usuario_rel.correo, payload['correo'])
        self.assertEqual(account.usuario_rel.cargo_id, cargo.pk)
        self.assertNotIn('password', edited.data)
        duplicate = self.client.put(self.detail(account), {'cedula':self.customer.usuario_rel.cedula}, format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('cedula', duplicate.data)
        invalid = self.client.put(self.detail(account), {'location_id':999999}, format='json')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('location_id', invalid.data)

    def test_password_policy_confirmation_and_revocation(self):
        url = reverse('admin-account-password', kwargs={'usuario_id':self.worker.usuario_rel_id})
        token = RefreshToken.for_user(self.worker)
        token['password_version'] = self.worker.password_version
        for password, confirmation in [('123','123'), ('Safe@929!VeryLong','different')]:
            self.assertEqual(self.client.post(url, {'new_password':password,'confirm_password':confirmation}).status_code, 400)
        changed = self.client.post(url, {'new_password':'Better@Secure937!','confirm_password':'Better@Secure937!'})
        self.assertEqual(changed.status_code, 200, changed.data)
        self.worker.refresh_from_db()
        self.assertTrue(self.worker.check_password('Better@Secure937!'))
        client = APIClient()
        client.defaults['REMOTE_ADDR'] = '192.0.2.92'
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        self.assertEqual(client.get(reverse('perfil')).status_code, 401)
        self.assertEqual(client.post('/auth/token/refresh/', {'refresh':str(token)}).status_code, 401)

    def test_inactive_cannot_login_reactivation_requires_fresh_login(self):
        login = APIClient()
        login.defaults['REMOTE_ADDR'] = '192.0.2.93'
        credentials = {'usuario':self.customer.usuario, 'password':'Previous@Secure937!'}
        self.assertEqual(login.post('/auth/token/', credentials).status_code, 200)
        self.assertEqual(self.state(self.customer, 0).status_code, 200)
        self.assertEqual(login.post('/auth/token/', credentials).status_code, 401)
        self.assertEqual(self.state(self.customer, 1).status_code, 200)
        self.assertEqual(login.post('/auth/token/', credentials).status_code, 200)
        self.assertTrue(Usuario.objects.filter(pk=self.customer.usuario_rel_id).exists())

    def test_self_deactivation_last_superadmin_and_permissions(self):
        self.assertEqual(self.state(self.admin, 0).status_code, 400)
        self.assertEqual(self.client.patch(reverse('actualizar-rol-usuario', kwargs={'usuario_id':self.admin.usuario_rel_id}), {'tipo_usuario':0}).status_code, 400)
        self.client.force_authenticate(self.worker)
        for url, payload in [(self.detail(self.customer), {'nombre_completo':'Denied'}),
            (reverse('actualizar-rol-usuario', kwargs={'usuario_id':self.customer.usuario_rel_id}), {'tipo_usuario':4}),
            (reverse('cambiar-estado-usuario', kwargs={'usuario_id':self.customer.usuario_rel_id}), {'estado':0})]:
            self.assertEqual(self.client.patch(url, payload).status_code, 403)

    def test_batch_deactivation_is_atomic_and_cannot_remove_all_admins(self):
        other = self.account('second-admin', 4)
        url = reverse('cambiar-estado-usuario-post')
        result = self.client.post(url, {'usuario_ids':[self.customer.usuario_rel_id, self.admin.usuario_rel_id, other.usuario_rel_id], 'estado':0}, format='json')
        self.assertEqual(result.status_code, 400)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.estado, 1)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class AccountRealtimeRevocationTests(TransactionTestCase):
    def test_open_crm_socket_closes_after_password_state_or_role_revocation(self):
        from asgiref.sync import async_to_sync
        from channels.db import database_sync_to_async
        from channels.layers import get_channel_layer
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken
        from core.asgi import application
        for index, change in enumerate(({'password_version':1}, {'estado':0}, {'tipo_usuario':0})):
            account = Credenciales.objects.create(usuario=f'ws-revoke-{index}', tipo_usuario=1, estado=1)
            token = str(AccessToken.for_user(account))

            async def scenario():
                socket = WebsocketCommunicator(application, '/ws/crm-chat/', subprotocols=['crm-chat', f'jwt.{token}'])
                self.assertTrue((await socket.connect())[0])
                await database_sync_to_async(Credenciales.objects.filter(pk=account.pk).update)(**change)
                await get_channel_layer().group_send('crm_agents', {'type':'crm.event', 'payload':{'type':'message.created'}})
                event = await socket.receive_output()
                self.assertEqual(event, {'type':'websocket.close', 'code':4403})
                await socket.disconnect()
                stale = WebsocketCommunicator(application, '/ws/crm-chat/', subprotocols=['crm-chat', f'jwt.{token}'])
                self.assertFalse((await stale.connect())[0])
                await stale.disconnect()
            async_to_sync(scenario)()
