import hashlib
import hmac
import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed


def internal_authenticate(request):
    secret = settings.CRM_INTERNAL_SERVICE_TOKEN
    bearer = request.headers.get('Authorization', '')
    timestamp = request.headers.get('X-WhatsApp-Gateway-Timestamp', '')
    request_id = request.headers.get('X-WhatsApp-Gateway-Request-ID', '')
    signature = request.headers.get('X-WhatsApp-Gateway-Signature', '')
    if not secret or not request_id or not timestamp:
        raise AuthenticationFailed('Autenticación interna inválida.')
    try:
        recent = abs(int(time.time()) - int(timestamp)) <= settings.WHATSAPP_GATEWAY_REQUEST_MAX_AGE
    except ValueError:
        recent = False
    expected = hmac.new(
        secret.encode(), f'{timestamp}.{request_id}.'.encode() + request.body, hashlib.sha256,
    ).hexdigest()
    valid = hmac.compare_digest(bearer, f'Bearer {secret}') and hmac.compare_digest(signature, expected)
    replay_key = f'whatsapp-gateway-request:{request_id}'
    if not recent or not valid or not cache.add(replay_key, True, settings.WHATSAPP_GATEWAY_REQUEST_MAX_AGE):
        raise AuthenticationFailed('Autenticación interna inválida.')


def signed_headers(raw_body):
    import uuid
    timestamp = str(int(time.time()))
    request_id = str(uuid.uuid4())
    secret = settings.CRM_INTERNAL_SERVICE_TOKEN
    signature = hmac.new(secret.encode(), f'{timestamp}.{request_id}.'.encode() + raw_body, hashlib.sha256).hexdigest()
    return {
        'Authorization': f'Bearer {secret}',
        'Content-Type': 'application/json',
        'X-WhatsApp-Gateway-Timestamp': timestamp,
        'X-WhatsApp-Gateway-Request-ID': request_id,
        'X-WhatsApp-Gateway-Signature': signature,
    }
