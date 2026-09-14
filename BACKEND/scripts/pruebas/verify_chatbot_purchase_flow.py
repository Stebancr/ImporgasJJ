"""Prueba manual reproducible del flujo informativo y la transferencia comercial."""
from crmChat.ollama_service import ollama_service


state = None
turns = (
    'Hola',
    'Estoy interesado en un calentador de paso a gas natural de 10 litros',
    '¿Qué precio y disponibilidad tiene?',
    'Quiero adquirirlo',
)

for message in turns:
    result = ollama_service.get_bot_response(message, conversation_state=state)
    state = result['state']
    print(f'CLIENTE: {message}')
    print(f'GASI: {result["response"]}')
    print(f'DERIVAR: {result["needs_agent"]}')
    print('---')
