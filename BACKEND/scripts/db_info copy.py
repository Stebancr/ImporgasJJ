import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
django.setup()
from django.conf import settings
from django.db import connection
print('DB NAME:', settings.DATABASES['default']['NAME'])
print('DB ENGINE:', settings.DATABASES['default']['ENGINE'])
print('DB HOST:', settings.DATABASES['default']['HOST'])
print('DB USER:', settings.DATABASES['default']['USER'])
print('TABLES SAMPLE:', connection.introspection.table_names()[:20])
