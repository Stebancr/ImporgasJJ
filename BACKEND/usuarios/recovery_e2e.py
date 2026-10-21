"""Docker-only, synthetic PostgreSQL browser fixture; never uses an existing database."""
import json
import os
import sys
import threading
import uuid
from unittest.mock import patch
from wsgiref.simple_server import make_server, WSGIRequestHandler


def main():
    if '--isolated-password-test' not in sys.argv or os.getenv('CRM_TEST_POSTGRES') != '1':
        raise SystemExit('Requires isolated Docker test flags.')
    sys.argv.append('test')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.test import override_settings
    from django.test.utils import setup_databases, teardown_databases
    from django.core import mail
    from django.core.wsgi import get_wsgi_application
    from django.db import connection
    from django.utils import timezone
    from .models import Usuario, Credenciales, PasswordResetDelivery
    from .password_recovery import deliver
    from .terms import CURRENT_TERMS_VERSION
    name = 'test_password_browser_' + uuid.uuid4().hex[:10]
    connection.settings_dict['TEST']['NAME'] = name
    config = setup_databases(verbosity=0, interactive=False)
    assert connection.settings_dict['NAME'] == name
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    try:
        with override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], SERVER_EMAIL_NOREPLY='reset@example.invalid',
                FRONTEND_PUBLIC_URL='http://crm.localhost', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'), \
                patch('usuarios.password_recovery.enqueue', side_effect=deliver):
            profile = Usuario.objects.create(cedula='browser-password-fixture', nombre_completo='Cliente QA', correo='browser-reset@example.invalid',
                terms_version=CURRENT_TERMS_VERSION, terms_accepted_at=timezone.now())
            user = Credenciales.objects.create(usuario=profile.correo, usuario_rel=profile, estado=1, tipo_usuario=0)
            user.set_password('Browser-old-synthetic-942!'); user.save()
            app = get_wsgi_application()
            def handler(environ, start_response):
                if environ.get('PATH_INFO') == '/__qa/mail':
                    # Only accessible on this explicitly isolated fixture, never a project URL.
                    assert connection.settings_dict['NAME'] == name
                    messages = getattr(mail, 'outbox', [])
                    result = {'count': len(messages), 'body': messages[-1].body if messages else '',
                              'states': list(PasswordResetDelivery.objects.values_list('state', flat=True))}
                    start_response('200 OK', [('Content-Type','application/json')])
                    return [json.dumps(result).encode()]
                return app(environ, start_response)
            server = make_server('0.0.0.0', 8098, handler, handler_class=Quiet)
            timer = threading.Timer(600, server.shutdown); timer.start()
            print('PASSWORD_BROWSER_READY isolated=true smtp=locmem', flush=True)
            try:
                server.serve_forever()
            finally:
                timer.cancel(); server.server_close()
    finally:
        teardown_databases(config, verbosity=0)


if __name__ == '__main__':
    main()
