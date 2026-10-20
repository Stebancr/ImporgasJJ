"""General development must not depend on a carrier or its credentials."""
from decimal import Decimal
from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from ecommerce.pricing import totals
from ecommerce.views import SHIPPING_COST, SHIPPING_THRESHOLD


class CarrierIndependenceTests(SimpleTestCase):
    def test_no_provider_application_or_configuration_loaded(self):
        self.assertNotIn('shipping', apps.app_configs)
        self.assertFalse(any(name.startswith('TCC_') for name in dir(settings)))
        for path in ('/api/shipping/config', '/ecommerce/shipping/quotes', '/api/ecommerce/shipping/cities'):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)

    def test_explicit_legacy_tariff_is_not_a_failed_quote_fallback(self):
        self.assertEqual(SHIPPING_COST, 25000)
        self.assertEqual(SHIPPING_THRESHOLD, 500000)
        for subtotal, expected in ((125000, 150000), (499999, 524999), (500000, 500000)):
            shipping = 0 if subtotal >= SHIPPING_THRESHOLD else SHIPPING_COST
            self.assertEqual(totals(Decimal(subtotal), shipping)['total'], Decimal(expected))
