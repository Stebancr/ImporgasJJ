"""Isolated database and temporary media only; no live catalog is modified."""
import tempfile
from pathlib import Path

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIRequestFactory
from usuarios.models import Credenciales
from .models import Brand, Category, Product, ProductImage
from .serializers import ProductCreateSerializer, ProductListSerializer, FavoriteSerializer


class ProductPresentationTests(APITestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.admin = Credenciales.objects.create(usuario='presentation-admin', tipo_usuario=1, estado=1)
        self.client.force_authenticate(self.admin)
        request = APIRequestFactory().get('/')
        request.user = self.admin
        self.context = {'request': request}
        self.product = Product.objects.create(name='Synthetic QA', price=123, category=Category.objects.create(name='QA'), brand=Brand.objects.create(name='QA'))
        self.images = []
        for index in range(3):
            name = f'qa-{index}.png'
            Path(self.media.name, name).write_bytes(b'synthetic file')
            self.images.append(ProductImage.objects.create(product=self.product, image=name, order=index, is_primary=index == 0))

    def url(self, image):
        return reverse('product-image-detail', args=[self.product.id, image.id])

    def test_selection_persists_and_preserves_gallery_and_product(self):
        response = self.client.patch(self.url(self.images[2]), {'is_primary': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.product.images.filter(is_primary=True).values_list('pk', flat=True)), [self.images[2].pk])
        self.assertEqual(self.product.images.count(), 3)
        for image in self.images:
            self.assertEqual(Path(self.media.name, image.image.name).read_bytes(), b'synthetic file')
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 123)
        self.assertEqual(self.product.total_stock, 0)
        self.assertIn('qa-2.png', ProductListSerializer(self.product, context=self.context).data['primary_image'])
        # Favorites (and listing/search) use this same serializer contract.
        self.assertIn('qa-2.png', FavoriteSerializer(type('FavoriteFixture', (), {'id': 1, 'product': self.product, 'created_at': self.product.created_at})(), context=self.context).data['product']['primary_image'])
        response = self.client.get(reverse('product-detail', args=[self.product.pk]))
        self.assertEqual([i['id'] for i in response.data['data']['images'] if i['is_primary']], [self.images[2].id])

    def test_delete_primary_promotes_alternative_then_handles_empty(self):
        for image in self.images:
            self.assertEqual(self.client.delete(self.url(image)).status_code, 204)
            remaining = self.product.images.count()
            self.assertEqual(self.product.images.filter(is_primary=True).count(), min(1, remaining))
        self.assertIsNone(ProductListSerializer(self.product).data['primary_image'])

    def test_cross_product_and_unauthorized_selection_rejected(self):
        other = Product.objects.create(name='Other QA', price=1, category=self.product.category, brand=self.product.brand)
        self.assertEqual(self.client.patch(reverse('product-image-detail', args=[other.pk, self.images[0].pk]), {'is_primary': True}, format='json').status_code, 404)
        self.client.force_authenticate(Credenciales.objects.create(usuario='presentation-customer', tipo_usuario=0, estado=1))
        self.assertEqual(self.client.patch(self.url(self.images[1]), {'is_primary': True}, format='json').status_code, 403)
        self.assertEqual(self.product.images.filter(is_primary=True).get().id, self.images[0].id)

    def test_description_preserved_verbatim(self):
        for text in ['', '  Título\r\n* Uno\n- Dos\n• Tres\n\nPárrafo  ', '<script>alert(1)</script> & <b>texto</b>']:
            with self.subTest(text=text):
                serializer = ProductCreateSerializer(self.product, data={'description': text}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                self.product.refresh_from_db()
                self.assertEqual(self.product.description, text)

    def test_primary_in_catalog_search_favorites_and_cart_product(self):
        self.client.patch(self.url(self.images[1]), {'is_primary': True}, format='json')
        for query in ['', '?search=Synthetic']:
            response = self.client.get(reverse('product-list') + query)
            self.assertEqual(response.status_code, 200)
            self.assertIn('qa-1.png', response.data['data'][0]['primary_image'])
        self.assertEqual(self.client.post(reverse('favorite-list'), {'product_id': self.product.id}, format='json').status_code, 201)
        response = self.client.get(reverse('favorite-list'))
        self.assertIn('qa-1.png', response.data['data'][0]['product']['primary_image'])
        response = self.client.post(reverse('cart'), {'product_id': self.product.id, 'quantity': 1}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['items'], [{'product_id': self.product.id, 'quantity': 1}])
        response = self.client.get(reverse('product-detail', args=[response.data['items'][0]['product_id']]))
        primary = [i for i in response.data['data']['images'] if i['is_primary']]
        self.assertEqual(primary[0]['id'], self.images[1].id)
