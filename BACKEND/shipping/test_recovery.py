"""Recovery regressions: current checkout persistence plus simulated carrier."""
from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from ecommerce.models import UserAddress, WompiPaymentIntent, Order
from . import tests as fixtures
from .tcc import TCCClient


@override_settings(**fixtures.TEST_SETTINGS)
class RecoveryTests(APITestCase):
    setUp = fixtures.TCCFlowTests.setUp
    carrier = fixtures.TCCFlowTests.carrier
    quote = fixtures.TCCFlowTests.quote
    webhook = fixtures.TCCFlowTests.webhook

    def test_previous_dev_address_model_can_still_write(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        old_apps = MigrationExecutor(connection).loader.project_state(
            [('ecommerce', '0018_delivery_without_shipping')]).apps
        OldAddress = old_apps.get_model('ecommerce', 'UserAddress')
        old = OldAddress.objects.create(user_id=self.user.pk, label='Old client',
            recipient_name='QA', phone='3000000000', address='Synthetic', city='Cali', department='Valle')
        self.assertEqual(UserAddress.objects.get(pk=old.pk).tcc_city_code, '')

    def test_saved_address_survives_draft_payment_and_retry(self):
        address = UserAddress.objects.create(user=self.user, label='QA', recipient_name='Saved recipient',
            phone='3000000000', address='Saved street', city=self.payload['city'],
            department=self.payload['department'], tcc_city_code=self.payload['tcc_city_code'],
            neighborhood='Saved neighborhood', delivery_instructions='Saved instructions', is_default=True)
        payload = {**self.payload, 'address_id':address.pk}
        quote = self.quote(payload)
        payload['shipping_quote_id'] = str(quote.pk)
        first = self.client.post(reverse('order-list'), payload, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        retry = self.client.post(reverse('order-list'), payload, format='json')
        self.assertEqual(retry.status_code, 200, retry.data)
        intent = WompiPaymentIntent.objects.get()
        self.assertEqual(intent.order.delivery_address_id, address.pk)
        self.assertEqual(intent.order.delivery_details['neighborhood'], 'Saved neighborhood')
        self.assertEqual(intent.order.shipping_address, 'Saved street')
        self.assertEqual(intent.total, 155000)
        self.assertEqual(self.webhook(intent).status_code, 200)
        self.assertEqual(self.webhook(intent).status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        address.delete()
        intent.order.refresh_from_db()
        self.assertIsNone(intent.order.delivery_address_id)
        self.assertEqual(intent.order.delivery_details['delivery_instructions'], 'Saved instructions')

    def test_sandbox_alias_and_missing_account(self):
        with override_settings(TCC_API_ENVIRONMENT='sandbox'):
            self.assertEqual(TCCClient().base, 'https://testsomos.tcc.com.co')
        with override_settings(TCC_MSJ_ACCOUNT=''):
            response = self.client.post(reverse('shipping-quote'), self.payload, format='json')
        self.assertEqual(response.status_code, 503)
        self.http.assert_not_called()

    def test_legacy_product_edit_without_logistics_does_not_invent_profile(self):
        self.profile.delete()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse('product-detail', args=[self.product.pk]),
            {'description':'Updated safely'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 125000)
        self.assertFalse(self.product.shipping_ready)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(reverse('shipping-quote'), self.payload, format='json').status_code, 400)
        self.http.assert_not_called()
