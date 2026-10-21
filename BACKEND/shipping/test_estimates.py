from decimal import Decimal
from unittest.mock import Mock
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from ecommerce.models import Order, WompiPaymentIntent, Product
from ecommerce.pricing import totals
from .models import ShippingQuote, ProductShippingProfile
from . import tests as fixtures
from .catalog import city
from .tcc import TCCClient, TCCError


@override_settings(**fixtures.TEST_SETTINGS)
class EstimateAndPricingTests(APITestCase):
    setUp = fixtures.TCCFlowTests.setUp
    carrier = fixtures.TCCFlowTests.carrier
    quote = fixtures.TCCFlowTests.quote
    intent = fixtures.TCCFlowTests.intent
    webhook = fixtures.TCCFlowTests.webhook

    def test_last_destination_is_private_and_normalized(self):
        self.quote()
        response = self.client.get(reverse('shipping-destination'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['destination']['code'], self.payload['tcc_city_code'])
        self.assertNotIn('phone', str(response.data))
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(reverse('shipping-destination')).status_code, (401,403))

    def test_anonymous_estimate_uses_product_and_city_without_creating_orders(self):
        self.client.force_authenticate(None)
        payload = {'items': self.payload['items'], 'tcc_city_code': '76001000',
                   'shipping_cost': 1, 'total': 1, 'customer_phone': 'not-stored'}
        response = self.client.post(reverse('shipping-estimate'), payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['total'], '30000.00')
        self.assertEqual(response.data['order_total'], '155000.00')
        self.assertEqual(response.data['destination']['city'], city('76001000')['city'])
        self.assertTrue(response.data['approximate'])
        self.assertIsNone(response.data['estimated_delivery'])
        self.assertNotIn('id', response.data)
        self.assertNotIn('not-stored', str(response.data))
        self.assertFalse(ShippingQuote.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(WompiPaymentIntent.objects.exists())
        self.assertEqual(self.http.call_args.kwargs['json']['idunidadnegocio'], 2)

    def test_latest_purchase_destination_can_replace_an_older_quote(self):
        self.quote()
        Order.objects.create(user=self.user, total=125000,
            delivery_details={'tcc_city_code': '76001000', 'customer_phone': 'private-not-returned'})
        response = self.client.get(reverse('shipping-destination'))
        self.assertEqual(response.data['destination']['code'], '76001000')
        self.assertNotIn('private-not-returned', str(response.data))

    def test_destination_skips_invalid_history_and_never_uses_another_customer(self):
        Order.objects.create(user=self.user, total=125000, delivery_details={'tcc_city_code': '76001000'})
        Order.objects.create(user=self.user, total=125000, delivery_details={'tcc_city_code': 'invalid'})
        Order.objects.create(user=self.admin, total=125000, delivery_details={'tcc_city_code': '11001000'})
        response = self.client.get(reverse('shipping-destination'))
        self.assertEqual(response.data['destination']['code'], '76001000')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_estimate_invalidates_on_quantity_city_and_logistics_changes(self):
        self.client.force_authenticate(None)
        payload = {'items': self.payload['items'], 'tcc_city_code': '11001000'}
        def estimate(data):
            response = self.client.post(reverse('shipping-estimate'), data, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            return response.data
        estimate(payload); estimate(payload)
        self.assertEqual(self.http.call_count, 1)
        updated = estimate({**payload, 'items': [{'product_id': self.product.pk, 'quantity': 3}]})
        self.assertEqual(updated['real_kg'], '6.000')
        self.assertEqual(self.http.call_args.kwargs['json']['idunidadnegocio'], 1)
        estimate({**payload, 'tcc_city_code': '76001000'})
        self.profile.height_cm = 20; self.profile.save()
        estimate(payload)
        self.assertEqual(self.http.call_count, 4)

    def test_incomplete_product_and_unknown_geography_are_blocked(self):
        self.client.force_authenticate(None)
        payload = {'items': self.payload['items'], 'tcc_city_code': 'invalid'}
        self.assertEqual(self.client.post(reverse('shipping-estimate'), payload, format='json').status_code, 400)
        self.profile.weight_kg = None; self.profile.save()
        payload['tcc_city_code'] = '76001000'
        response=self.client.post(reverse('shipping-estimate'), payload, format='json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data['status'],'incomplete')
        self.assertIn('Peso',response.data['missing_fields'])
        self.assertFalse(Product.objects.get(pk=self.product.pk).shipping_ready)
        self.http.assert_not_called()

    def test_missing_profile_returns_actionable_error_without_carrier_request(self):
        self.client.force_authenticate(None)
        self.profile.delete()
        response=self.client.post(reverse('shipping-estimate'), {'items': self.payload['items'], 'tcc_city_code':'76001000'}, format='json')
        self.assertEqual(response.status_code,422)
        self.assertEqual(response.data['code'],'shipping_profile_incomplete')
        self.assertFalse(response.data['can_quote'])
        self.assertIn('Valor declarado',response.data['missing_fields'])
        self.assertNotIn('items',response.data)
        self.http.assert_not_called()

    def test_quote_metadata_and_accounting_survive_verified_duplicate_payment(self):
        quote = self.quote()
        self.assertEqual(quote.provider_summary, {'codigoResultado': '0', 'totaldespacho': '30000.00'})
        payload = {**self.payload, 'shipping_quote_id': str(quote.pk), 'price': 1,
                   'total': 1, 'shipping_cost': 0, 'taxes': -100, 'discounts': 999999}
        response = self.client.post(reverse('order-list'), payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        intent = WompiPaymentIntent.objects.get(reference=payload['wompi_reference'])
        self.assertEqual((intent.subtotal, intent.shipping_cost, intent.taxes, intent.discounts, intent.total),
                         (Decimal(125000), Decimal(30000), Decimal(0), Decimal(0), Decimal(155000)))
        self.assertIsNone(intent.order.paid_total)
        self.assertEqual(self.webhook(intent).status_code, 200)
        self.assertEqual(self.webhook(intent).status_code, 200)
        order = Order.objects.get(pk=intent.order_id)
        self.assertEqual(order.paid_total, order.subtotal+order.shipping_cost+order.taxes-order.discounts)
        self.assertEqual(order.paid_total, Decimal(155000))
        self.assertEqual(Order.objects.count(), 1)

    def test_corrupted_stored_breakdown_rejects_payment(self):
        intent = self.intent()
        WompiPaymentIntent.objects.filter(pk=intent.pk).update(taxes=100)
        self.assertEqual(self.webhook(intent).status_code, 400)
        intent.refresh_from_db()
        self.assertIsNone(intent.processed_at)
        self.assertEqual(self.dispatch_calls, 0)

    def test_public_estimate_cannot_be_used_as_checkout_quote(self):
        self.client.post(reverse('shipping-estimate'), {'items': self.payload['items'], 'tcc_city_code': '76001000'}, format='json')
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_provider_credentials_and_nonofficial_base_fail_safely(self):
        self.client.force_authenticate(None)
        with override_settings(TCC_DEVELOPMENT_BASE_URL='https://internal.invalid'):
            with self.assertRaises(TCCError): TCCClient()
        self.http.side_effect = None
        self.http.return_value = Mock(status_code=403)
        response = self.client.post(reverse('shipping-estimate'), {'items': self.payload['items'], 'tcc_city_code': '76001000'}, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['code'], 'carrier_authentication')
        self.assertNotIn('synthetic-tcc-test-secret', str(response.data))


class PricingArithmeticTests(SimpleTestCase):
    def test_tax_and_discount_are_separate_and_total_is_exact(self):
        self.assertEqual(totals('100000.10', '20000.20', taxes='19000.03', discounts='5000.01'),
            {'subtotal': Decimal('100000.10'), 'shipping_cost': Decimal('20000.20'),
             'taxes': Decimal('19000.03'), 'discounts': Decimal('5000.01'), 'total': Decimal('134000.32')})
        for changes in ({'taxes': -1}, {'discounts': 200000}, {'taxes': 'NaN'}):
            with self.assertRaises(ValueError): totals(100000, 10000, **changes)
