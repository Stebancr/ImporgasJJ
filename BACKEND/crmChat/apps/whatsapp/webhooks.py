"""Parser defensivo de mensajes y estados de WhatsApp Cloud API."""

from crmChat.apps.meta.webhooks import NormalizedMessage


STATUS_MAP = {
    'sent': 'sent',
    'delivered': 'delivered',
    'read': 'read',
    'failed': 'failed',
}


def _message_content(message):
    message_type = message.get('type', 'text')
    content = message.get(message_type, {}) if isinstance(message.get(message_type), dict) else {}
    if message_type == 'text':
        return content.get('body', ''), 'text', []
    if message_type == 'interactive':
        reply = content.get('button_reply') or content.get('list_reply') or {}
        return reply.get('title') or reply.get('id', ''), 'interactive', []
    normalized_type = message_type if message_type in {'image', 'audio', 'video', 'document', 'sticker'} else 'document'
    attachment = {
        'id': content.get('id', ''),
        'name': content.get('filename', ''),
        'mime_type': content.get('mime_type', ''),
        'sha256': content.get('sha256', ''),
        'caption': content.get('caption', ''),
    }
    return content.get('caption', ''), normalized_type, [attachment]


def parse_webhook(payload):
    result = []
    for entry in payload.get('entry', []):
        waba_id = str(entry.get('id', ''))
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value', {})
            phone_number_id = str(value.get('metadata', {}).get('phone_number_id', '') or waba_id)
            names = {
                str(contact.get('wa_id', '')): contact.get('profile', {}).get('name', '')
                for contact in value.get('contacts', [])
            }
            for message in value.get('messages', []):
                sender_id = str(message.get('from', ''))
                text, message_type, attachments = _message_content(message)
                result.append(NormalizedMessage(
                    channel='whatsapp',
                    integration_external_id=phone_number_id,
                    sender_id=sender_id,
                    recipient_id=phone_number_id,
                    external_message_id=str(message.get('id', '')),
                    text=text,
                    message_type=message_type,
                    timestamp=message.get('timestamp'),
                    sender_name=names.get(sender_id, ''),
                    attachments=attachments,
                    reply_to_external_id=str(message.get('context', {}).get('id', '')),
                    metadata={'waba_id': waba_id},
                ))
            for delivery in value.get('statuses', []):
                result.append(NormalizedMessage(
                    channel='whatsapp',
                    integration_external_id=phone_number_id,
                    recipient_id=str(delivery.get('recipient_id', '')),
                    external_message_id=str(delivery.get('id', '')),
                    timestamp=delivery.get('timestamp'),
                    status=STATUS_MAP.get(delivery.get('status'), 'failed'),
                    metadata={'errors': delivery.get('errors', [])},
                ))
    return result
