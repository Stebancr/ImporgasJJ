
from core.config.base import *


ALLOWED_HOSTS = [
    'localhost',
    '62.72.7.176',
    '.ngrok.io',
    'juvenescent-tamelessly-dennis.ngrok-free.dev',
    '127.0.0.1',
    'formacion.cloudregencyapps.com',
    'testserver',
]

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', ''),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'mysql'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
