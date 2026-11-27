"""Ajustes exclusivos del despliegue Docker de IMPORGAS JJ."""

import os
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403


DEBUG = False
if os.environ.get('DJANGO_SETTINGS_MODULE') == 'core.settings_production_worker':
    # Celery uses Django models and URL reversing but does not authenticate HTTP clients.
    _jwt_key = None
else:
    _jwt_key = os.environ.get('JWT_SIGNING_KEY', '')
    if len(_jwt_key) < 32 or _jwt_key == SECRET_KEY:
        raise ImproperlyConfigured('JWT_SIGNING_KEY must be an independent cryptographic key (at least 32 characters).')
SIMPLE_JWT = {**SIMPLE_JWT, 'SIGNING_KEY': _jwt_key}
ROOT_URLCONF = 'core.urls_production'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'backend',
    'nginx',
    'imporgasjj.com',
    'www.imporgasjj.com',
    '2.25.225.216',
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://www.imporgasjj.com',
]
CSRF_TRUSTED_ORIGINS = [
    'https://www.imporgasjj.com',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() == 'true'

STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'

SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30')),
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.getenv('JWT_REFRESH_DAYS', '1')),
    ),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_webhook_secrets': {
            '()': 'core.logging_filters.RedactWebhookSecretsFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['redact_webhook_secrets'],
        },
    },
    'root': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'crmChat': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
