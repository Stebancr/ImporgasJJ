"""Isolated Docker-only browser test backend. Never serve a real database.

Run with CRM_TEST_POSTGRES=1 python -m shipping.e2e_server --tcc-e2e.
TCC, email and dispatch queuing are intercepted; Wompi events are synthetic.
"""
import sys
import os
import json
import threading
import uuid
from unittest.mock import Mock, patch
from wsgiref.simple_server import make_server, WSGIRequestHandler


def main():
    if '--tcc-e2e' not in sys.argv or os.environ.get('CRM_TEST_POSTGRES') != '1':
        raise SystemExit('Requires explicit isolated test flags.')
    sys.argv.append('test')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.test import override_settings
    from django.test.utils import setup_databases, teardown_databases
    from django.core.wsgi import get_wsgi_application
    from django.db import connection
    from django.urls import reverse
    from django.utils import timezone
    from usuarios.models import Credenciales, Usuario
    from usuarios.terms import CURRENT_TERMS_VERSION
    from ecommerce.models import Product, Category, Brand, Location, ProductStock, Order, WompiPaymentIntent, UserAddress
    from shipping.models import ProductShippingProfile, Shipment
    from shipping.tasks import create_shipment
    from shipping.tests import TEST_SETTINGS

    database_name = 'test_tcc_e2e_' + uuid.uuid4().hex[:12]
    connection.settings_dict['TEST']['NAME'] = database_name
    config = setup_databases(verbosity=0, interactive=False)
    assert connection.settings_dict['NAME'] == database_name
    overrides = {**TEST_SETTINGS, 'ALLOWED_HOSTS': ['*'], 'MEDIA_ROOT': '/tmp/tcc-e2e-media',
                 'TCC_ORIGIN_CITY_CODE': '76001000', 'WOMPI_PUBLIC_KEY': 'pub_test_e2e_synthetic'}
    counter = {'dispatch_calls': 0}
    class QuietHandler(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    def carrier(url, **kwargs):
        assert kwargs['headers']['AccessToken'] == 'synthetic-tcc-test-secret'
        assert url.startswith('https://testsomos.tcc.com.co/')
        if url.endswith('/consultarliquidacion'):
            return Mock(status_code=200, json=lambda: {'codigoResultado': 0, 'total': {'totaldespacho': '30000.00'}})
        assert url.endswith('/grabardespacho8')
        counter['dispatch_calls'] += 1
        return Mock(status_code=200, json=lambda: {'remesas':[{'codigoresultado':0,'numeroremesa':'999000001'}]})
    try:
        with override_settings(**overrides), patch('shipping.tcc.requests.post', side_effect=carrier), \
                patch('shipping.services.enqueue_shipment', side_effect=lambda pk: create_shipment.run(pk)), \
                patch('ecommerce.views.send_order_payment_confirmation'):
            for username, role in [('tcc-e2e-client', 0), ('tcc-e2e-admin', 4), ('dest@qa.invalid', 0)]:
                profile = Usuario.objects.create(cedula=username, nombre_completo='TCC QA', correo=username if '@' in username else username+'@example.invalid',
                    telefono='3000000000', terms_version=CURRENT_TERMS_VERSION, terms_accepted_at=timezone.now())
                credential = Credenciales.objects.create(usuario=username, usuario_rel=profile, estado=1, tipo_usuario=role)
                credential.set_password('TCC-synthetic-fixture-only'); credential.save()
            product = Product.objects.create(name='TCC integración QA', price=125000,
                category=Category.objects.create(name='QA'), brand=Brand.objects.create(name='QA'))
            ProductShippingProfile.objects.create(product=product, weight_kg=6, height_cm=10, width_cm=10, length_cm=10, declared_value=125000)
            ProductStock.objects.create(product=product, quantity=20, location=Location.objects.create(name='QA', address='QA', city='Cali'))
            app = get_wsgi_application()
            def handler(environ, start_response):
                path = environ.get('PATH_INFO')
                if path in ('/__qa/state', '/__qa/stop'):
                    assert connection.settings_dict['NAME'] == database_name
                    result = {**counter, 'orders': Order.objects.count(), 'intents': WompiPaymentIntent.objects.count(),
                        'shipments': Shipment.objects.count(), 'addresses': UserAddress.objects.count(), 'database_isolated': True,
                        'product_id': product.pk, 'webhook_path': reverse('wompi-webhook'),
                        'rows': list(Order.objects.values('id','subtotal','shipping_cost','discounts','taxes','total','paid_total')),
                        'waybills': list(Shipment.objects.values_list('waybill', flat=True))}
                    start_response('200 OK', [('Content-Type','application/json')])
                    if path == '/__qa/stop':
                        threading.Thread(target=server.shutdown, daemon=True).start()
                    return [json.dumps(result, default=str).encode()]
                return app(environ, start_response)
            server = make_server('0.0.0.0', 8099, handler, handler_class=QuietHandler)
            timer = threading.Timer(600, server.shutdown)
            timer.start()
            print('TCC_E2E_READY isolated_postgresql=true external_carrier=mock payment=synthetic', flush=True)
            try:
                server.serve_forever()
            finally:
                timer.cancel(); server.server_close()
    finally:
        teardown_databases(config, verbosity=0)
        print('TCC_E2E_FINISHED isolated_database_removed=true', flush=True)


if __name__ == '__main__':
    main()
