"""General development must not depend on a carrier or its credentials."""
from decimal import Decimal
from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from ecommerce.pricing import totals


class CarrierIndependenceTests(SimpleTestCase):
    def test_provider_loaded_but_disabled_by_default(self):
        self.assertIn('shipping', apps.app_configs)
        self.assertFalse(settings.TCC_SHIPPING_ENABLED)
        self.assertFalse(settings.TCC_DISPATCH_ENABLED)

    def test_products_only_at_every_purchase_amount(self):
        for subtotal in (125000,499999,500000,2900000):
            result=totals(Decimal(subtotal),taxes=2000,discounts=1000)
            self.assertEqual(result['total'],Decimal(subtotal)+1000)
            self.assertIsNone(result['shipping_cost'])
