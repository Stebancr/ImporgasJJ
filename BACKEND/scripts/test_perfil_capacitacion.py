import os
import sys
import json
import django
from pathlib import Path

# Ensure project root is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIClient
from usuarios.models import Usuarios, Colaboradores

TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3NjIyODU1LCJpYXQiOjE3Njc2MjI1NTUsImp0aSI6ImM1M2YzYWQ0MzBjNDQ0NzViMTQ2ZDcxMjNhYTUyZjVjIiwidXNlcl9pZCI6IjU1In0.IqIqACCY2jsRIRF4joN0jyRLma7adKJy0X6ho1R-VQk'

client = APIClient()

# Ensure a test user exists
usr = Usuarios.objects.filter(usuario='admin_test').first()
colab = Colaboradores.objects.filter(idcolaborador=54).first()
if not usr:
    usr = Usuarios(usuario='admin_test', tipousuario=1, estadousuario=1, idcolaboradoru=colab)
    usr.set_password('admin123')
    usr.save()
elif usr.idcolaboradoru_id is None and colab is not None:
    usr.idcolaboradoru = colab
    usr.save(update_fields=['idcolaboradoru'])

# Obtain a fresh JWT access token
token_resp = client.post('/auth/token/', {'usuario': 'admin_test', 'password': 'admin123'}, format='json', HTTP_HOST='localhost')
if token_resp.status_code != 200:
    print('TOKEN_STATUS', token_resp.status_code)
    try:
        print('TOKEN_BODY_SNIPPET')
        print(token_resp.content.decode('utf-8', errors='ignore')[:400])
    except Exception:
        pass
    raise SystemExit(1)
token_data = json.loads(token_resp.content.decode('utf-8'))
access_token = token_data.get('access')

client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

# Call perfil endpoint using authenticated user
url = '/user/perfil/'
response = client.get(url, HTTP_HOST='localhost')

print('STATUS', response.status_code)

# Save full body to file for inspection
full_path = PROJECT_ROOT / 'last_response_script.txt'
try:
    content_text = response.content.decode('utf-8', errors='ignore')
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content_text)
    # Show only the first 400 chars to keep output concise
    print('BODY_SNIPPET')
    print(content_text[:400])
except Exception as e:
    print('ERROR_READING_BODY', str(e))
