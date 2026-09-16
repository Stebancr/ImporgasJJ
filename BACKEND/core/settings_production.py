"""Ajustes exclusivos del despliegue Docker de IMPORGAS JJ."""

import os
from datetime import timedelta

from .settings import *  # noqa: F401,F403


DEBUG = False
ROOT_URLCONF = 'core.urls_production'

ALLOWED_HOSTS = [
    'imporgasjj.com',
    'www.imporgasjj.com',
    '.djsolutions.io',
    'djsolutions.io',
    'www.djsolutions.io',
    '2.25.225.216',
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://imporgasjj.com',
    'https://www.imporgasjj.com',
    'https://djsolutions.io',
    'https://www.djsolutions.io',
]
CORS_ALLOWED_ORIGIN_REGEXES = [r'^https://([a-z0-9-]+\.)*djsolutions\.io$']
CSRF_TRUSTED_ORIGINS = [
    'https://imporgasjj.com',
    'https://www.imporgasjj.com',
    'https://djsolutions.io',
    'https://www.djsolutions.io',
    'https://*.djsolutions.io',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '3600'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False').lower() == 'true'

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
        },
    },
    'root': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'crmChat': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
