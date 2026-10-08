"""Run through `docker compose ... exec -T backend python manage.py shell < ...`.

Only synthetic prompts, no database writes, no external messaging.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import mean
import requests
from django.conf import settings

base = settings.OLLAMA_API_URL.rsplit('/api/', 1)[0]
prompt = 'Explica en español, brevemente, por qué conviene el mantenimiento preventivo de un calentador. No inventes precios ni características.'
results = {}

def run(model, ctx, predict):
    started = time.perf_counter()
    response = requests.post(base + '/api/chat', json={
        'model': model, 'stream': False,
        'messages': [{'role': 'system', 'content': 'Eres asesor comercial de IMPORGAS JJ. Responde en español en tres frases.'},
                     {'role': 'user', 'content': prompt}],
        'options': {'num_ctx': ctx, 'num_predict': predict, 'temperature': 0.1},
    }, timeout=120)
    response.raise_for_status()
    result = response.json()
    assert result.get('message', {}).get('content'), 'Empty inference'
    return {'seconds': round(time.perf_counter()-started, 3),
            'tokens': result.get('eval_count'), 'done': result.get('done')}

for model, ctx, predict in [('qwen:4b', 4096, 450), (settings.OLLAMA_MODEL, settings.OLLAMA_NUM_CTX, settings.OLLAMA_NUM_PREDICT)]:
    samples = [run(model, ctx, predict) for _ in range(3)]
    loaded = requests.get(base + '/api/ps', timeout=10).json()
    results[model] = {'samples': samples, 'average_seconds': round(mean(x['seconds'] for x in samples), 3),
                      'loaded_bytes': sum(x['size'] for x in loaded.get('models', []))}
with ThreadPoolExecutor(2) as pool:
    results['parallel_two'] = list(pool.map(lambda _: run(settings.OLLAMA_MODEL, settings.OLLAMA_NUM_CTX, settings.OLLAMA_NUM_PREDICT), range(2)))
print(json.dumps(results, ensure_ascii=False))
