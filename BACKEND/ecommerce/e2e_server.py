"""Docker-only synthetic browser fixture. Never serves the development database."""
import json
import os
import sys
import threading
import uuid
from wsgiref.simple_server import make_server, WSGIRequestHandler
from unittest.mock import patch


def main():
    if '--isolated-e2e' not in sys.argv or os.environ.get('CRM_TEST_POSTGRES') != '1':
        raise SystemExit('Explicit isolated test flags required.')
    for key in list(os.environ):
        if key.startswith('TCC_'):
            del os.environ[key]
    sys.argv.append('test')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from django.db import connection
    from django.test import override_settings
    from django.test.utils import setup_databases, teardown_databases
    from django.core.wsgi import get_wsgi_application
    from django.utils import timezone
    from usuarios.models import Credenciales, Usuario
    from usuarios.terms import CURRENT_TERMS_VERSION
    from ecommerce.models import Product, Category, Brand, Location, ProductStock

    name = 'test_general_e2e_' + uuid.uuid4().hex[:12]
    connection.settings_dict['TEST']['NAME'] = name
    config = setup_databases(verbosity=0, interactive=False)
    class QuietHandler(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    try:
        with override_settings(ALLOWED_HOSTS=['*'], MEDIA_ROOT='/tmp/general-e2e-media',
                TRANSACTIONAL_EMAIL_ENABLED=False, WOMPI_PUBLIC_KEY='pub_test_synthetic',
                WOMPI_INTEGRITY_SECRET='synthetic-fixture-only'), patch('requests.sessions.Session.request', side_effect=AssertionError('External traffic disabled')):
            for username, role in [('general-e2e-client', 0), ('general-e2e-admin', 4)]:
                profile = Usuario.objects.create(cedula=username, nombre_completo='General QA',
                    correo=username+'@example.invalid', telefono='3000000000',
                    terms_version=CURRENT_TERMS_VERSION, terms_accepted_at=timezone.now())
                credential = Credenciales.objects.create(usuario=username, usuario_rel=profile, estado=1, tipo_usuario=role)
                credential.set_password('General-synthetic-fixture-only'); credential.save()
            product = Product.objects.create(name='Producto general QA', price=125000,
                category=Category.objects.create(name='QA'), brand=Brand.objects.create(name='QA'))
            ProductStock.objects.create(product=product, quantity=20,
                location=Location.objects.create(name='QA', address='QA', city='Cali'))
            app = get_wsgi_application()
            def handler(environ, start_response):
                if environ.get('PATH_INFO') in ('/__qa/state', '/__qa/stop'):
                    assert connection.settings_dict['NAME'] == name
                    start_response('200 OK', [('Content-Type', 'application/json')])
                    if environ['PATH_INFO'] == '/__qa/stop':
                        threading.Thread(target=server.shutdown, daemon=True).start()
                    return [json.dumps({'database_isolated': True, 'product_id': product.pk}).encode()]
                return app(environ, start_response)
            server = make_server('0.0.0.0', 8099, handler, handler_class=QuietHandler)
            timer = threading.Timer(600, server.shutdown); timer.start()
            print('GENERAL_E2E_READY isolated_database=true external_traffic=blocked', flush=True)
            try:
                server.serve_forever()
            finally:
                timer.cancel(); server.server_close()
    finally:
        teardown_databases(config, verbosity=0)


if __name__ == '__main__':
    main()
