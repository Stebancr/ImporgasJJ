"""One explicit development-only delivery; no passwords or links in command output."""
import secrets
from unittest.mock import patch
from email.utils import parseaddr
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.test import override_settings
from transactional_mail.configuration import public_url, validate_smtp
from usuarios.models import Usuario, Credenciales, PasswordResetDelivery
from usuarios.password_recovery import request_reset, deliver, sender


class Command(BaseCommand):
    help = 'One authorized development-only password recovery SMTP test; refuses to overwrite an existing account.'

    def add_arguments(self, parser):
        parser.add_argument('--recipient', required=True)
        parser.add_argument('--send', action='store_true')

    def handle(self, *args, **options):
        if not settings.DEBUG or not options['send']:
            raise CommandError('Requires DEBUG development and explicit --send.')
        recipient = options['recipient'].strip().lower()
        try:
            validate_email(recipient)
            address = parseaddr(sender())[1]
            validate_smtp()
            url = public_url()
        except Exception:
            raise CommandError('Invalid sender, SMTP or FRONTEND_PUBLIC_URL configuration; values suppressed.') from None
        if not url.startswith(('http://localhost/', 'http://127.0.0.1/')):
            raise CommandError('Controlled test requires the local development frontend.')
        with transaction.atomic():
            if (Credenciales.objects.filter(Q(usuario__iexact=recipient) | Q(usuario_rel__correo__iexact=recipient)).exists()
                    or Usuario.objects.filter(correo__iexact=recipient).exists()):
                raise CommandError('Account already exists: no password changed and no message sent. Review before reusing.')
            profile = Usuario.objects.create(cedula='qa-recovery-'+secrets.token_hex(6), nombre_completo='Prueba recuperación desarrollo', correo=recipient)
            user = Credenciales.objects.create(usuario=recipient, usuario_rel=profile, tipo_usuario=0, estado=1)
            user.set_password(secrets.token_urlsafe(40))
            user.save(update_fields=['password'])
        with override_settings(PASSWORD_RESET_ALLOWED_RECIPIENTS=[recipient]), patch('usuarios.password_recovery.enqueue', side_effect=deliver):
            request_reset(recipient)
        event = PasswordResetDelivery.objects.filter(user=user).latest('created_at')
        self.stdout.write(f'development=true account_created=true recipient={recipient} from={address} cc=none bcc=none')
        self.stdout.write(f'delivery={event.pk} state={event.state} reason={event.last_error or "none"} completed_at={event.completed_at}')
        if event.state != 'sent':
            self.stdout.write('No automatic resend attempted. Account preserved; password not disclosed.')
