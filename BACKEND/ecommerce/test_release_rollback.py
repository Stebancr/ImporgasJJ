from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase


class PreviousReleaseWriteCompatibilityTests(TestCase):
    def test_old_account_and_address_writes_survive_image_rollback(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Rollback SQL defaults target PostgreSQL production only.')
        apps = MigrationLoader(connection).project_state([
            ('usuarios', '0007_credential_password_version'), ('ecommerce', '0013_cartitem'),
        ]).apps
        old_user = apps.get_model('usuarios', 'Credenciales').objects.create(usuario='rollback-synthetic', estado=1, tipo_usuario=0)
        old_address = apps.get_model('ecommerce', 'UserAddress').objects.create(user_id=old_user.pk,
            recipient_name='QA', phone='0000000000', address='Synthetic', city='Cali', department='Valle del Cauca')
        from usuarios.models import Credenciales
        from ecommerce.models import UserAddress
        self.assertEqual(Credenciales.objects.get(pk=old_user.pk).password_reset_version, 0)
        current = UserAddress.objects.get(pk=old_address.pk)
        self.assertEqual((current.complement, current.neighborhood, current.delivery_instructions), ('', '', ''))

    def test_old_order_writes_preserve_current_defaults(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Rollback SQL defaults target PostgreSQL production only.')
        apps = MigrationLoader(connection).project_state([('ecommerce', '0013_cartitem')]).apps
        old = apps.get_model('ecommerce', 'Order').objects.create(customer_name='Synthetic', customer_email='qa@example.invalid',
            shipping_address='Synthetic', city='Cali', department='Valle del Cauca', subtotal=1000, shipping_cost=0, total=1000)
        from ecommerce.models import Order
        current = Order.objects.get(pk=old.pk)
        self.assertEqual((current.discounts, current.taxes, current.delivery_details), (0, 0, {}))
        self.assertIsNone(current.carrier_shipping_cost)
