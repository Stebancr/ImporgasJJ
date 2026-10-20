"""Production-shaped synthetic data only; never call a real carrier or payment API."""
from decimal import Decimal
from io import StringIO
import json
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APITestCase
from usuarios.models import Credenciales, Usuario
from usuarios.terms import CURRENT_TERMS_VERSION
from django.utils import timezone
from unittest.mock import patch
from ecommerce.models import Product, Brand, Category, CartItem, Order, WompiPaymentIntent
from .models import ProductShippingProfile


class LegacyProductRolloutTests(APITestCase):
    def setUp(self):
        self.admin = Credenciales.objects.create(usuario='rollout-admin',tipo_usuario=4,estado=1)
        profile=Usuario.objects.create(cedula='rollout-synthetic',nombre_completo='QA',terms_version=CURRENT_TERMS_VERSION,terms_accepted_at=timezone.now())
        self.customer = Credenciales.objects.create(usuario='rollout-customer',tipo_usuario=0,estado=1,usuario_rel=profile)
        self.product = Product.objects.create(name='Producto histórico', description='Conservar',price=2900000,total_stock=7,
            brand=Brand.objects.create(name='Marca ensayo'),category=Category.objects.create(name='Categoría ensayo'))
        self.client.force_authenticate(self.admin)

    @override_settings(TCC_SHIPPING_ENABLED=True)
    def test_legacy_product_visible_editable_and_filterable_without_inventing_profile(self):
        detail = self.client.get(f'/products/{self.product.pk}')
        self.assertEqual(detail.status_code,200)
        self.assertIsNone(detail.data['data']['shipping_profile'])
        self.assertEqual(detail.data['data']['shipping_status'],'incomplete')
        before = (self.product.price,self.product.total_stock)
        response = self.client.patch(f'/products/{self.product.pk}', {'description':'Texto actualizado'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.product.refresh_from_db()
        self.assertEqual((self.product.price,self.product.total_stock),before)
        self.assertFalse(ProductShippingProfile.objects.exists())
        response = self.client.get('/products',{'shipping_status':'incomplete'})
        self.assertEqual(response.data['total'],1)

    def test_logistics_status_rejects_invalid_packaging_even_with_positive_dimensions(self):
        profile = ProductShippingProfile.objects.create(product=self.product,weight_kg=1,height_cm=1,width_cm=1,
            length_cm=1,declared_value=100,packaging_code='UNDOCUMENTED')
        self.assertFalse(Product.objects.get(pk=self.product.pk).shipping_ready)
        profile.packaging_code='CLEM_CAJA';profile.save()
        self.assertTrue(Product.objects.get(pk=self.product.pk).shipping_ready)

    @override_settings(TCC_SHIPPING_ENABLED=False,TCC_REQUIRE_CONFIRMED_SHIPPING=True)
    def test_disabled_tcc_does_not_silently_charge_zero_or_create_payment(self):
        self.client.force_authenticate(self.customer)
        result=self.client.post('/orders', {'customer_name':'QA','customer_email':'qa@example.invalid',
            'customer_phone':'3000000000','shipping_address':'Dirección sintética','payment_method':'wompi',
            'wompi_reference':'rollout-never-charge','items':[{'product_id':self.product.pk,'quantity':1}]},format='json')
        self.assertEqual(result.status_code,409,result.data)
        self.assertEqual(result.data['code'],'shipping_pending')
        self.assertFalse(Order.objects.exists())
        self.assertFalse(WompiPaymentIntent.objects.exists())

    @override_settings(TCC_SHIPPING_ENABLED=True,TCC_ADMIN_ONLY=True,TCC_REQUIRE_CONFIRMED_SHIPPING=True)
    def test_admin_only_rollout_gates_config_estimation_and_checkout(self):
        self.assertTrue(self.client.get('/shipping/config').data['enabled'])
        self.client.force_authenticate(self.customer)
        self.assertFalse(self.client.get('/shipping/config').data['enabled'])
        self.assertEqual(self.client.post('/shipping/estimate',{},format='json').status_code,503)
        self.client.force_authenticate(None)
        self.assertFalse(self.client.get('/shipping/config').data['enabled'])

    def test_preflight_is_read_only_and_does_not_print_credentials(self):
        output=StringIO()
        with override_settings(TCC_PRODUCTION_API_TOKEN='secret-never-print'):
            call_command('tcc_preflight',production=True,stdout=output)
        self.assertNotIn('secret-never-print',output.getvalue())
        report=json.loads(output.getvalue())
        self.assertEqual(report['logistical_status']['incomplete'],1)
        self.assertFalse(ProductShippingProfile.objects.exists())

    def test_release_migration_rolls_back_the_entire_operation_on_failure(self):
        def failure(*args, **kwargs):
            Product.objects.filter(pk=self.product.pk).update(price=1)
            raise RuntimeError('Synthetic migration failure')
        with patch('shipping.management.commands.migrate_tcc_release.call_command', side_effect=failure):
            with self.assertRaises(RuntimeError):
                call_command('migrate_tcc_release',stdout=StringIO())
        self.product.refresh_from_db()
        self.assertEqual(self.product.price,Decimal('2900000'))


class MigrationAndRollbackRehearsal(TransactionTestCase):
    """Migrate from production's 0013 schema; roll back code with additive schema intact."""
    def test_upgrade_preserves_legacy_products_and_old_version_can_still_write(self):
        executor=MigrationExecutor(connection)
        latest=executor.loader.graph.leaf_nodes()
        old_targets=[('shipping',None),('ecommerce','0013_cartitem')]
        try:
            executor.migrate(old_targets)
            old=executor.loader.project_state([('ecommerce','0013_cartitem')]).apps
            BrandOld=old.get_model('ecommerce','Brand'); CategoryOld=old.get_model('ecommerce','Category')
            ProductOld=old.get_model('ecommerce','Product'); OrderOld=old.get_model('ecommerce','Order')
            AddressOld=old.get_model('ecommerce','UserAddress'); IntentOld=old.get_model('ecommerce','WompiPaymentIntent')
            brand=BrandOld.objects.create(name='Ensayo',slug='ensayo')
            category=CategoryOld.objects.create(name='Ensayo',slug='ensayo')
            product=ProductOld.objects.create(name='Histórico',slug='historico',description='Texto original',
                price=2900000,total_stock=7,is_available=True,brand=brand,category=category)
            account=Credenciales.objects.create(usuario='rollback-synthetic',password='!')
            snapshot=list(ProductOld.objects.values('id','description','price','total_stock','is_available'))
            call_command('migrate_tcc_release',stdout=StringIO())
            self.assertEqual(list(ProductOld.objects.values('id','description','price','total_stock','is_available')),snapshot)
            self.assertFalse(ProductShippingProfile.objects.exists())
            # Simulate the previous application's ORM: it does not know the new columns.
            address=AddressOld.objects.create(user_id=account.pk,recipient_name='QA',address='Dirección sintética',city='Cali')
            order=OrderOld.objects.create(user_id=account.pk,order_number='ROLLBACK-QA',customer_name='QA',
                customer_email='qa@example.invalid',subtotal=2900000,shipping_cost=25000,total=2925000,payment_method='cash')
            IntentOld.objects.create(user_id=account.pk,reference='ROLLBACK-PAY-QA',subtotal=2900000,shipping_cost=25000,
                total=2925000,checkout_data={})
            self.assertIsNotNone(address.pk)
            self.assertEqual(Order.objects.get(pk=order.pk).total,Decimal('2925000'))
            ProductOld.objects.filter(pk=product.pk).update(description='Edición con versión anterior')
            self.assertEqual(Product.objects.get(pk=product.pk).description,'Edición con versión anterior')
        finally:
            MigrationExecutor(connection).migrate(latest)
