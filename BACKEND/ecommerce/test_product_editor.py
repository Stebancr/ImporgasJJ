import io
import json
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from usuarios.models import Credenciales
from ecommerce.models import Product, ProductImage, ProductStock, Brand, Category, Location


def photo():
    stream = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(stream, format='PNG')
    return SimpleUploadedFile('qa.png', stream.getvalue(), content_type='image/png')


class ProductEditorTests(APITestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name, TCC_SHIPPING_ENABLED=False)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = Credenciales.objects.create(usuario='product-editor-admin', tipo_usuario=4, estado=1)
        self.client.force_authenticate(self.user)
        self.location = Location.objects.create(name='QA', address='QA', city='Cali')
        self.payload = dict(key=str(uuid.uuid4()), product=dict(name='Producto QA', price='100.00',
            category=Category.objects.create(name='QA').pk, brand=Brand.objects.create(name='QA').pk),
            images=[dict(file='upload_0', alt_text='Imagen QA')], primary=0,
            stocks=[dict(location=self.location.pk, quantity=5)], specs=[dict(name='Modelo', value='QA')])

    def save(self, pk=None):
        return self.client.post(f'/ecommerce/products/{pk}/editor' if pk else '/ecommerce/products/editor',
            {'payload': json.dumps(self.payload), **({'upload_0': photo()} if any('file' in i for i in self.payload['images']) else {})}, format='multipart')

    def test_create_retry_and_edit_gallery(self):
        first = self.save()
        self.assertEqual(first.status_code, 201, first.data)
        pk = first.data['data']['id']
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ProductImage.objects.count(), 1)
        self.assertEqual(ProductStock.objects.get().quantity, 5)
        self.payload.update(key=str(uuid.uuid4()), updated_at=first.data['data']['updated_at'], images=[], primary=None)
        self.payload['specs'] = []
        self.assertEqual(self.save(pk).status_code, 200)
        self.assertEqual(ProductImage.objects.count(), 0)
        self.assertEqual(len(list(Path(self.media.name).rglob('*.png'))), 1, 'Existing blobs remain safely retained.')

    def test_invalid_stock_rolls_back_everything(self):
        self.payload['stocks'][0]['quantity'] = -1
        self.assertEqual(self.save().status_code, 400)
        self.assertFalse(Product.objects.exists())
        self.assertFalse(list(Path(self.media.name).rglob('*.png')))

    def test_late_failure_rolls_back_database_and_new_file(self):
        with patch('ecommerce.product_editor.ProductStock.objects.update_or_create', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                self.save()
        self.assertFalse(Product.objects.exists())
        self.assertFalse(ProductImage.objects.exists())
        self.assertFalse(list(Path(self.media.name).rglob('*.png')))

    def test_changed_retry_and_stale_edit_rejected(self):
        first = self.save().data['data']
        self.payload['product']['name'] = 'Changed'
        self.assertEqual(self.save().status_code, 409)
        self.payload.update(key=str(uuid.uuid4()), updated_at='old')
        self.assertEqual(self.save(first['id']).status_code, 409)
        self.assertEqual(Product.objects.get().name, 'Producto QA')

    def test_positive_price_and_permissions(self):
        self.payload['product']['price'] = '0'
        self.assertEqual(self.save().status_code, 400)
        self.user.tipo_usuario = 0
        self.user.save()
        self.assertEqual(self.save().status_code, 403)

    def test_invalid_primary_and_foreign_image(self):
        self.payload['primary'] = 8
        self.assertEqual(self.save().status_code, 400)
        self.payload.update(primary=0, images=[dict(id=999)])
        self.assertEqual(self.save().status_code, 400)

    def test_existing_images_survive_edit(self):
        first = self.save().data['data']
        product = Product.objects.get()
        image = ProductImage.objects.get()
        original_path = image.image.name
        self.payload.update(key=str(uuid.uuid4()), updated_at=first['updated_at'], images=[dict(id=image.pk, alt_text='Nuevo texto')])
        self.payload['product']['price'] = '150'
        self.payload['stocks'][0]['quantity'] = 9
        self.payload['specs'] = [dict(id=product.specifications.get().pk, value='Actualizado')]
        response = self.save(product.pk)
        self.assertEqual(response.status_code, 200, response.data)
        image.refresh_from_db()
        self.assertEqual(image.image.name, original_path)
        self.assertEqual(image.alt_text, 'Nuevo texto')
        self.assertEqual(ProductStock.objects.get().quantity, 9)
        self.assertEqual(product.specifications.get().value, 'Actualizado')

    def test_declared_price_distributed_without_rounding_inflation(self):
        from shipping import tests as fixtures
        from shipping.services import shipping_snapshot
        self.payload['product']['shipping_profile'] = dict(weight_kg='1', height_cm='10',
            width_cm='10', length_cm='10', declared_value_from_price=True, packages_per_unit=3)
        with override_settings(**fixtures.TEST_SETTINGS):
            response = self.save()
            self.assertEqual(response.status_code, 201, response.data)
            product = Product.objects.get()
            self.assertTrue(product.shipping_ready)
            snapshot = shipping_snapshot(self.user, [{'product_id':product.pk,'quantity':2}],
                {'tcc_city_code':'76001000'}, estimate=True)
            values = [Decimal(p['declared_value']) for p in snapshot['packages']]
            self.assertEqual(sum(values), Decimal('200'))
            self.assertEqual(values[:3], [Decimal('33.34'), Decimal('33.33'), Decimal('33.33')])
            product.price = Decimal('120'); product.save()
            second = shipping_snapshot(self.user, [{'product_id':product.pk,'quantity':1}],
                {'tcc_city_code':'76001000'}, estimate=True)
            self.assertEqual(sum(Decimal(p['declared_value']) for p in second['packages']), Decimal('120'))

    def test_manual_declared_value_and_existing_images_survive_edit(self):
        from shipping import tests as fixtures
        from shipping.services import shipping_snapshot
        self.payload['product']['shipping_profile'] = dict(weight_kg='1', height_cm='10',
            width_cm='10', length_cm='10', declared_value_from_price=False,
            declared_value='20', packages_per_unit=3)
        with override_settings(**fixtures.TEST_SETTINGS):
            first = self.save().data['data']
            product = Product.objects.get()
            snapshot = shipping_snapshot(self.user, [{'product_id':product.pk,'quantity':2}],
                {'tcc_city_code':'76001000'}, estimate=True)
            self.assertEqual(sum(Decimal(p['declared_value']) for p in snapshot['packages']), Decimal('120'))
            image = ProductImage.objects.get()
            original_path = image.image.name
            self.payload.update(key=str(uuid.uuid4()), updated_at=first['updated_at'],
                images=[dict(id=image.pk, alt_text='Nuevo texto')])
            self.payload['product']['price'] = '150'
            self.payload['stocks'][0]['quantity'] = 9
            self.payload['specs'] = [dict(id=product.specifications.get().pk, value='Actualizado')]
            response = self.save(product.pk)
            self.assertEqual(response.status_code, 200, response.data)
            image.refresh_from_db(); product.refresh_from_db()
            self.assertEqual(image.image.name, original_path)
            self.assertEqual(image.alt_text, 'Nuevo texto')
            self.assertEqual(ProductStock.objects.get().quantity, 9)
            self.assertEqual(product.shipping_profile.declared_value, Decimal('20'))

    def test_primary_change_and_duplicate_spec_roll_back(self):
        first = self.save().data['data']
        product = Product.objects.get()
        previous = ProductImage.objects.get()
        self.payload.update(key=str(uuid.uuid4()), updated_at=first['updated_at'],
            images=[dict(id=previous.pk), dict(file='upload_0')], primary=1)
        response = self.save(product.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(product.images.filter(is_primary=True).count(), 1)
        self.assertNotEqual(product.images.get(is_primary=True).pk, previous.pk)
        self.payload.update(key=str(uuid.uuid4()), updated_at=response.data['data']['updated_at'])
        self.payload['specs'] = [dict(name='Duplicada',value='A'),dict(name='Duplicada',value='B')]
        self.assertEqual(self.save(product.pk).status_code, 400)
        self.assertEqual(product.images.count(), 2)
        self.assertEqual(product.images.filter(is_primary=True).count(), 1)
        self.assertEqual(len(list(Path(self.media.name).rglob('*.png'))), 2)
