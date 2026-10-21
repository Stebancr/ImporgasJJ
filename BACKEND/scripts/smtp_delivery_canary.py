"""Explicit, development-only real SMTP canary on a dedicated Celery queue.

Uses the actual recovery delivery service; only prefixes the test subject.
Never imported by the regular application's task discovery.
"""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from core.celery import app
from usuarios import password_recovery as recovery
from usuarios.models import Credenciales, PasswordResetDelivery

QUEUE = 'smtp-tls-canary'
MARKER = 'authorized_development_smtp_canary'


def guard():
    if (not settings.DEBUG or os.getenv('SMTP_CANARY_ENABLED') != '1'
            or urlsplit(settings.FRONTEND_PUBLIC_URL).hostname != 'localhost'
            or urlsplit(settings.FRONTEND_PUBLIC_URL).scheme != 'http'
            or len(settings.PASSWORD_RESET_ALLOWED_RECIPIENTS) != 1):
        raise ImproperlyConfigured('Requires explicit local development canary and exactly one authorized recipient.')


@app.task(name='diagnostics.smtp_delivery_canary', ignore_result=True)
def deliver_canary(event_id):
    guard()
    event = PasswordResetDelivery.objects.select_related('user__usuario_rel').get(pk=event_id)
    if event.state != 'pending' or event.last_error != MARKER:
        return False
    recipient = settings.PASSWORD_RESET_ALLOWED_RECIPIENTS[0].lower()
    if not event.user or not event.user.usuario_rel or event.user.usuario_rel.correo.lower() != recipient:
        return False
    original = recovery.build_email
    def build_test_message(user):
        message = original(user)
        if message.to != [recipient] or message.cc or message.bcc:
            raise ImproperlyConfigured('Canary recipient mismatch.')
        message.subject = '[PRUEBA DESARROLLO] ' + message.subject
        message.extra_headers['Message-ID'] = f'<smtp-dev-{event.pk}@imporgasjj.com>'
        return message
    recovery.build_email = build_test_message
    try:
        return recovery.deliver(event.pk)
    finally:
        recovery.build_email = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--enqueue', action='store_true')
    options = parser.parse_args()
    guard()
    if options.worker:
        app.worker_main(['worker','--pool=solo','--concurrency=1','--loglevel=WARNING',
                         '-Q',QUEUE,'--hostname=smtp-canary@%h'])
    elif options.enqueue:
        recipient = settings.PASSWORD_RESET_ALLOWED_RECIPIENTS[0].lower()
        with transaction.atomic():
            user = Credenciales.objects.select_for_update().get(usuario_rel__correo__iexact=recipient)
            if not recovery.eligible(user):
                raise ImproperlyConfigured('Canary account is unavailable.')
            if PasswordResetDelivery.objects.filter(user=user, last_error=MARKER).exists():
                raise ImproperlyConfigured('A canary was already queued; review its result instead of resending.')
            # Also reject a previously successful canary whose marker was cleared by delivery.
            if PasswordResetDelivery.objects.filter(user=user, state='sent').exists():
                raise ImproperlyConfigured('A delivery already succeeded for this QA account; manual review required.')
            user.password_reset_version += 1
            user.save(update_fields=['password_reset_version'])
            event = PasswordResetDelivery.objects.create(user=user, version=user.password_reset_version,
                recipient_hash=recovery.email_hash(recipient), last_error=MARKER)
        app.send_task('diagnostics.smtp_delivery_canary', args=[str(event.pk)], queue=QUEUE, retry=False)
        print('canary_queued=true event=' + str(event.pk) + ' queue=' + QUEUE + ' no_cc_bcc=true')
    else:
        parser.error('Choose --worker or --enqueue.')


if __name__ == '__main__':
    main()
