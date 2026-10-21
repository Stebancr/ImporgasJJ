"""All carrier calls are intercepted. Never create a real shipment in tests."""
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.test import override_settings, skipUnlessDBFeature
from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient, APITransactionTestCase

from usuarios.models import Credenciales, Usuario
from usuarios.terms import CURRENT_TERMS_VERSION
from ecommerce.models import Brand, Category, Product, ProductStock, Location, CartItem, UserAddress, Order, WompiPaymentIntent
from .catalog import city
from .models import ProductShippingProfile, ShippingQuote, Shipment, ShipmentEvent
from .services import shipping_snapshot, quotation_payload, dispatch_payload
from .tcc import TCCClient, TCCError, safe_document_url
from .tasks import create_shipment, recover_pending_shipments


TEST_SETTINGS = dict(TCC_SHIPPING_ENABLED=True, TCC_DISPATCH_ENABLED=True,
    TCC_PQT_ACCOUNT='1485100', TCC_MSJ_ACCOUNT='5625200',
    TCC_API_ENVIRONMENT='development', TCC_API_TOKEN='synthetic-tcc-test-secret', TCC_PRODUCTION_APPROVED=False,
    TCC_ORIGIN_CITY_CODE='05001000', TCC_SENDER={'name':'Remitente QA','company':'QA', 'document_type':'NIT',
    'document':'900000000','address':'Dirección sintética QA','phone':'3000000000','email':'qa@example.invalid'},
    TCC_SHIPPING_MARKUP_PERCENT='0', TCC_SHIPPING_HANDLING_FEE='0',
    WOMPI_INTEGRITY_SECRET='integrity-test', WOMPI_EVENTS_SECRET='events-secret-for-tests',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')


@override_settings(**TEST_SETTINGS)
class TCCFlowTests(APITestCase):
    def setUp(self):
        cache.clear()  # core test settings use LocMemCache, never live Redis.
        profile = Usuario.objects.create(cedula='tcc-qa',nombre_completo='Cliente TCC QA',correo='qa@example.invalid',
            terms_accepted_at=timezone.now(),terms_version=CURRENT_TERMS_VERSION)
        self.user = Credenciales.objects.create(usuario='tcc-qa',usuario_rel=profile,estado=1,tipo_usuario=0)
        self.admin = Credenciales.objects.create(usuario='tcc-admin-qa',estado=1,tipo_usuario=4)
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(name='Producto TCC QA',description='Sintético',price=Decimal('125000'),
            brand=Brand.objects.create(name='TCC QA'),category=Category.objects.create(name='TCC QA'))
        self.profile = ProductShippingProfile.objects.create(product=self.product,weight_kg=2,height_cm=10,
            width_cm=10,length_cm=10,declared_value=125000)
        self.stock = ProductStock.objects.create(product=self.product,quantity=20,
            location=Location.objects.create(name='TCC QA',address='Dirección QA',city='QA'))
        self.cart = CartItem.objects.create(user=self.user,product=self.product,quantity=1)
        destination = city('11001000')
        self.payload = {'customer_name':'Destinatario QA','customer_email':'qa@example.invalid', 'customer_phone':'3000000000',
            'shipping_address':'Dirección sintética 2', 'city':destination['city'], 'department':destination['department'],
            'tcc_city_code':destination['code'], 'complement':'Apto QA','neighborhood':'Barrio QA','delivery_instructions':'Solo prueba',
            'payment_method':'wompi','wompi_reference':'TCC-REF-QA', 'items':[{'product_id':self.product.pk,'quantity':1}]}
        self.http = patch('shipping.tcc.requests.post').start()
        self.addCleanup(patch.stopall)
        self.http.side_effect = self.carrier
        self.enqueue = patch('shipping.services.enqueue_shipment').start()
        self.rate = '30000.00'
        self.dispatch_calls = 0

    def carrier(self, url, **kwargs):
        self.assertTrue(url.startswith('https://testsomos.tcc.com.co/'))
        self.assertEqual(kwargs['headers']['AccessToken'], 'synthetic-tcc-test-secret')
        self.assertFalse(kwargs['allow_redirects'])
        if url.endswith('/consultarliquidacion'):
            return Mock(status_code=200,json=lambda:{'codigoResultado':0,'total':{'totaldespacho':self.rate}})
        self.assertTrue(url.endswith('/grabardespacho8'))
        self.dispatch_calls += 1
        return Mock(status_code=200,json=lambda:{'remesas':[{'codigoresultado':0,'numeroremesa':'123456789'}],
            'numerorecogida':'QA-1','urlrotulos':'https://testsomos.tcc.com.co/qa/rotulo.pdf',
            'urlrelacionenvio':'http://localhost/private', 'urlremesa':'https://evil.example/private'})

    def quote(self, payload=None):
        response = self.client.post(reverse('shipping-quote'),payload or self.payload,format='json')
        self.assertEqual(response.status_code,200,response.data)
        return ShippingQuote.objects.get(pk=response.data['id'])

    def intent(self):
        quote = self.quote()
        response = self.client.post(reverse('order-list'),{**self.payload,'shipping_quote_id':str(quote.pk)},format='json')
        self.assertEqual(response.status_code,201,response.data)
        return WompiPaymentIntent.objects.get(reference=self.payload['wompi_reference'])

    def webhook(self, intent, state='APPROVED', amount=None):
        transaction = {'id':'TCC-TX-QA','reference':intent.reference,'status':state,
                       'amount_in_cents':int(intent.total*100) if amount is None else amount,'currency':'COP'}
        timestamp = 1700000000
        raw=f"{transaction['id']}{state}{transaction['amount_in_cents']}{timestamp}events-secret-for-tests"
        payload={'event':'transaction.updated','data':{'transaction':transaction},'timestamp':timestamp,
            'signature':{'properties':['transaction.id','transaction.status','transaction.amount_in_cents'],
                         'checksum':hashlib.sha256(raw.encode()).hexdigest()}}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('wompi-webhook'),payload,format='json')

    def paid(self):
        intent = self.intent()
        self.assertEqual(self.webhook(intent).status_code,200)
        intent.refresh_from_db()
        return intent.order.shipment

    def test_weight_thresholds_and_volume_from_supplied_plugin(self):
        for weight,length,expected,vol in [('2',10,'MSJ','0.40'),('5',10,'MSJ','0.40'),
                                           ('5.001',10,'PQT','0.40'),('2',200,'PQT','8.00')]:
            self.profile.weight_kg=Decimal(weight);self.profile.length_cm=length;self.profile.save()
            quote=self.quote()
            self.assertEqual(quote.account_type,expected)
            self.assertEqual(Decimal(quote.snapshot['volumetric_kg']),Decimal(vol))
            self.assertEqual(quote.snapshot['account'],'5625200' if expected=='MSJ' else '1485100')
            print('TCC WEIGHT real=%s volume=%s expected=%s obtained=%s PASS (mock)'%(weight,vol,expected,quote.account_type))

    def test_quantities_multiple_boxes_preserve_dimensions(self):
        self.cart.quantity=3;self.cart.save()
        self.profile.packages_per_unit=2;self.profile.save()
        quote=self.quote({**self.payload,'items':[{'product_id':self.product.pk,'quantity':3}]})
        self.assertEqual(len(quote.snapshot['packages']),6)
        self.assertEqual(Decimal(quote.snapshot['real_kg']),12)
        units=quotation_payload(quote.snapshot)['unidades']
        self.assertEqual(len(units),6)
        self.assertEqual({(u['alto'],u['ancho'],u['largo']) for u in units},{(10,10,10)})
        self.assertEqual(quote.account_type,'PQT')

    def test_missing_profile_dimensions_or_incomplete_address_block_quote(self):
        self.profile.height_cm=None;self.profile.save()
        self.assertEqual(self.client.post(reverse('shipping-quote'),self.payload,format='json').status_code,400)
        self.profile.height_cm=10;self.profile.save()
        for patch_value in ({'tcc_city_code':''},{'city':'Wrong city'},{'customer_phone':''},{'shipping_address':''}):
            self.assertEqual(self.client.post(reverse('shipping-quote'),{**self.payload,**patch_value},format='json').status_code,400)

    def test_profile_decimal_validation_and_publish_guard(self):
        self.client.force_authenticate(self.admin)
        url=reverse('product-detail',kwargs={'pk':self.product.pk})
        for field in ('weight_kg','height_cm','width_cm','length_cm','declared_value'):
            response=self.client.patch(url,{'shipping_profile':{field:'-1'}},format='json')
            self.assertEqual(response.status_code,400)
        response=self.client.patch(url,{'shipping_profile':{'weight_kg':None}},format='json')
        self.assertEqual(response.status_code,400)
        response=self.client.patch(url,{'is_available':False,'shipping_profile':{'weight_kg':None}},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.profile.refresh_from_db();self.assertIsNone(self.profile.weight_kg)
        # Republishing requires valid logistics; ordinary legacy edits remain allowed.
        self.assertEqual(self.client.patch(url,{'is_available':True},format='json').status_code,400)
        self.product.refresh_from_db()
        self.assertFalse(self.product.shipping_ready)

    def test_cache_and_address_history_owner_and_changes(self):
        address=UserAddress.objects.create(user=self.user,label='QA',recipient_name='Destinatario QA',phone='3000000000',
            address='Histórico QA',city=self.payload['city'],department=self.payload['department'],tcc_city_code='11001000')
        payload={**self.payload,'address_id':address.pk}
        quote=self.quote(payload)
        again=self.quote(payload)
        self.assertEqual(quote.pk,again.pk)
        self.assertEqual(self.http.call_count,1)
        self.rate = '35000.00'
        refreshed = self.quote({**payload, 'force': True})
        self.assertNotEqual(refreshed.pk, quote.pk)
        self.assertEqual(refreshed.tcc_rate, Decimal('35000.00'))
        address.address='Dirección nueva QA';address.save()
        updated=self.quote(payload)
        self.assertNotEqual(quote.pk,updated.pk)
        quote.refresh_from_db();self.assertEqual(quote.snapshot['address']['address'],'Histórico QA')
        stranger=Credenciales.objects.create(usuario='tcc-stranger-qa',estado=1,tipo_usuario=0)
        self.client.force_authenticate(stranger)
        CartItem.objects.create(user=stranger,product=self.product,quantity=1)
        self.assertEqual(self.client.post(reverse('shipping-quote'),payload,format='json').status_code,400)

    def test_expired_quote_or_cart_change_blocks_order(self):
        quote=self.quote()
        ShippingQuote.objects.filter(pk=quote.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.post(reverse('order-list'),{**self.payload,'shipping_quote_id':str(quote.pk)},format='json').status_code,400)
        quote=self.quote()
        self.cart.quantity=2;self.cart.save()
        self.assertEqual(self.client.post(reverse('order-list'),{**self.payload,'shipping_quote_id':str(quote.pk)},format='json').status_code,400)
        self.assertFalse(Order.objects.exists())

    def test_fresh_rate_change_cannot_be_charged_silently(self):
        quote=self.quote();self.rate='40000'
        response=self.client.post(reverse('order-list'),{**self.payload,'shipping_quote_id':str(quote.pk)},format='json')
        self.assertEqual(response.status_code,400)
        self.assertFalse(WompiPaymentIntent.objects.exists())

    @override_settings(TCC_SHIPPING_MARKUP_PERCENT='10',TCC_SHIPPING_HANDLING_FEE='2000')
    def test_legacy_markup_settings_cannot_add_to_carrier_rate(self):
        intent=self.intent()
        quote=intent.order.shipment.quote
        self.assertEqual((quote.tcc_rate,quote.surcharge,quote.total),(Decimal('30000'),Decimal('0'),Decimal('30000')))
        self.assertEqual(intent.total,Decimal('155000'))
        self.assertEqual(intent.order.total,intent.total)
        self.assertEqual(self.dispatch_calls,0)

    def test_payment_creates_one_waybill_and_inventory_only_after_approval(self):
        intent=self.intent()
        self.stock.refresh_from_db();self.assertEqual(self.stock.quantity,20)
        self.assertEqual(Order.objects.count(),1)
        shipment=intent.order.shipment
        self.assertEqual(shipment.state,'awaiting_payment')
        self.assertEqual(create_shipment.run(shipment.pk),{'skipped':'already_claimed_or_final'})
        self.assertEqual(self.webhook(intent,amount=100).status_code,400)
        self.assertEqual(self.webhook(intent).status_code,200)
        self.assertEqual(self.webhook(intent).status_code,200)
        self.stock.refresh_from_db();self.assertEqual(self.stock.quantity,19)
        self.assertEqual(Order.objects.count(),1)
        self.assertEqual(intent.order.items.count(),1)
        create_shipment.run(shipment.pk);create_shipment.run(shipment.pk)
        shipment.refresh_from_db()
        self.assertEqual(shipment.state,'created')
        self.assertEqual(self.dispatch_calls,1)
        self.assertEqual(shipment.waybill,'123456789')
        self.assertNotIn('relation',shipment.document_urls)
        self.assertNotIn('waybill',shipment.document_urls)
        self.assertEqual(shipment.events.filter(event_key='dispatch-confirmed').count(),1)
        payload=dispatch_payload(shipment)
        self.assertEqual(payload['destinatarios'][0]['numeroreferenciacliente'],shipment.order.order_number)
        self.assertNotIn('AccessToken',json.dumps(shipment.request_summary))

    def test_nonapproved_wompi_statuses_never_dispatch(self):
        intent=self.intent()
        for state in ('PENDING','DECLINED','VOIDED','ERROR'):
            self.assertEqual(self.webhook(intent,state).status_code,200)
            create_shipment.run(intent.order.shipment.pk)
        self.assertEqual(self.dispatch_calls,0)
        self.stock.refresh_from_db();self.assertEqual(self.stock.quantity,20)

    def test_carrier_outage_before_payment_is_safe(self):
        self.http.side_effect=requests.ConnectTimeout('secret-never-log')
        response=self.client.post(reverse('shipping-quote'),self.payload,format='json')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('secret-never-log',str(response.data))
        self.assertFalse(Order.objects.exists())

    def test_retry_after_connect_timeout_and_manual_audit(self):
        shipment=self.paid()
        self.http.side_effect=requests.ConnectTimeout()
        self.assertEqual(create_shipment.run(shipment.pk)['state'],'error')
        shipment.refresh_from_db();self.assertIsNotNone(shipment.next_attempt_at)
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post(reverse('shipping-action',kwargs={'order_id':shipment.order_id,'action':'retry'}))
        self.assertEqual(response.status_code,202)
        self.assertTrue(ShipmentEvent.objects.filter(shipment=shipment,actor=self.admin).exists())
        self.http.side_effect=self.carrier
        self.assertEqual(create_shipment.run(shipment.pk)['state'],'created')

    def test_read_timeout_and_worker_crash_never_blindly_retry(self):
        shipment=self.paid()
        self.http.side_effect=requests.ReadTimeout('sensitive-content')
        self.assertEqual(create_shipment.run(shipment.pk)['state'],'uncertain')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(reverse('shipping-action',kwargs={'order_id':shipment.order_id,'action':'retry'})).status_code,409)
        calls=self.http.call_count
        create_shipment.run(shipment.pk);recover_pending_shipments.run()
        self.assertEqual(self.http.call_count,calls)
        Shipment.objects.filter(pk=shipment.pk).update(state='creating',started_at=timezone.now()-timedelta(minutes=4))
        recover_pending_shipments.run()
        shipment.refresh_from_db();self.assertEqual(shipment.state,'uncertain')

    def test_client_admin_visibility_and_deferred_tracking(self):
        shipment=self.paid();create_shipment.run(shipment.pk)
        detail=reverse('order-detail',kwargs={'pk':shipment.order_id})
        response=self.client.get(detail)
        self.assertEqual(response.status_code,200)
        public=response.data['data']['shipment']
        self.assertIn('tcc.com.co/rastreo',public['tracking_url'])
        self.assertNotIn('documents',public)
        self.assertNotIn('account',public)
        self.assertFalse(public['tracking_api_available'])
        self.client.force_authenticate(self.admin)
        admin=self.client.get(f'/ecommerce/admin/orders/{shipment.order_id}')
        self.assertEqual(admin.status_code,200,admin.data)
        self.assertEqual(admin.data['data']['shipment']['account_type'],'MSJ')
        self.assertIn('label',admin.data['data']['shipment']['documents'])
        self.assertEqual(self.client.post(reverse('shipping-action',kwargs={'order_id':shipment.order_id,'action':'sync'})).status_code,409)
        response=self.client.patch(f'/ecommerce/admin/orders/{shipment.order_id}',{'status':'delivered'},format='json')
        self.assertEqual(response.status_code,409)

    def test_digital_profile_needs_no_transport_dimensions_or_carrier_call(self):
        self.profile.requires_shipping=False;self.profile.weight_kg=None;self.profile.save()
        quote=self.quote()
        self.assertEqual(quote.total,0)
        self.assertEqual(quote.snapshot['packages'],[])
        self.http.assert_not_called()

    @override_settings(TCC_DISPATCH_ENABLED=False)
    def test_safety_switch_never_creates_real_dispatch(self):
        shipment=self.paid()
        self.assertEqual(create_shipment.run(shipment.pk),{'skipped':'dispatch_disabled'})
        self.assertEqual(self.dispatch_calls,0)

    def test_ssrf_and_production_credentials_fail_closed(self):
        for url in ('http://somos.tcc.com.co/doc','https://localhost/a','https://127.0.0.1/a',
                    'https://somos.tcc.com.co.evil.example/a','https://somos.tcc.com.co:bad/a','https://user@somos.tcc.com.co/a'):
            self.assertEqual(safe_document_url(url),'')
        with override_settings(TCC_API_ENVIRONMENT='production',TCC_PRODUCTION_APPROVED=False):
            with self.assertRaises(TCCError):TCCClient()
        with override_settings(TCC_API_ENVIRONMENT='production',TCC_PRODUCTION_APPROVED=True,TCC_PRODUCTION_API_TOKEN=''):
            with self.assertRaises(TCCError):TCCClient()

    def test_rate_validation_rejects_nonfinite_and_provider_body_is_not_exposed(self):
        for body in ({'codigoResultado':-1,'mensajeResultado':'synthetic-tcc-test-secret'},
                     {'codigoResultado':0,'total':{'totaldespacho':'NaN'}}, {'codigoResultado':0,'total':{'totaldespacho':'-1'}}):
            self.http.side_effect=None;self.http.return_value=Mock(status_code=200,json=lambda:body)
            response=self.client.post(reverse('shipping-quote'),self.payload,format='json')
            self.assertEqual(response.status_code,503)
            self.assertNotIn('synthetic-tcc-test-secret',str(response.data))

    def test_missing_route_rate_is_reported_without_provider_payload(self):
        self.http.side_effect = None
        self.http.return_value = Mock(status_code=200, json=lambda: {'codigoResultado': -1,
            'mensajeResultado': 'synthetic-tcc-test-secret {"errors":["No existe tarifa para la ruta solicitada"]}'})
        response = self.client.post(reverse('shipping-quote'), self.payload, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['code'], 'route_not_configured')
        self.assertNotIn('synthetic-tcc-test-secret', str(response.data))

    def test_multiple_products_and_profile_changes_invalidate_quote(self):
        second = Product.objects.create(name='Segundo QA', price=50000, brand=self.product.brand, category=self.product.category)
        ProductShippingProfile.objects.create(product=second, weight_kg=3, height_cm=10, width_cm=10,
            length_cm=10, declared_value=50000, packages_per_unit=2)
        CartItem.objects.create(user=self.user, product=second, quantity=2)
        payload = {**self.payload, 'items': [*self.payload['items'], {'product_id': second.pk, 'quantity': 2}]}
        quote = self.quote(payload)
        self.assertEqual(quote.snapshot['real_kg'], '14.000')
        self.assertEqual(len(quote.snapshot['packages']), 5)
        self.assertEqual(quote.account_type, 'PQT')
        self.profile.height_cm = 20
        self.profile.save()
        response = self.client.post(reverse('order-list'), {**payload, 'shipping_quote_id': str(quote.pk)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_sender_identity_is_not_taken_from_buyer(self):
        with override_settings(TCC_SENDER={}, TCC_DISPATCH_ENABLED=False):
            self.assertEqual(self.quote().total, Decimal('30000'))
        with override_settings(TCC_SENDER={}, TCC_DISPATCH_ENABLED=True):
            self.assertEqual(self.client.post(reverse('shipping-quote'), self.payload, format='json').status_code, 503)

    def test_cancelled_draft_is_not_reopened_or_dispatched_by_late_payment(self):
        intent = self.intent()
        order = intent.order
        order.status = 'cancelled'
        order.save()
        self.assertEqual(self.webhook(intent).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.wompi_status, 'APPROVED')
        from .serializers import shipment_data
        self.assertEqual(shipment_data(order)['state_label'], 'Orden cancelada localmente; despacho no solicitado')
        self.assertTrue(order.shipment.events.filter(event_key='payment-after-local-cancellation').exists())
        self.assertEqual(create_shipment.run(order.shipment.pk), {'skipped': 'already_claimed_or_final'})
        self.assertEqual(self.dispatch_calls, 0)


@override_settings(**TEST_SETTINGS)
class TCCConcurrencyTests(APITransactionTestCase):
    setUp = TCCFlowTests.setUp
    carrier = TCCFlowTests.carrier
    quote = TCCFlowTests.quote
    intent = TCCFlowTests.intent

    @skipUnlessDBFeature('has_select_for_update')
    def test_two_workers_only_send_one_dispatch(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import connection, close_old_connections
        intent = self.intent()
        intent.wompi_status, intent.processed_at = 'APPROVED', timezone.now()
        intent.save()
        order = intent.order
        order.status = 'paid'
        order.save()
        shipment = order.shipment
        shipment.state = 'pending'
        shipment.save()
        entered, release = Event(), Event()
        def carrier(url, **kwargs):
            entered.set()
            if not release.wait(15):
                raise RuntimeError('Test worker coordination timed out')
            return self.carrier(url, **kwargs)
        self.http.side_effect = carrier
        def worker():
            close_old_connections()
            try:
                return create_shipment.run(shipment.pk)
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker)
            try:
                self.assertTrue(entered.wait(10))
                self.assertEqual(pool.submit(worker).result(timeout=10), {'skipped': 'already_claimed_or_final'})
            finally:
                release.set()
            self.assertEqual(first.result(timeout=10), {'state': 'created'})
        self.assertEqual(self.dispatch_calls, 1)
        shipment.refresh_from_db()
        self.assertEqual(shipment.waybill, '123456789')
