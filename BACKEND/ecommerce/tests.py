import hashlib
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import override_settings
from django.core import mail
from django.urls import reverse
from rest_framework.test import APITestCase

from usuarios.models import Credenciales, Usuario
from usuarios.terms import CURRENT_TERMS_VERSION
from django.utils import timezone
from .models import Brand, CartItem, Category, FCMDeviceToken, Location, Order, Product, ProductStock, Review, WompiPaymentIntent
from .email_service import send_order_payment_confirmation
from gestion.models import Cotizacion, Factura


class LocationDeleteAPITests(APITestCase):
    def setUp(self):
        self.admin = Credenciales.objects.create(usuario='location-admin', estado=1, tipo_usuario=1)
        self.client.force_authenticate(self.admin)
        self.location = Location.objects.create(name='Sede de prueba', address='Calle 1', city='Cali')
        self.url = reverse('location-detail', args=[self.location.id])

    def test_unused_location_can_be_deleted(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Location.objects.filter(pk=self.location.pk).exists())

    def test_assigned_worker_blocks_delete_without_losing_assignment(self):
        worker = Credenciales.objects.create(usuario='location-worker', estado=1, tipo_usuario=0, location=self.location)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertIn('usuario o trabajador asignado', response.data['error'])
        worker.refresh_from_db()
        self.assertEqual(worker.location_id, self.location.id)

    def test_product_stock_blocks_delete_with_useful_message(self):
        brand = Brand.objects.create(name='Marca sede')
        category = Category.objects.create(name='Categoría sede')
        product = Product.objects.create(name='Producto sede', price=100, brand=brand, category=category)
        ProductStock.objects.create(product=product, location=self.location, quantity=1)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertIn('producto con stock', response.data['error'])
        self.assertTrue(Location.objects.filter(pk=self.location.pk).exists())

    def test_quotation_and_invoice_block_delete(self):
        Cotizacion.objects.create(location=self.location, creado_por=self.admin, cliente_nombre='Cliente')
        Factura.objects.create(location=self.location, creado_por=self.admin, cliente_nombre='Cliente')
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertIn('1 cotización', response.data['error'])
        self.assertIn('1 factura', response.data['error'])
        self.assertTrue(Location.objects.filter(pk=self.location.pk).exists())


class ProductReviewAPITests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(cedula='review-1', nombre_completo='Cliente Prueba', correo='review@example.com')
        self.user = Credenciales.objects.create(usuario='reviewer', usuario_rel=profile, estado=1, tipo_usuario=0)
        self.user.set_password('safe-test-password')
        self.user.save(update_fields=['password'])
        brand = Brand.objects.create(name='Marca Test')
        category = Category.objects.create(name='Categoría Test')
        self.product = Product.objects.create(
            name='Producto Test', description='Producto para pruebas', price=100000,
            brand=brand, category=category,
        )
        self.url = reverse('product-review-list', args=[self.product.id])

    def test_anonymous_can_list_but_cannot_create(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertIn(self.client.post(self.url, {'rating': 5, 'comment': 'Excelente'}, format='json').status_code, [401, 403])

    def test_authenticated_user_can_create_review(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'rating': 5, 'comment': 'Excelente producto'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 1)
        self.assertEqual(float(self.product.rating), 5.0)

    def test_invalid_ratings_and_missing_product_are_rejected(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url, {'rating': 0, 'comment': 'Comentario válido'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'rating': 6, 'comment': 'Comentario válido'}, format='json').status_code, 400)
        missing_url = reverse('product-review-list', args=[999999])
        self.assertEqual(self.client.post(missing_url, {'rating': 5, 'comment': 'Comentario válido'}, format='json').status_code, 404)

    def test_duplicate_review_is_rejected(self):
        Review.objects.create(product=self.product, user=self.user, rating=4, comment='Primera reseña')
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'rating': 5, 'comment': 'Segunda reseña'}, format='json')
        self.assertEqual(response.status_code, 400)


@override_settings(CASH_ON_DELIVERY_ENABLED=True)
class EcommercePurchaseFlowTests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(
            cedula='buyer-1', nombre_completo='Cliente Compra', correo='compra@example.com',
            terms_accepted_at=timezone.now(), terms_version=CURRENT_TERMS_VERSION,
        )
        self.user = Credenciales.objects.create(usuario='buyer', usuario_rel=profile, estado=1, tipo_usuario=0)
        brand = Brand.objects.create(name='Marca Compra')
        category = Category.objects.create(name='Categoría Compra')
        self.product = Product.objects.create(
            name='Producto comprable', description='Producto para flujo completo',
            price=Decimal('600000.00'), brand=brand, category=category,
        )
        location = Location.objects.create(name='Bodega Compra', address='Calle 2', city='Bogotá')
        ProductStock.objects.create(product=self.product, location=location, quantity=4)
        self.payload = {
            'customer_name': 'Cliente Compra', 'customer_email': 'compra@example.com',
            'customer_phone': '3000000000', 'shipping_address': 'Calle 10 # 20-30',
            'city': 'Bogotá', 'department': 'Bogotá D.C.', 'payment_method': 'cash',
            'items': [{'product_id': self.product.id, 'quantity': 2}],
        }

    @override_settings(CASH_ON_DELIVERY_ENABLED=False)
    def test_disabled_cash_method_is_rejected_by_backend(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_catalog_detail_cart_payload_cash_order_and_tracking(self):
        listing = self.client.get(reverse('product-list'))
        detail = self.client.get(reverse('product-detail', args=[self.product.id]))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['data']['total_stock'], 4)

        self.client.force_authenticate(self.user)
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(pk=response.data['data']['id'])
        self.assertEqual(order.items.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.total_stock, 2)
        tracked = self.client.get(reverse('order-tracking', args=[order.tracking_code]))
        self.assertEqual(tracked.status_code, 200)
        self.assertEqual(tracked.data['data']['order_number'], order.order_number)

    def test_product_pagination_rejects_invalid_values_without_server_error(self):
        for query in ('?per_page=0', '?per_page=abc', '?page=-1'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(reverse('product-list') + query).status_code, 400)

    def test_cart_requires_login_and_supports_item_lifecycle(self):
        cart_url = reverse('cart')
        item_url = reverse('cart-item', args=[self.product.id])
        self.assertEqual(self.client.get(cart_url).status_code, 401)
        self.assertEqual(self.client.post(cart_url, {'product_id': self.product.id, 'quantity': 1}, format='json').status_code, 401)
        self.assertFalse(CartItem.objects.exists())

        self.client.force_authenticate(self.user)
        added = self.client.post(cart_url, {'product_id': self.product.id, 'quantity': 1}, format='json')
        self.assertEqual(added.status_code, 201)
        self.assertEqual(added.data['items'][0]['quantity'], 1)
        changed = self.client.patch(item_url, {'quantity': 3}, format='json')
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data['items'][0]['quantity'], 3)
        self.assertEqual(self.client.patch(item_url, {'quantity': 1000}, format='json').status_code, 400)
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 3)
        self.assertEqual(self.client.delete(item_url).status_code, 204)
        self.assertFalse(CartItem.objects.exists())

    def test_repeated_addition_updates_single_cart_line_and_quantity(self):
        self.client.force_authenticate(self.user)
        cart_url = reverse('cart')
        first = self.client.post(cart_url, {'product_id': self.product.id, 'quantity': 1}, format='json')
        second = self.client.post(cart_url, {'product_id': self.product.id, 'quantity': 2}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['items'][0]['quantity'], 3)
        self.assertEqual(CartItem.objects.filter(user=self.user, product=self.product).count(), 1)

    def test_zero_quantity_never_creates_order(self):
        self.client.force_authenticate(self.user)
        self.payload['items'][0]['quantity'] = 0
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_anonymous_cannot_create_order_or_payment_intent(self):
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(ProductStock.objects.get(product=self.product).quantity, 4)
        self.payload.update(payment_method='wompi', wompi_reference='ANON-REF')
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(WompiPaymentIntent.objects.exists())

    def test_old_terms_must_be_accepted_before_checkout(self):
        self.client.force_authenticate(self.user)
        self.user.usuario_rel.terms_version = '0.9'
        self.user.usuario_rel.save(update_fields=['terms_version'])
        response = self.client.post(reverse('order-list'), self.payload, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'terms_acceptance_required')
        self.assertFalse(Order.objects.exists())


@override_settings(
    WOMPI_EVENTS_SECRET='events-secret-for-tests',
    WOMPI_PUBLIC_KEY='pub_test_for_tests',
    WOMPI_INTEGRITY_SECRET='integrity-secret-for-tests',
    WOMPI_API_URL='https://sandbox.wompi.co/v1',
    WOMPI_HTTP_TIMEOUT=2,
)
class WompiPaymentTests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(
            cedula='wompi-buyer', nombre_completo='Cliente Wompi', correo='wompi@example.com',
            terms_accepted_at=timezone.now(), terms_version=CURRENT_TERMS_VERSION,
        )
        self.user = Credenciales.objects.create(usuario='wompi-buyer', usuario_rel=profile, estado=1, tipo_usuario=0)
        self.client.force_authenticate(self.user)
        brand = Brand.objects.create(name='Wompi Brand')
        category = Category.objects.create(name='Wompi Category')
        self.product = Product.objects.create(
            name='Calentador Wompi', description='10 litros gas natural', price=Decimal('125000.00'),
            brand=brand, category=category,
        )
        location = Location.objects.create(name='Bodega Wompi', address='Calle 1', city='Bogotá')
        ProductStock.objects.create(product=self.product, location=location, quantity=10)

    def create_intent(self, suffix):
        return WompiPaymentIntent.objects.create(
            user=self.user, reference=f'REF-{suffix}', subtotal=Decimal('125000.00'), shipping_cost=0,
            total=Decimal('125000.00'), checkout_data={
                'customer_name': 'Cliente Wompi', 'customer_email': 'wompi@example.com',
                'shipping_address': 'Dirección de prueba',
                'items': [{'product_id': self.product.id, 'product_name': self.product.name,
                           'quantity': 1, 'unit_price': '125000.00'}],
            },
        )

    def signed_payload(self, intent, payment_status):
        transaction = {
            'id': f'TX-{intent.pk}-{payment_status}', 'reference': intent.reference,
            'status': payment_status, 'amount_in_cents': int(intent.total * 100), 'currency': 'COP',
        }
        timestamp = 1700000000
        properties = ['transaction.id', 'transaction.status', 'transaction.amount_in_cents']
        raw = f"{transaction['id']}{transaction['status']}{transaction['amount_in_cents']}{timestamp}events-secret-for-tests"
        return {
            'event': 'transaction.updated', 'data': {'transaction': transaction},
            'signature': {'properties': properties, 'checksum': hashlib.sha256(raw.encode()).hexdigest()},
            'timestamp': timestamp,
        }

    def test_signed_webhook_handles_all_wompi_states(self):
        for payment_status in ('APPROVED', 'PENDING', 'DECLINED', 'VOIDED', 'ERROR'):
            with self.subTest(payment_status=payment_status):
                intent = self.create_intent(payment_status)
                response = self.client.post(reverse('wompi-webhook'), self.signed_payload(intent, payment_status), format='json')
                self.assertEqual(response.status_code, 200)
                intent.refresh_from_db()
                self.assertEqual(intent.wompi_status, payment_status)
                self.assertEqual(Order.objects.filter(wompi_reference=intent.reference).count(), 1 if payment_status == 'APPROVED' else 0)

    def test_duplicate_approved_webhook_creates_one_order(self):
        intent = self.create_intent('DUPLICATE')
        payload = self.signed_payload(intent, 'APPROVED')
        self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 200)
        self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 200)
        self.assertEqual(Order.objects.filter(wompi_reference=intent.reference).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.total_stock, 9)

    def test_zero_and_negative_stock_can_be_ordered_only_after_approval(self):
        ProductStock.objects.filter(product=self.product).update(quantity=0)
        self.product.total_stock = 0
        self.product.save(update_fields=['total_stock'])
        cart_response = self.client.post(reverse('cart'), {'product_id': self.product.pk, 'quantity': 2}, format='json')
        self.assertEqual(cart_response.status_code, 201)
        for number, quantity, expected in ((1, 2, -2), (2, 3, -5)):
            with self.subTest(number=number):
                reference = f'REF-NEGATIVE-{number}'
                response = self.client.post(reverse('order-list'), {
                    'customer_name': 'Cliente Wompi', 'customer_email': 'wompi@example.com',
                    'shipping_address': 'Dirección de prueba', 'payment_method': 'wompi',
                    'wompi_reference': reference,
                    'items': [{'product_id': self.product.pk, 'quantity': quantity}],
                }, format='json')
                self.assertEqual(response.status_code, 201)
                self.product.refresh_from_db()
                self.assertEqual(self.product.total_stock, 0 if number == 1 else -2)
                intent = WompiPaymentIntent.objects.get(reference=reference)
                payload = self.signed_payload(intent, 'APPROVED')
                self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 200)
                self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 200)
                self.product.refresh_from_db()
                self.assertEqual(self.product.total_stock, expected)
                self.assertEqual(Order.objects.filter(wompi_reference=reference).count(), 1)
                detail = self.client.get(reverse('product-detail', args=[self.product.pk]))
                self.assertEqual(detail.data['data']['total_stock'], 0)
                self.assertNotIn('stock_entries', detail.data['data'])

    def test_checkout_creates_intent_and_order_only_after_approval(self):
        payload = {
            'customer_name': 'Cliente Wompi', 'customer_email': 'wompi@example.com',
            'shipping_address': 'Dirección de prueba', 'payment_method': 'wompi',
            'wompi_reference': 'REF-CHECKOUT',
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }
        response = self.client.post(reverse('order-list'), payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 0)
        intent = WompiPaymentIntent.objects.get(reference='REF-CHECKOUT')
        expected = hashlib.sha256(f'{intent.reference}{int(intent.total * 100)}COPintegrity-secret-for-tests'.encode()).hexdigest()
        self.assertEqual(response.data['data']['wompi_signature'], expected)
        self.assertEqual(Decimal(response.data['data']['total']), intent.total)
        approved = self.client.post(reverse('wompi-webhook'), self.signed_payload(intent, 'APPROVED'), format='json')
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(Order.objects.filter(wompi_reference='REF-CHECKOUT', status=Order.Status.PAID).count(), 1)

    def test_webhook_rejects_invalid_signature(self):
        intent = self.create_intent('INVALID')
        payload = self.signed_payload(intent, 'APPROVED')
        payload['signature']['checksum'] = 'invalid'
        self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 401)

    @patch('ecommerce.views.requests.get')
    def test_status_endpoint_verifies_transaction_with_wompi(self, request_get):
        intent = self.create_intent('QUERY')
        provider_response = Mock()
        provider_response.raise_for_status.return_value = None
        provider_response.json.return_value = {'data': self.signed_payload(intent, 'APPROVED')['data']['transaction']}
        request_get.return_value = provider_response
        response = self.client.get(reverse('wompi-payment-status'), {
            'tracking': str(intent.tracking_code), 'transaction_id': f'TX-{intent.pk}-APPROVED',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['payment_status'], 'APPROVED')


class FCMDeviceTokenAPITests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(cedula='fcm-1', nombre_completo='Móvil', correo='mobile@example.com')
        self.user = Credenciales.objects.create(usuario='mobile-user', usuario_rel=profile, estado=1, tipo_usuario=0)
        self.admin = Credenciales.objects.create(usuario='push-admin', estado=1, tipo_usuario=1)
        self.url = reverse('fcm-device-token-list')
        self.token = 'fcm-token-for-tests-' + ('x' * 40)

    def test_authentication_registration_deduplication_and_deactivation(self):
        self.assertIn(self.client.post(self.url, {'token': self.token}, format='json').status_code, [401, 403])
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url, {'token': self.token, 'platform': 'android'}, format='json').status_code, 201)
        self.assertEqual(self.client.post(self.url, {'token': self.token, 'platform': 'ios'}, format='json').status_code, 200)
        self.assertEqual(FCMDeviceToken.objects.filter(token=self.token).count(), 1)
        self.assertEqual(self.client.delete(self.url, {'token': self.token}, format='json').status_code, 204)
        self.assertFalse(FCMDeviceToken.objects.get(token=self.token).is_active)

    @patch('ecommerce.views.send_push_to_user')
    def test_admin_can_send_without_exposing_credentials(self, send_push):
        send_push.return_value = {'sent': 1, 'failed': 0, 'deactivated': 0}
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse('admin-push-notification'), {
            'user_id': self.user.pk,
            'title': 'Pedido actualizado',
            'body': 'Tu pedido cambió de estado.',
            'data': {'order_id': '10'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['sent'], 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PaymentConfirmationEmailTests(APITestCase):
    def test_approved_payment_sends_one_confirmation_email(self):
        order = Order.objects.create(
            customer_name='Cliente Pago', customer_email='cliente@example.com',
            shipping_address='Dirección de prueba', total=Decimal('89000.00'),
            payment_method=Order.PaymentMethod.WOMPI,
            wompi_reference='REF-EMAIL', wompi_status=Order.WompiStatus.APPROVED,
            status=Order.Status.PAID,
        )
        self.assertTrue(send_order_payment_confirmation(order.pk))
        self.assertFalse(send_order_payment_confirmation(order.pk))
        order.refresh_from_db()
        self.assertIsNotNone(order.payment_confirmation_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.order_number, mail.outbox[0].subject)
