from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from rest_framework.test import APITestCase

from usuarios.models import Credenciales

from .models import Brand, Category, Location, Product
from .serializers import LocationSerializer


class StoreCategoriesAndNorthPinTests(APITestCase):
    def test_catalog_upgrade_preserves_existing_alias_and_api_metadata(self):
        migration = import_module('ecommerce.migrations.0022_store_categories')
        Category.objects.filter(slug='manometro').delete()
        existing = Category.objects.create(name='MANÓMETROS', slug='presion-historica', icon='gauge', order=70)
        for _ in range(2):
            migration.add_categories(apps, SimpleNamespace(connection=connection))
        self.assertFalse(Category.objects.filter(slug='manometro').exists())
        self.assertEqual(Category.objects.get(slug='presion-historica').pk, existing.pk)
        response = self.client.get('/products', {'per_page': 1})
        self.assertEqual(response.status_code, 200)
        categories = {item['slug']: item['icon'] for item in response.data['categories']}
        for _, slug, icon, _ in migration.CATEGORIES:
            if slug != 'manometro':
                self.assertEqual(Category.objects.filter(slug=slug).count(), 1)
                self.assertEqual(categories[slug], icon)

    def test_north_pin_targets_production_name_and_preserves_south(self):
        north = Location.objects.create(name='SEDE CALI NORTE', address='Av 6 N #30N 42 San Vicente', city='Cali')
        south = Location.objects.create(name='SEDE CALI SUR', address='Cll 10 # 65a-75 local 809', city='Cali')
        migration = import_module('ecommerce.migrations.0023_north_location_pin')
        migration.identify_north(apps, SimpleNamespace(connection=connection))
        north.refresh_from_db()
        south.refresh_from_db()
        data = LocationSerializer(north).data
        self.assertIn('#30N-46', data['address'])
        self.assertEqual((data['latitude'], data['longitude']), ('3.4718433', '-76.5266492'))
        self.assertEqual(data['google_place_id'], 'ChIJXf6b2uupMI4RNN6J4-rm_jo')
        self.assertEqual(south.address, 'Cll 10 # 65a-75 local 809')
        self.assertIsNone(south.latitude)
        self.assertFalse(LocationSerializer(north, data={'latitude': '91'}, partial=True).is_valid())
        self.assertFalse(LocationSerializer(south, data={'latitude': '4'}, partial=True).is_valid())

    def test_admin_can_reassign_and_public_catalog_filters_by_id(self):
        original = Category.objects.create(name='Histórica')
        target = Category.objects.get(slug='electricidad')
        brand = Brand.objects.create(name='Marca de prueba')
        product = Product.objects.create(name='Válvula de prueba', category=original, brand=brand, price=45000)
        admin = Credenciales.objects.create(usuario='qa-catalog', estado=1, tipo_usuario=4)
        self.client.force_authenticate(admin)
        response = self.client.patch(f'/products/{product.pk}', {'category': target.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.category_id, target.pk)
        self.assertEqual(product.price, 45000)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/products', {'category_id': target.pk}).data['total'], 1)
        self.assertEqual(self.client.get('/products', {'category_id': original.pk}).data['total'], 0)
