import os
import sys
from pathlib import Path
import django
from django.db import connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

DB_NAME = connection.settings_dict.get('NAME')

with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """,
        [DB_NAME, 'colaboradores']
    )
    cols = [row[0] for row in cursor.fetchall()]

print('Tabla colaboradores columnas:')
for c in cols:
    print('-', c)
