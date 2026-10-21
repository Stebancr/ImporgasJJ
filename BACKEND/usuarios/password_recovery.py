"""Customer-only recovery. Queue arguments and audit records never contain secrets."""
import logging
import smtplib
import ssl
from email.utils import formataddr
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from transactional_mail.configuration import public_url, validate_smtp
from transactional_mail.branding import logo_context, attach_logo
from .models import Credenciales, PasswordResetDelivery

logger = logging.getLogger(__name__)
SUBJECT = 'Restablece tu contraseña de ImporGas JJ'


class RecoveryTokens(PasswordResetTokenGenerator):
    key_salt = 'usuarios.customer.password.recovery.v1'

    def _make_hash_value(self, user, timestamp):
        profile = user.usuario_rel
        return super()._make_hash_value(user, timestamp) + str((
            user.password_reset_version, user.password_version, user.usuario,
            user.estado, user.tipo_usuario,
            profile.correo if profile else '', profile.estado if profile else 0,
        ))


tokens = RecoveryTokens()


def email_hash(email):
    return salted_hmac('password-reset-recipient', email.lower()).hexdigest()


def sender():
    address = settings.SERVER_EMAIL_NOREPLY
    try:
        validate_email(address)
    except ValidationError:
        raise ImproperlyConfigured('SERVER_EMAIL_NOREPLY') from None
    return formataddr(('ImporGas JJ - No responder', address), charset='utf-8')


def eligible(user):
    return bool(user and user.estado == 1 and user.tipo_usuario == 0 and user.has_usable_password()
                and user.usuario_rel and user.usuario_rel.estado == 1 and user.usuario_rel.correo)


def request_reset(email):
    key = email_hash(email)
    # Same limits for known and unknown email addresses; caller always responds neutrally.
    try:
        if not cache.add('reset:cooldown:' + key, 1, 60):
            return
        hour_key = 'reset:hour:' + key
        cache.add(hour_key, 0, 3600)
        if cache.incr(hour_key) > 3:
            return
    except Exception:
        logger.warning('password_reset state=unavailable reason=rate_limit_cache')
        return
    with transaction.atomic():
        users = list(Credenciales.objects.select_for_update(of=('self',)).filter(
            Q(usuario_rel__correo__iexact=email) | Q(usuario__iexact=email),
            tipo_usuario=0, estado=1).order_by('pk')[:2])
        user = users[0] if len(users) == 1 and eligible(users[0]) else None
        # A login alias must not redirect mail to an unrelated profile address.
        if user and user.usuario_rel.correo.strip().lower() != email:
            user = None
        version = 0
        if user:
            user.password_reset_version += 1
            user.save(update_fields=['password_reset_version'])
            version = user.password_reset_version
        delivery = PasswordResetDelivery.objects.create(user=user, version=version, recipient_hash=key)
        transaction.on_commit(lambda: enqueue(delivery.pk))


def enqueue(delivery_id):
    from .tasks import deliver_password_reset
    try:
        deliver_password_reset.apply_async(args=[str(delivery_id)], retry=False)
    except Exception:
        PasswordResetDelivery.objects.filter(pk=delivery_id).update(state='failed', last_error='queue_unavailable')
        logger.warning('password_reset state=failed reason=queue_unavailable')


def build_email(user):
    from_email = sender()
    validate_smtp()
    link = public_url('/restablecer-contrasena') + '#' + urlencode({
        'uid': urlsafe_base64_encode(force_bytes(user.pk)), 'token': tokens.make_token(user),
    })
    context = {**logo_context(), 'reset_url': link, 'minutes': max(1, settings.PASSWORD_RESET_TIMEOUT // 60),
               'contact': getattr(settings, 'TRANSACTIONAL_REPLY_TO', '')}
    message = EmailMultiAlternatives(SUBJECT,
        render_to_string('usuarios/password_reset.txt', context), from_email,
        [user.usuario_rel.correo],
        connection=get_connection(timeout=min(settings.EMAIL_TIMEOUT, 10)))
    message.attach_alternative(render_to_string('usuarios/password_reset.html', context), 'text/html')
    attach_logo(message, context)
    return message


def deliver(delivery_id):
    with transaction.atomic():
        event = PasswordResetDelivery.objects.select_for_update().get(pk=delivery_id)
        if event.state != 'pending':
            return False
        user = Credenciales.objects.filter(pk=event.user_id).first()
        if (not eligible(user) or user.password_reset_version != event.version
                or (timezone.now() - event.created_at).total_seconds() > settings.PASSWORD_RESET_TIMEOUT
                or email_hash(user.usuario_rel.correo) != event.recipient_hash):
            event.state = 'skipped'
            event.save(update_fields=['state'])
            return False
        event.state = 'sending'
        event.save(update_fields=['state'])
    state, error = 'sent', ''
    try:
        if (settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
                and user.usuario_rel.correo.lower() not in [s.lower() for s in settings.PASSWORD_RESET_ALLOWED_RECIPIENTS]):
            raise ImproperlyConfigured('PASSWORD_RESET_ALLOWED_RECIPIENTS')
        if build_email(user).send() != 1:
            raise smtplib.SMTPException()
    except ImproperlyConfigured as exc:
        state = 'failed'
        name = str(exc)
        error = 'configuration_' + (name if name in ('SERVER_EMAIL_NOREPLY', 'PASSWORD_RESET_ALLOWED_RECIPIENTS') else 'invalid')
    except ssl.SSLCertVerificationError:
        state, error = 'failed', 'smtp_tls_certificate'
    except smtplib.SMTPSenderRefused:
        state, error = 'failed', 'smtp_sender_rejected'
    except smtplib.SMTPAuthenticationError:
        state, error = 'failed', 'smtp_authentication'
    except (TimeoutError, smtplib.SMTPServerDisconnected):
        state, error = 'uncertain', 'smtp_delivery_uncertain'
    except Exception:
        state, error = 'failed', 'mail_unavailable'
    PasswordResetDelivery.objects.filter(pk=event.pk).update(state=state, last_error=error, completed_at=timezone.now())
    logger.info('password_reset delivery=%s state=%s reason=%s', event.pk, state, error or 'none')
    return state == 'sent'
