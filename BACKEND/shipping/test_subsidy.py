"""Promotion accounting through persisted quotes, Wompi and duplicate webhooks."""
from decimal import Decimal
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from ecommerce.models import UserAddress, Order
from .tests import TCCFlowTests, TEST_SETTINGS
from .policy import shipping_policy


@override_settings(FREE_SHIPPING_THRESHOLD='2000000')
class SubsidyPolicyTests(SimpleTestCase):
    def test_inclusive_boundary_and_product_discounts(self):
        for subtotal, discounts, applied, charge, subsidy, remaining in [
            ('1999999', 0, False, '35000.00', '0.00', '1.00'),
            ('2000000', 0, True, '0.00', '35000.00', '0.00'),
            ('2100000', 0, True, '0.00', '35000.00', '0.00'),
            ('2100000', '100001', False, '35000.00', '0.00', '1.00'),
        ]:
            with self.subTest(subtotal=subtotal, discounts=discounts):
                result = shipping_policy(subtotal, '35000', discounts=discounts)
                self.assertEqual(result['free_shipping_applied'], applied)
                self.assertEqual(result['carrier_shipping_cost'], '35000.00')
                self.assertEqual(result['customer_shipping_charge'], charge)
                self.assertEqual(result['shipping_discount'], subsidy)
                self.assertEqual(result['amount_to_free_shipping'], remaining)

    def test_no_false_promotion_for_nonshipping_or_zero_rate(self):
        self.assertFalse(shipping_policy('3000000', 0)['free_shipping_applied'])
        self.assertFalse(shipping_policy('3000000', '35000', requires_shipping=False)['free_shipping_applied'])

    @override_settings(FREE_SHIPPING_THRESHOLD='2500000')
    def test_threshold_is_server_configuration(self):
        self.assertFalse(shipping_policy('2000000', '35000')['free_shipping_applied'])


@override_settings(**TEST_SETTINGS, FREE_SHIPPING_THRESHOLD='2000000')
class SubsidyFlowTests(APITestCase):
    setUp = TCCFlowTests.setUp
    carrier = TCCFlowTests.carrier
    quote = TCCFlowTests.quote
    intent = TCCFlowTests.intent
    webhook = TCCFlowTests.webhook

    def test_threshold_payment_preserves_carrier_and_subsidy_and_is_idempotent(self):
        self.product.price = Decimal('2000000'); self.product.save()
        intent = self.intent()
        self.assertEqual(intent.total, Decimal('2000000'))
        self.assertEqual(intent.shipping_cost, 0)
        order = intent.order
        self.assertEqual(order.carrier_shipping_cost, Decimal(self.rate))
        self.assertEqual(order.shipping_discount, Decimal(self.rate))
        self.assertTrue(order.free_shipping_applied)
        self.assertEqual(order.free_shipping_threshold, Decimal('2000000'))
        self.assertEqual(self.webhook(intent).status_code, 200)
        self.assertEqual(self.webhook(intent).status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.enqueue.call_count, 1)
        self.assertEqual(self.dispatch_calls, 0)
        order.refresh_from_db(); self.assertEqual(order.paid_total, Decimal('2000000'))
        from .tasks import create_shipment
        create_shipment.run(order.shipment.pk)
        create_shipment.run(order.shipment.pk)
        self.assertEqual(self.dispatch_calls, 1)

    def test_below_threshold_customer_pays_real_rate(self):
        self.product.price = Decimal('1999999'); self.product.save()
        intent = self.intent()
        self.assertEqual(intent.total, Decimal('2029999'))
        self.assertEqual(intent.order.shipping_discount, 0)
        self.assertFalse(intent.order.free_shipping_applied)
        self.assertEqual(intent.order.carrier_shipping_cost, intent.shipping_cost)

    def test_rate_changes_even_when_customer_shipping_is_free_require_requote(self):
        self.product.price = Decimal('2100000'); self.product.save()
        quote = self.quote()
        self.rate = '35000.00'
        response = self.client.post(reverse('order-list'), {**self.payload, 'shipping_quote_id': str(quote.pk)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_quantity_change_invalidates_promotion_quote(self):
        self.product.price = Decimal('1100000'); self.product.save()
        quote = self.quote()
        self.cart.quantity = 2; self.cart.save()
        self.payload['items'][0]['quantity'] = 2
        response = self.client.post(reverse('order-list'), {**self.payload, 'shipping_quote_id': str(quote.pk)}, format='json')
        self.assertEqual(response.status_code, 400)
        replacement = self.quote()
        self.assertTrue(replacement.snapshot['shipping_policy']['free_shipping_applied'])
        self.assertEqual(replacement.tcc_rate, Decimal(self.rate))

    def test_signed_in_estimate_requires_a_saved_address(self):
        response = self.client.post(reverse('shipping-estimate'), {'items': self.payload['items'], 'tcc_city_code': '76001000'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.http.assert_not_called()

    def test_progress_uses_server_prices_without_granting_free_delivery(self):
        self.client.force_authenticate(None)
        response = self.client.post(reverse('shipping-promotion'), {'items': self.payload['items'], 'subtotal': 2000000}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['eligible_subtotal'], '125000.00')
        self.assertEqual(response.data['amount_to_free_shipping'], '1875000.00')
        self.assertNotIn('free_shipping_applied', response.data)
        self.http.assert_not_called()

    def test_malformed_progress_payloads_return_validation_errors(self):
        for payload in ([], {}, {'items': []}, {'items': [{'product_id': self.product.pk, 'quantity': -1}]}):
            self.assertEqual(self.client.post(reverse('shipping-promotion'), payload, format='json').status_code, 400)
        self.http.assert_not_called()

    def test_guest_estimate_promotion_does_not_create_an_address_or_order(self):
        self.product.price = Decimal('2000000'); self.product.save()
        self.client.force_authenticate(None)
        response = self.client.post(reverse('shipping-estimate'), {'items': self.payload['items'], 'tcc_city_code': '76001000', 'total': 1}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['tcc_rate'], '30000.00')
        self.assertEqual(response.data['total'], '0.00')
        self.assertEqual(response.data['order_total'], '2000000.00')
        self.assertTrue(response.data['free_shipping_applied'])
        self.assertFalse(UserAddress.objects.exists()); self.assertFalse(Order.objects.exists())

    def test_threshold_change_invalidates_cached_quote(self):
        self.product.price = Decimal('2100000'); self.product.save()
        quote = self.quote()
        with override_settings(FREE_SHIPPING_THRESHOLD='3000000'):
            response = self.client.post(reverse('order-list'), {**self.payload, 'shipping_quote_id': str(quote.pk)}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertFalse(self.quote().snapshot['shipping_policy']['free_shipping_applied'])
