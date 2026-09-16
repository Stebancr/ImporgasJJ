"""Operaciones de salida para WhatsApp Cloud API."""

from crmChat.apps.meta.services import graph_request


def _send(integration, recipient_id, message):
    body = {'messaging_product': 'whatsapp', 'recipient_type': 'individual', 'to': recipient_id}
    body.update(message)
    return graph_request(integration, 'POST', f'{integration.phone_number_id}/messages', json_body=body)


def send_text(integration, recipient_id, text, reply_to=''):
    message = {'type': 'text', 'text': {'preview_url': False, 'body': text}}
    if reply_to:
        message['context'] = {'message_id': reply_to}
    return _send(integration, recipient_id, message)


def send_media(integration, recipient_id, media_type, *, media_id='', link='', caption='', filename=''):
    media = {'id': media_id} if media_id else {'link': link}
    if caption and media_type in {'image', 'video', 'document'}:
        media['caption'] = caption
    if filename and media_type == 'document':
        media['filename'] = filename
    return _send(integration, recipient_id, {'type': media_type, media_type: media})


def send_interactive(integration, recipient_id, interactive):
    return _send(integration, recipient_id, {'type': 'interactive', 'interactive': interactive})


def mark_read(integration, external_message_id):
    return graph_request(integration, 'POST', f'{integration.phone_number_id}/messages', json_body={
        'messaging_product': 'whatsapp',
        'status': 'read',
        'message_id': external_message_id,
    })
