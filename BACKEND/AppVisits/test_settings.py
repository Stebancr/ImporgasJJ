"""Isolated visits tests: never loads .env, SMTP, production DB or media."""
import tempfile

SECRET_KEY = 'visits-isolated-tests-only'
DEBUG = False
USE_TZ = True
TIME_ZONE = 'America/Bogota'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'rest_framework', 'usuarios', 'ecommerce', 'AppVisits']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
AUTH_USER_MODEL = 'usuarios.Credenciales'
ROOT_URLCONF = 'AppVisits.urls'
MIDDLEWARE = []
ALLOWED_HOSTS = ['testserver', 'localhost']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'visitas@example.test'
MEDIA_ROOT = tempfile.mkdtemp(prefix='visits-isolated-media-')
MEDIA_URL = '/media/'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'DEFAULT_THROTTLE_CLASSES': []}
