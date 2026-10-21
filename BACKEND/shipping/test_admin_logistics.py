from decimal import Decimal
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from ecommerce.models import Product, Brand, Category
from .models import ProductShippingProfile


@override_settings(TCC_SHIPPING_ENABLED=False)
class LogisticsListingTests(APITestCase):
    def setUp(self):
        brand = Brand.objects.create(name='Synthetic logistics')
        category = Category.objects.create(name='Synthetic logistics')
        self.old = Product.objects.create(name='Legacy QA', price=125000, brand=brand, category=category)
        self.ready = Product.objects.create(name='Complete QA', price=125000, brand=brand, category=category)
        self.profile = ProductShippingProfile.objects.create(product=self.ready, weight_kg=2,
            height_cm=10, width_cm=10, length_cm=10, declared_value_from_price=True)

    def test_missing_fields_visible_without_enabled_carrier(self):
        response = self.client.get(reverse('product-list'), {'shipping_status': 'incomplete'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 1)
        item = response.data['data'][0]
        self.assertEqual(item['id'], self.old.pk)
        self.assertIn('Peso', item['shipping_missing_fields'])
        self.assertFalse(item['shipping_ready'])

    def test_filter_search_and_pagination_use_full_queryset(self):
        response = self.client.get(reverse('product-list'), {'shipping_status': 'complete', 'search': 'QA', 'per_page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['data'][0]['id'], self.ready.pk)
        self.assertEqual(response.data['data'][0]['shipping_missing_fields'], [])

    def test_insufficient_price_per_package_is_incomplete(self):
        self.ready.price = Decimal('0.01')
        self.ready.save()
        self.profile.packages_per_unit = 2
        self.profile.save()
        response = self.client.get(reverse('product-list'), {'shipping_status': 'complete'})
        self.assertEqual(response.data['total'], 0)
        self.assertFalse(self.ready.shipping_ready)

    def test_non_shipping_profile_needs_no_invented_dimensions(self):
        ProductShippingProfile.objects.create(product=self.old, requires_shipping=False)
        self.assertTrue(self.old.shipping_ready)
        self.assertEqual(self.old.shipping_missing_fields, [])

    def test_public_config_and_catalog_ignore_stale_authentication(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-synthetic-token')
        response=self.client.get(reverse('shipping-config'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['status'],'disabled')
        self.assertFalse(response.data['can_quote'])
        self.assertEqual(self.client.get(reverse('shipping-cities')).status_code,200)

    def test_empty_catalog_is_valid(self):
        from unittest.mock import patch
        with patch('shipping.views.cities',return_value=[]):
            response=self.client.get(reverse('shipping-cities'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data,[])

    @override_settings(TCC_SHIPPING_ENABLED=True)
    def test_unknown_product_is_404_not_provider_failure(self):
        response=self.client.post(reverse('shipping-estimate'),
            {'items':[{'product_id':999999,'quantity':1}],'tcc_city_code':'76001000'},format='json')
        self.assertEqual(response.status_code,404)
        self.assertEqual(response.data['status'],'not_found')
