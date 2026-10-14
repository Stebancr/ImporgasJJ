"""Run inside the dev backend with manage.py shell; synthetic ecommerce only.

run('prepare') while the chatbot worker is stopped; restart it; run('check').
run('live') measures eight concurrent conversations with a running worker.
"""
import json
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
from django.conf import settings
from crmChat.models import ChatMessage, ChatSession, BotConversationLease

STATE = Path('/tmp/imporgas-simple-chat-qa.json')
HEADERS = {'Host': 'localhost'}
BASE = 'http://nginx/api/crm-chat/bot/'


def prepare(index):
    client = requests.Session()
    start = time.time()
    result = client.post(BASE+'chat/', headers=HEADERS, json={
        'message': 'Quiero comprar un calentador', 'user_name': 'QA simplificado '+str(uuid.uuid4()),
    }, timeout=15)
    result.raise_for_status()
    data = result.json()
    return {'session_id': data['session_id'], 'message_id': data['user_message_id'],
            'cookies': client.cookies.get_dict(), 'started': start}


def check(item):
    client = requests.Session()
    client.cookies.update(item['cookies'])
    for _ in range(120):
        session = ChatSession.objects.get(pk=item['session_id'])
        replies = session.messages.filter(reply_to_message_id=item['message_id'])
        if session.status in ('waiting', 'active') and replies.filter(status='sent').exists():
            break
        time.sleep(.1)
    else:
        raise AssertionError('Synthetic conversation did not transfer within timeout')
    elapsed = time.time() - item['started']
    assert replies.count() == 1
    reply = replies.get()
    assert 'Voy a comunicarte' in reply.text
    assert 'Muchas gracias por comunicarse' not in reply.text
    assert not any(value in reply.text for value in ('http', '$', 'duchas', 'calentador'))
    result = client.post(BASE+'chat/', headers=HEADERS, json={
        'session_id': session.pk, 'message': 'Me interesa ese',
    }, timeout=15)
    result.raise_for_status()
    assert session.messages.filter(sender_type='bot').count() == 1
    stranger = requests.get(BASE+f'sessions/{session.pk}/messages/', headers=HEADERS, timeout=10)
    assert stranger.status_code == 403
    return elapsed


def run(mode='live'):
    assert settings.DEBUG and not settings.CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED
    if mode in ('live', 'prepare'):
        with ThreadPoolExecutor(max_workers=8) as pool:
            items = list(pool.map(prepare, range(8)))
        if mode == 'prepare':
            STATE.write_text(json.dumps(items))
            pending = ChatMessage.objects.filter(pk__in=[i['message_id'] for i in items], status='queued').count()
            assert pending == 8, pending
            print('QA prepared pending=8; restart chatbot worker then run check')
            return
    else:
        items = json.loads(STATE.read_text())
    with ThreadPoolExecutor(max_workers=8) as pool:
        durations = list(pool.map(check, items))
    pending = ChatMessage.objects.filter(pk__in=[i['message_id'] for i in items], status__in=('queued', 'processing')).count()
    assert pending == 0
    assert not BotConversationLease.objects.filter(session_id__in=[i['session_id'] for i in items]).exists()
    print(json.dumps({'mode': mode, 'conversations': 8, 'average_seconds': round(sum(durations)/8, 3),
                      'maximum_seconds': round(max(durations), 3), 'pending': pending, 'duplicates': 0}))
