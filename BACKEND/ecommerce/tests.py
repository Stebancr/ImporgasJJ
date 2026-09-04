import hashlib
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import override_settings
from django.core import mail
from django.urls import reverse
from rest_framework.test import APITestCase

from usuarios.models import Credenciales, Usuario
from .models import Brand, Category, FCMDeviceToken, Order, Product, Review
from .email_service import send_order_payment_confirmation


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


@override_settings(
    WOMPI_EVENTS_SECRET='events-secret-for-tests',
    WOMPI_PUBLIC_KEY='pub_test_for_tests',
    WOMPI_API_URL='https://sandbox.wompi.co/v1',
    WOMPI_HTTP_TIMEOUT=2,
)
class WompiPaymentTests(APITestCase):
    def create_order(self, suffix):
        return Order.objects.create(
            customer_name='Cliente Wompi', customer_email='wompi@example.com',
            shipping_address='Dirección de prueba', total=Decimal('125000.00'),
            payment_method=Order.PaymentMethod.WOMPI,
            wompi_reference=f'REF-{suffix}', wompi_status=Order.WompiStatus.PENDING,
        )

    def signed_payload(self, order, payment_status):
        transaction = {
            'id': f'TX-{payment_status}', 'reference': order.wompi_reference,
            'status': payment_status, 'amount_in_cents': 12500000, 'currency': 'COP',
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
        expected_order_status = {
            'APPROVED': Order.Status.PAID, 'PENDING': Order.Status.PENDING,
            'DECLINED': Order.Status.CANCELLED, 'VOIDED': Order.Status.CANCELLED,
            'ERROR': Order.Status.CANCELLED,
        }
        for payment_status, order_status in expected_order_status.items():
            with self.subTest(payment_status=payment_status):
                order = self.create_order(payment_status)
                response = self.client.post(reverse('wompi-webhook'), self.signed_payload(order, payment_status), format='json')
                self.assertEqual(response.status_code, 200)
                order.refresh_from_db()
                self.assertEqual(order.wompi_status, payment_status)
                self.assertEqual(order.status, order_status)

    def test_webhook_rejects_invalid_signature(self):
        order = self.create_order('INVALID')
        payload = self.signed_payload(order, 'APPROVED')
        payload['signature']['checksum'] = 'invalid'
        self.assertEqual(self.client.post(reverse('wompi-webhook'), payload, format='json').status_code, 401)

    @patch('ecommerce.views.requests.get')
    def test_status_endpoint_verifies_transaction_with_wompi(self, request_get):
        order = self.create_order('QUERY')
        provider_response = Mock()
        provider_response.raise_for_status.return_value = None
        provider_response.json.return_value = {'data': self.signed_payload(order, 'APPROVED')['data']['transaction']}
        request_get.return_value = provider_response
        response = self.client.get(reverse('wompi-payment-status'), {
            'tracking': str(order.tracking_code), 'transaction_id': 'TX-APPROVED',
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
