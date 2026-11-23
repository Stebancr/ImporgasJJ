"""Controlled smoke: isolated DB + real Redis/worker/ASGI, synthetic channel IO.

Run through manage.py shell ONLY in docker-compose.crm-audit.yml after migrate.
Never emits credentials, user tokens, provider URLs or message contents.
"""
import asyncio
import hashlib
import hmac
import json
import time
import uuid
from io import BytesIO

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from crmChat.models import ChatMessage, ChatSession
from usuarios.models import Credenciales

if not (settings.DEBUG and settings.CRM_TEST_MODE and not settings.CRM_EXTERNAL_SEND_ENABLED
        and settings.DATABASES['default']['NAME'] == 'crm_audit'
        and settings.DATABASES['default']['HOST'] == 'database'):
    raise RuntimeError('CRM_AUDIT_ISOLATION_REQUIRED')
if not settings.CRM_INTERNAL_SERVICE_TOKEN:
    raise RuntimeError('CRM_AUDIT_SYNTHETIC_INTERNAL_SECRET_REQUIRED')

run = uuid.uuid4().hex
settings.MEDIA_ROOT = '/tmp/crm-audit-media'
client = APIClient(HTTP_HOST='localhost')
agent = Credenciales.objects.create(usuario=f'audit-{run}', tipo_usuario=4, estado=1)
client.force_authenticate(agent)


def signed_post(path, payload):
    raw = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()
    timestamp, request_id = str(int(time.time())), str(uuid.uuid4())
    key = settings.CRM_INTERNAL_SERVICE_TOKEN
    signature = hmac.new(key.encode(), f'{timestamp}.{request_id}.'.encode()+raw, hashlib.sha256).hexdigest()
    return client.generic('POST', path, raw, content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {key}', HTTP_X_WHATSAPP_GATEWAY_TIMESTAMP=timestamp,
        HTTP_X_WHATSAPP_GATEWAY_REQUEST_ID=request_id, HTTP_X_WHATSAPP_GATEWAY_SIGNATURE=signature)


response = signed_post('/internal/whatsapp/status/', {'connection_id': 'audit',
    'status': 'connected', 'phone_number': '570000000001'})
assert response.status_code == 200, response.status_code
synthetic_number = f'5700{int(run[:8], 16):010d}'
incoming = {'connection_id': 'audit', 'idempotency_key': run, 'remote_jid': synthetic_number+'@s.whatsapp.net',
    'number': synthetic_number, 'push_name': 'Contacto sintético', 'message_id': run,
    'timestamp': int(time.time()), 'type': 'text', 'text': 'Mensaje de auditoría', 'is_group': False}
response = signed_post('/internal/whatsapp/webhook/', incoming)
assert response.status_code == 201, response.status_code
session = ChatSession.objects.get(integration__external_account_id='audit', external_thread_id=incoming['remote_jid'])
token = str(AccessToken.for_user(agent))


async def scenario():
    from core.asgi import application
    socket = WebsocketCommunicator(application, '/ws/crm-chat/',
        headers=[(b'host', b'localhost')], subprotocols=['crm-chat', f'jwt.{token}'])
    assert (await socket.connect())[0]
    await socket.send_json_to({'type': 'ping'})
    assert (await socket.receive_json_from())['type'] == 'pong'
    endpoint = f'/crm-chat/sessions/{session.pk}/messages/'

    async def request(method, path, payload=None, **kwargs):
        return await database_sync_to_async(getattr(client, method))(path, payload or {}, **kwargs)

    response = await request('patch', f'/crm-chat/sessions/{session.pk}/', {'status': 'active'}, format='json')
    assert response.status_code == 200
    second = {**incoming, 'idempotency_key': run+'2', 'message_id': run+'2'}
    response = await database_sync_to_async(signed_post)('/internal/whatsapp/webhook/', second)
    assert response.status_code == 201
    duplicate = await database_sync_to_async(signed_post)('/internal/whatsapp/webhook/', second)
    assert duplicate.status_code == 200

    response = await request('post', '/crm-chat/templates/', {
        'name': f'Auditoría {run}', 'text': 'Respuesta sintética', 'category': 'Auditoría',
        'channels': ['whatsapp_web'], 'active': True,
    }, format='json')
    assert response.status_code == 201, response.status_code
    template_id = response.data['id']
    operation = str(uuid.uuid4())
    payload = {'text': 'Respuesta sintética', 'client_message_id': operation,
               'template_id': template_id, 'template_variables': {}}
    response = await request('post', endpoint, payload, format='json')
    assert response.status_code == 201, response.status_code
    assert response.data['status'] == 'queued'
    message_id = response.data['id']
    duplicate = await request('post', endpoint, payload, format='json')
    assert duplicate.status_code == 200 and duplicate.data['id'] == message_id

    data = BytesIO()
    Image.new('RGB', (8, 8), 'orange').save(data, format='PNG')
    response = await request('post', endpoint, {'text': 'Adjunto sintético',
        'client_message_id': str(uuid.uuid4()),
        'file': SimpleUploadedFile('audit.png', data.getvalue(), content_type='image/png')}, format='multipart')
    assert response.status_code == 201, response.status_code
    media_id = response.data['id']
    attachment_url = response.data['attachments'][0]['url'].removeprefix('/api')
    response = await request('get', attachment_url)
    assert response.status_code == 200
    response.close()

    deadline, events = time.monotonic()+20, set()
    while time.monotonic() < deadline:
        statuses = await database_sync_to_async(list)(ChatMessage.objects.filter(
            pk__in=[message_id, media_id]).values_list('status', 'metadata'))
        if all(status == 'sent' and metadata.get('simulated') for status, metadata in statuses):
            if 'message.updated' in events:
                break
        try:
            event = await asyncio.wait_for(socket.receive_json_from(timeout=3), timeout=4)
            events.add(event['type'])
        except asyncio.TimeoutError:
            raise AssertionError('CRM_WORKER_OR_REALTIME_TIMEOUT') from None
    else:
        raise AssertionError('CRM_WORKER_TIMEOUT')
    assert await database_sync_to_async(ChatMessage.objects.filter(session=session).count)() == 4
    response = await request('get', endpoint)
    assert response.status_code == 200 and len(response.data['messages']) == 4
    await socket.disconnect()
    return {'worker': 'simulated_sent', 'websocket': sorted(events), 'duplicates': 0,
            'messages': 4, 'template': True, 'protected_attachment': True}


print('CRM_ISOLATED_SMOKE ' + json.dumps(async_to_sync(scenario)()))
