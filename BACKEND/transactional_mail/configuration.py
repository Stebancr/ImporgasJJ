from email.utils import parseaddr
import ipaddress
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def validate_smtp():
    if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
        return
    if settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
        raise ImproperlyConfigured('EMAIL_USE_SSL y EMAIL_USE_TLS no pueden activarse simultáneamente.')
    if not 1 <= settings.EMAIL_PORT <= 65535 or not 1 <= settings.EMAIL_TIMEOUT <= 60:
        raise ImproperlyConfigured('Revisa EMAIL_PORT y EMAIL_TIMEOUT (1 a 60 segundos).')
    if settings.EMAIL_HOST in ('smtp-relay.brevo.com', 'smtp-relay.sendinblue.com'):
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise ImproperlyConfigured('Brevo requiere EMAIL_HOST_USER y EMAIL_HOST_PASSWORD (credencial SMTP, no clave API).')
        if settings.EMAIL_PORT != 587 or not settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL:
            raise ImproperlyConfigured('Brevo requiere puerto 587 con TLS activado y SSL desactivado en esta configuración.')
    if not parseaddr(settings.DEFAULT_FROM_EMAIL)[1]:
        raise ImproperlyConfigured('Configura DEFAULT_FROM_EMAIL.')


def public_url(path='', api=False):
    base = (settings.PUBLIC_API_URL if api else settings.FRONTEND_PUBLIC_URL).rstrip('/')
    url = urlsplit(base)
    host = (url.hostname or '').lower()
    private_host = host == 'localhost' or host.endswith(('.local', '.internal', '.localhost'))
    try:
        private_host = private_host or not ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    if (url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment
            or (not settings.DEBUG and (url.scheme != 'https' or private_host))
            or (url.hostname != 'localhost' and '.' not in url.hostname)):
        raise ImproperlyConfigured('URL pública inválida; producción requiere un dominio HTTPS.')
    return base + '/' + path.lstrip('/')
