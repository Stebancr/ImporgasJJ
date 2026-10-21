from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase
from unittest import skipUnless
from usuarios.models import Credenciales
from ecommerce.models import UserAddress



def payload():
    return dict(label='Casa QA', recipient_name='Persona QA', phone='3000000000',
                address='Calle sintética 123', city='Cali', department='Valle del Cauca',
                neighborhood='Barrio QA', is_default=False)


class DeliveryAddressTests(APITestCase):
    def setUp(self):
        self.user = Credenciales.objects.create(usuario='address-qa', estado=1, tipo_usuario=0)
        self.other = Credenciales.objects.create(usuario='other-address-qa', estado=1, tipo_usuario=0)
        self.client.force_authenticate(self.user)
        self.url = '/ecommerce/user/addresses'

    def test_repeated_create_default_edit_and_ownership(self):
        self.assertEqual(self.client.post(self.url, {**payload(), 'phone':'-------'}, format='json').status_code, 400)
        first = self.client.post(self.url, payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)
        pk = first.data['data']['id']
        self.assertTrue(first.data['data']['is_default'])
        duplicate = self.client.post(self.url, {**payload(), 'label':'Otra etiqueta', 'address':'  CALLE sintética 123  '}, format='json')
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.data['data']['id'], pk)
        self.assertEqual(UserAddress.objects.count(), 1)
        second = self.client.post(self.url, {**payload(), 'address':'Otra calle QA', 'is_default':True}, format='json')
        other_pk = second.data['data']['id']
        self.assertEqual(UserAddress.objects.filter(is_default=True).count(), 1)
        self.assertEqual(self.client.put(f'{self.url}/{pk}', {'is_default':True}, format='json').status_code, 200)
        self.assertTrue(UserAddress.objects.get(pk=pk).is_default)
        self.assertEqual(self.client.put(f'{self.url}/{other_pk}', {'address':payload()['address']}, format='json').status_code, 400)
        self.assertEqual(self.client.put(f'{self.url}/{pk}', {'city':''}, format='json').status_code, 400)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).data['data'], [])
        self.assertEqual(self.client.put(f'{self.url}/{pk}', {'is_default':True}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'{self.url}/{pk}').status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f'{self.url}/{other_pk}').status_code, 204)
        self.assertEqual(UserAddress.objects.count(), 1)


@skipUnless(connection.vendor == 'postgresql', 'Verify concurrent retries in PostgreSQL.')
class ConcurrentAddressTests(TransactionTestCase):
    def test_retries_create_one_address(self):
        user = Credenciales.objects.create(usuario='concurrent-address-qa', estado=1, tipo_usuario=0)
        barrier = Barrier(2)
        def create():
            close_old_connections()
            try:
                client = APIClient(); client.force_authenticate(user)
                barrier.wait(timeout=10)
                response = client.post('/ecommerce/user/addresses', payload(), format='json')
                return response.status_code, response.data['data']['id']
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(create) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(code for code, _ in results), [200, 201])
        self.assertEqual(len({pk for _, pk in results}), 1)
        self.assertEqual(UserAddress.objects.count(), 1)
