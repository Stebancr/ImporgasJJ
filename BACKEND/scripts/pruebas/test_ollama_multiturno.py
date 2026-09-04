"""Prueba manual end-to-end del estado conversacional usando el Ollama real."""
import json

import requests


MESSAGES = [
    'Hola',
    'Quiero comprar un celular',
    'Tengo un millón',
    '¿Cuál me recomiendas?',
    '¿Y hacen envíos?',
    'Quiero saber sobre la garantía',
    'Volviendo al celular, ¿cuál me recomiendas?',
    'Quiero hablar con un asesor',
]


def main():
    session_id = None
    for message in MESSAGES:
        response = requests.post(
            'http://localhost:8000/crm-chat/bot/chat/',
            json={
                'message': message,
                'session_id': session_id,
                'user_name': 'Prueba multiturno',
            },
            timeout=120,
        )
        data = response.json()
        session_id = data.get('session_id', session_id)
        print(json.dumps({
            'user': message,
            'status_code': response.status_code,
            'bot': data.get('message'),
            'state': data.get('conversation_state'),
            'needs_agent': data.get('needs_agent'),
            'needs_login': data.get('needs_login'),
        }, ensure_ascii=False), flush=True)
        response.raise_for_status()


if __name__ == '__main__':
    main()
