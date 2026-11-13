"""Same synthetic history against the original and bounded API implementations."""
import gc
import json
import time
import tracemalloc
import uuid
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate
from usuarios.models import Credenciales
from crmChat.models import ChatSession, ChatMessage
from crmChat.views import MessageListCreateView

if not (settings.DEBUG and settings.CRM_TEST_MODE and settings.DATABASES['default']['NAME'] == 'crm_audit'):
    raise RuntimeError('CRM_AUDIT_ISOLATION_REQUIRED')
baseline = {'__name__': 'crmChat.audit_baseline', '__package__': 'crmChat'}
exec(compile(Path('/tmp/original_crm_views.py').read_text(encoding='utf-8-sig'),
             '/tmp/original_crm_views.py', 'exec'), baseline)
agent = Credenciales.objects.create(usuario='benchmark-'+uuid.uuid4().hex, tipo_usuario=4, estado=1)
session = ChatSession.objects.create(channel='ecommerce', status='active')
ChatMessage.objects.bulk_create([ChatMessage(session=session, sender_type='user', text='Synthetic history '*20)
                                for _ in range(2000)])
metrics = {}
for name, view in [('before', baseline['MessageListCreateView']), ('after', MessageListCreateView)]:
    request = APIRequestFactory().get('/crm-chat/sessions/', {'limit': 100})
    force_authenticate(request, agent)
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    with CaptureQueriesContext(connection) as queries:
        response = view.as_view()(request, pk=session.pk)
        payload = json.dumps(response.data, default=str).encode()
    duration = time.perf_counter()-start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert response.status_code == 200
    metrics[name] = {'messages': len(response.data['messages']), 'seconds': round(duration, 4),
                     'peak_bytes': peak, 'response_bytes': len(payload), 'queries': len(queries)}
print('CRM_BENCHMARK ' + json.dumps(metrics))
