"""Operaciones Send API y sender actions de Messenger."""

from crmChat.apps.meta.services import graph_request


def _send(integration, recipient_id, payload):
    body = {'recipient': {'id': recipient_id}, 'messaging_type': 'RESPONSE'}
    body.update(payload)
    return graph_request(integration, 'POST', f'{integration.page_id}/messages', json_body=body)


def send_text(integration, recipient_id, text, quick_replies=None):
    message = {'text': text}
    if quick_replies:
        message['quick_replies'] = quick_replies
    return _send(integration, recipient_id, {'message': message})


def send_attachment(integration, recipient_id, attachment_type, url, reusable=False):
    return _send(integration, recipient_id, {'message': {'attachment': {
        'type': attachment_type,
        'payload': {'url': url, 'is_reusable': reusable},
    }}})


def sender_action(integration, recipient_id, action):
    if action not in {'mark_seen', 'typing_on', 'typing_off'}:
        raise ValueError('Sender action no soportada.')
    return _send(integration, recipient_id, {'sender_action': action})


def get_sender_profile(integration, sender_id):
    """Consulta el perfil Page-scoped sin registrar un fallo opcional como caída del canal."""

    return graph_request(
        integration,
        'GET',
        sender_id,
        params={'fields': 'id,name,first_name,last_name,profile_pic'},
        record_error=False,
    )
