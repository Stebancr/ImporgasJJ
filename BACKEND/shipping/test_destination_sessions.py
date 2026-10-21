from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from ecommerce.models import UserAddress, Order
from usuarios.models import Credenciales
from . import tests as fixtures


@override_settings(**fixtures.TEST_SETTINGS)
class DestinationSessionTests(APITestCase):
    setUp=fixtures.TCCFlowTests.setUp
    carrier=fixtures.TCCFlowTests.carrier

    def address(self,user=None):
        return UserAddress.objects.create(user=user or self.user,label='Synthetic',recipient_name='QA',
            phone='3000000000',address='Private synthetic street',city='CALI',department='VALLE DEL CAUCA',
            tcc_city_code='76001000',is_default=True)

    def estimate(self,**destination):
        return self.client.post(reverse('shipping-estimate'),{'items':self.payload['items'],**destination},format='json')

    def test_anonymous_municipality_needs_no_address_or_account(self):
        self.client.force_authenticate(None)
        response=self.estimate(tcc_city_code='76001000')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.data['approximate'])
        self.assertFalse(UserAddress.objects.exists())
        self.assertFalse(Order.objects.exists())

    def test_anonymous_cannot_use_private_address_id(self):
        address=self.address()
        self.client.force_authenticate(None)
        self.assertEqual(self.estimate(address_id=address.pk).status_code,401)
        self.http.assert_not_called()

    def test_other_accounts_address_is_not_disclosed(self):
        other=Credenciales.objects.create(usuario='destination-other-qa',estado=1,tipo_usuario=0)
        address=self.address(other)
        response=self.estimate(address_id=address.pk)
        self.assertEqual(response.status_code,404)
        self.assertNotIn(address.address,str(response.data))
        self.http.assert_not_called()

    def test_saved_address_overrides_browser_city_and_reveals_no_pii(self):
        address=self.address()
        response=self.estimate(address_id=address.pk,tcc_city_code='11001000',price=1,shipping_cost=1)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.http.call_args.kwargs['json']['idciudaddestino'],'76001000')
        self.assertEqual(response.data['order_total'],'155000.00')
        self.assertNotIn(address.address,str(response.data))
        address.refresh_from_db();self.assertTrue(address.is_default)

    def test_estimate_cache_is_scoped_to_account(self):
        self.assertEqual(self.estimate(tcc_city_code='76001000').status_code,200)
        self.assertEqual(self.estimate(tcc_city_code='76001000').status_code,200)
        self.assertEqual(self.http.call_count,1)
        other=Credenciales.objects.create(usuario='destination-cache-qa',estado=1,tipo_usuario=0)
        self.client.force_authenticate(other)
        self.assertEqual(self.estimate(tcc_city_code='76001000').status_code,200)
        self.assertEqual(self.http.call_count,2)

    def test_expired_session_is_not_treated_as_an_empty_address_list(self):
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-synthetic-token')
        self.assertEqual(self.estimate(tcc_city_code='76001000').status_code,401)
        self.http.assert_not_called()

    def test_legacy_address_names_resolve_without_rewriting_it(self):
        address=self.address()
        address.tcc_city_code='';address.city='Cali';address.department='Valle del Cauca';address.save()
        response=self.estimate(address_id=address.pk)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.http.call_args.kwargs['json']['idciudaddestino'],'76001000')
        address.refresh_from_db();self.assertEqual(address.tcc_city_code,'')
        final=self.client.post(reverse('shipping-quote'),{'items':self.payload['items'],
            'address_id':address.pk,'customer_email':'qa@example.invalid'},format='json')
        self.assertEqual(final.status_code,200,final.data)
        self.assertFalse(final.data['approximate'])

    def test_ambiguous_legacy_destination_needs_manual_selection(self):
        address=self.address();address.tcc_city_code='';address.city='Unknown QA';address.save()
        self.assertEqual(self.estimate(address_id=address.pk).status_code,400)
        self.http.assert_not_called()
