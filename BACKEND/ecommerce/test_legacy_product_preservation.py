from unittest.mock import patch
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APITestCase
from usuarios.models import Credenciales
from ecommerce.models import Product, Category, Brand


class LegacyProductPreservationTests(APITestCase):
    def test_retained_historical_foreign_key_does_not_become_a_500(self):
        admin=Credenciales.objects.create(usuario='legacy-product-admin',tipo_usuario=4,estado=1)
        self.client.force_authenticate(admin)
        product=Product.objects.create(name='Historical QA',price=125000,
            category=Category.objects.create(name='QA'),brand=Brand.objects.create(name='QA'))
        with patch.object(Product,'delete',side_effect=IntegrityError('synthetic retained foreign key')):
            response=self.client.delete(reverse('product-detail',args=[product.pk]))
        self.assertEqual(response.status_code,409)
        product.refresh_from_db()
        self.assertEqual(product.name,'Historical QA')
        self.assertEqual(product.price,125000)
