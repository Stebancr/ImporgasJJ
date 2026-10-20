from decimal import Decimal
from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from usuarios.models import Credenciales,Usuario
from usuarios.terms import CURRENT_TERMS_VERSION
from ecommerce.models import Brand,Category,Product,UserAddress,WompiPaymentIntent,Order,CartItem
from ecommerce import tests as checkout_tests
from ecommerce.pricing import totals


@override_settings(WOMPI_PUBLIC_KEY='pub_test_synthetic',WOMPI_INTEGRITY_SECRET='synthetic-only',
    WOMPI_EVENTS_SECRET='events-secret-for-tests',TRANSACTIONAL_EMAIL_ENABLED=False)
class CheckoutWithoutShippingTests(APITestCase):
    def setUp(self):
        profile=Usuario.objects.create(cedula='checkout-qa',nombre_completo='Synthetic client',
            correo='synthetic@example.invalid',terms_version=CURRENT_TERMS_VERSION,terms_accepted_at=timezone.now())
        self.user=Credenciales.objects.create(usuario='checkout-qa',estado=1,tipo_usuario=0,usuario_rel=profile)
        self.client.force_authenticate(self.user)
        self.product=Product.objects.create(name='Legacy product',price=125000,
            category=Category.objects.create(name='QA'),brand=Brand.objects.create(name='QA'))
        self.address=UserAddress.objects.create(user=self.user,label='QA',recipient_name='Receiver',
            phone='3000000000',address='Synthetic street',city='Cali',department='Valle',
            neighborhood='Synthetic district',complement='QA apt',delivery_instructions='QA instructions')
        self.payload={'customer_name':'Synthetic client','customer_email':'synthetic@example.invalid',
            'shipping_address':'Untrusted street','city':'Untrusted city','payment_method':'wompi',
            'address_id':self.address.pk,'wompi_reference':'QA-reference',
            'items':[{'product_id':self.product.pk,'quantity':1}]}
        CartItem.objects.create(user=self.user,product=self.product,quantity=1)

    def submit(self):
        return self.client.post(reverse('order-list'),self.payload,format='json')

    def test_backend_ignores_browser_prices_taxes_discounts_and_freight(self):
        self.payload.update(total=1,subtotal=1,taxes=-100000,discounts=125000,shipping_cost=999999)
        self.payload['items'][0]['unit_price']=1
        response=self.submit()
        self.assertEqual(response.status_code,201,response.data)
        intent=WompiPaymentIntent.objects.get()
        self.assertEqual(intent.total,125000)
        self.assertEqual(intent.subtotal,125000)
        self.assertEqual(intent.taxes,0);self.assertEqual(intent.discounts,0)
        self.assertIsNone(intent.shipping_cost)
        self.assertNotIn('shipping_cost',response.data['data'])
        self.assertEqual(intent.checkout_data['shipping_address'],'Synthetic street')
        self.assertEqual(intent.checkout_data['delivery_details']['complement'],'QA apt')
        self.assertEqual(CartItem.objects.get().quantity,1)

    def test_idempotence_different_address_rejected_and_cart_preserved(self):
        self.assertEqual(self.submit().status_code,201)
        self.assertEqual(self.submit().status_code,200)
        self.assertEqual(WompiPaymentIntent.objects.count(),1)
        self.address.address='Changed street';self.address.save()
        self.assertEqual(self.submit().status_code,409)
        self.assertEqual(WompiPaymentIntent.objects.get().checkout_data['shipping_address'],'Synthetic street')
        self.assertEqual(CartItem.objects.count(),1)

    def test_address_ownership_and_current_product_price(self):
        other=Credenciales.objects.create(usuario='other-qa',estado=1)
        self.address.user=other;self.address.save()
        self.assertEqual(self.submit().status_code,400)
        self.assertFalse(WompiPaymentIntent.objects.exists())
        self.address.user=self.user;self.address.save()
        self.product.price=2900000;self.product.save()
        self.assertEqual(self.submit().status_code,201)
        self.assertEqual(WompiPaymentIntent.objects.get().total,2900000)

    @patch('ecommerce.views.send_order_payment_confirmation')
    def test_signed_payment_materializes_address_and_snapshot_once(self,mail):
        self.assertEqual(self.submit().status_code,201)
        intent=WompiPaymentIntent.objects.get()
        payload=checkout_tests.WompiPaymentTests.signed_payload(self,intent,'APPROVED')
        for _ in range(2):
            response=self.client.post(reverse('wompi-webhook'),payload,format='json')
            self.assertEqual(response.status_code,200,response.data)
        order=Order.objects.get()
        self.assertEqual(order.total,125000);self.assertEqual(order.paid_total,125000)
        self.assertIsNone(order.shipping_cost)
        self.assertEqual(order.delivery_address_id,self.address.pk)
        self.assertEqual(order.delivery_details['neighborhood'],'Synthetic district')
        self.assertEqual(order.shipping_address,'Synthetic street')
        self.assertEqual(order.items.count(),1)
        mail.assert_called_once()
        self.address.delete();order.refresh_from_db()
        self.assertIsNone(order.delivery_address_id)
        self.assertEqual(order.shipping_address,'Synthetic street')
        self.assertEqual(order.delivery_details['complement'],'QA apt')

    def test_tax_discount_validation(self):
        self.assertEqual(totals(125000,taxes=1000,discounts=2000)['total'],Decimal(124000))
        for kwargs in ({'taxes':-1},{'discounts':126000},{'taxes':'NaN'}):
            with self.assertRaises(ValueError):totals(125000,**kwargs)
