"""Docker dev-only smoke: synthetic ecommerce conversations, no external sends."""
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from django.conf import settings

assert settings.DEBUG, 'This smoke test is restricted to development.'
for _ in range(20):
    try:
        if requests.get('http://nginx/api/', headers={'Host': 'localhost'}, timeout=3).status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(1)
else:
    raise AssertionError('Backend/proxy did not become ready.')

def check(index):
    client = requests.Session()
    headers = {'Host': 'localhost'}
    started = time.perf_counter()
    response = client.post('http://nginx/api/crm-chat/bot/chat/', headers=headers,
                           json={'message': 'Hola', 'user_name': f'QA Docker cola {index}'}, timeout=15)
    assert response.status_code == 202, response.status_code
    data = response.json()
    assert data['bot_message_id'] is None
    session_id = data['session_id']
    url = f'http://nginx/api/crm-chat/bot/sessions/{session_id}/messages/'
    for _ in range(20):
        result = client.get(url, headers=headers, timeout=10)
        assert result.status_code == 200, result.status_code
        replies = [m for m in result.json()['messages'] if m['sender_type'] == 'bot']
        if replies:
            assert len(replies) == 1
            stranger = requests.get(url, headers=headers, timeout=10)
            assert stranger.status_code == 403
            return {'session_id': session_id, 'single_reply': True,
                    'seconds': round(time.perf_counter()-started, 3), 'isolation': True}
        time.sleep(1)
    raise AssertionError('The queued bot message did not complete within 20 seconds.')

with ThreadPoolExecutor(2) as pool:
    print(list(pool.map(check, range(2))))
