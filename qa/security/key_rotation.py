"""Cold-process JWT key rotation check, isolated synthetic account only."""
import json
import sys
from pathlib import Path
from django.conf import settings
from rest_framework.test import APIClient
from auth.authentication import PasswordVersionJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

assert settings.DEBUG and settings.DATABASES['default']['NAME'] == 'security_qa'
assert settings.SIMPLE_JWT['SIGNING_KEY'] != settings.SECRET_KEY
path = Path('/tmp/security-key-rotation.json')
client = APIClient()
if sys.argv[-1] == 'verify':
    old = json.loads(path.read_text())
    try:
        PasswordVersionJWTAuthentication().get_validated_token(old['access'])
    except InvalidToken:
        pass
    else:
        raise AssertionError('Old signing key was accepted')
    assert client.post('/auth/token/refresh/', {'refresh': old['refresh']}).status_code == 401
response = client.post('/auth/token/', {'usuario': 'security-browser-fixture', 'password': 'Synthetic@Browser937!'})
assert response.status_code == 200
client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
assert client.get('/user/perfil').status_code == 200
if sys.argv[-1] != 'verify':
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(json.dumps({'access': response.data['access'], 'refresh': response.data['refresh']}))
print('JWT_KEY_ROTATION_' + ('AFTER' if sys.argv[-1] == 'verify' else 'BEFORE') + '=PASS')
