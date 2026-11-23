from django.test import TestCase
from rest_framework.test import APITestCase
from usuarios.models import Credenciales
from .models import Brand, Category, Product
from .category_icons import ICON_KEYS


class CategoryIconSelectionTests(APITestCase):
    def setUp(self):
        self.admin = Credenciales.objects.create(usuario='icon-admin', tipo_usuario=4, estado=1)
        self.client.force_authenticate(self.admin)
        self.category = Category.objects.create(name='Categoría histórica QA', slug='categoria-historica-qa', icon='flame', order=55)
        self.product = Product.objects.create(name='Producto histórico QA', price=123456, category=self.category,
            brand=Brand.objects.create(name='Marca histórica QA'))

    def test_change_icon_persists_and_public_metadata_matches_without_other_changes(self):
        before = (self.product.category_id, self.product.price, self.category.slug, self.category.order)
        response = self.client.patch(f'/categories/{self.category.pk}', {'icon_key': 'valve'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.category.refresh_from_db()
        self.assertEqual(self.category.icon_key, 'valve')
        self.assertEqual(self.category.icon, 'flame')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/categories/{self.category.pk}').data['data']['icon_key'], 'valve')
        metadata = self.client.get('/products').data['categories']
        self.assertEqual(next(row for row in metadata if row['id'] == self.category.pk)['icon_key'], 'valve')
        self.product.refresh_from_db()
        self.assertEqual(before, (self.product.category_id, self.product.price, self.category.slug, self.category.order))
        self.assertEqual(self.client.get('/products', {'category_id': self.category.pk}).data['total'], 1)

    def test_create_empty_category_and_legacy_null_are_supported(self):
        response = self.client.post('/categories', {'name':'Válvulas QA', 'icon_key':'valve'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['data']['product_count'], 0)
        self.assertEqual(response.data['data']['icon_key'], 'valve')
        self.assertIsNone(Category.objects.get(pk=self.category.pk).icon_key)
        self.assertEqual(self.client.patch(f'/categories/{self.category.pk}', {'icon_key':None}, format='json').status_code, 200)

    def test_invalid_keys_and_unauthorized_edits_are_rejected(self):
        for key in ('__proto__','constructor','https://external.invalid/icon.svg','lucide/ArbitraryImport'):
            response = self.client.patch(f'/categories/{self.category.pk}', {'icon_key':key}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('icon_key', response.data)
        self.client.force_authenticate(None)
        self.assertIn(self.client.patch(f'/categories/{self.category.pk}', {'icon_key':'zap'}, format='json').status_code,(401,403))
        self.category.refresh_from_db()
        self.assertIsNone(self.category.icon_key)

    def test_duplicate_names_ignore_case_accents_spaces_and_slug_collisions(self):
        for name in ('  CATEGORIA   HISTÓRICA QA  ', 'Categoría histórica QA!'):
            response=self.client.post('/categories', {'name':name,'icon_key':'wrench'}, format='json')
            self.assertEqual(response.status_code,400,response.data)
        self.assertEqual(Category.objects.filter(slug='categoria-historica-qa').count(),1)
        response=self.client.patch(f'/categories/{self.category.pk}', {'name':self.category.name,'is_active':False}, format='json')
        self.assertEqual(response.status_code,200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.category_id,self.category.pk)

    def test_controlled_registry_includes_all_required_product_families(self):
        self.assertTrue({'flame','heater','gauge','valve','pipe','cylinder','wrench','zap','steam'} <= ICON_KEYS)

    def test_existing_duplicate_labels_do_not_block_unrelated_icon_edits(self):
        Category.objects.create(name='CATEGORIA HISTORICA QA', slug='legacy-duplicate-qa')
        response=self.client.put(f'/categories/{self.category.pk}', {
            'name':self.category.name, 'icon_key':'folder-tree', 'order':self.category.order,
        },format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(Category.objects.filter(pk=self.category.pk).get().slug,'categoria-historica-qa')
