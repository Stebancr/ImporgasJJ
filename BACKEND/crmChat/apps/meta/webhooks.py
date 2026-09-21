"""Normalización de payloads recibidos desde Meta Graph API."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class NormalizedMessage:
    """Contrato interno común para mensajes y actualizaciones de estado."""

    channel: str
    integration_external_id: str
    sender_id: str = ''
    recipient_id: str = ''
    external_message_id: str = ''
    text: str = ''
    message_type: str = 'text'
    timestamp: int | None = None
    sender_name: str = ''
    attachments: list[dict[str, Any]] = field(default_factory=list)
    status: str = ''
    reply_to_external_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def detect_channel(payload):
    """Determina el canal usando el campo ``object`` definido por Meta."""

    object_name = payload.get('object')
    if object_name == 'whatsapp_business_account':
        return 'whatsapp'
    if object_name == 'instagram':
        return 'instagram'
    if object_name == 'page':
        return 'facebook'
    return ''


def normalize_payload(payload, forced_channel=''):
    """Delega el parsing al adaptador del canal detectado."""

    channel = forced_channel or detect_channel(payload)
    if channel == 'whatsapp':
        from crmChat.apps.whatsapp.webhooks import parse_webhook
    elif channel == 'facebook':
        from crmChat.apps.facebook.webhooks import parse_webhook
    elif channel == 'instagram':
        from crmChat.apps.instagram.webhooks import parse_webhook
    else:
        return []
    return parse_webhook(payload)


def parse_messaging_entries(payload, channel):
    """Normaliza la estructura ``entry[].messaging[]`` de Messenger/Instagram."""

    result = []
    for entry in payload.get('entry', []):
        account_id = str(entry.get('id', ''))
        for item in entry.get('messaging', []):
            sender_id = str(item.get('sender', {}).get('id', ''))
            recipient_id = str(item.get('recipient', {}).get('id', account_id))
            message = item.get('message') or {}
            if message:
                if message.get('is_echo'):
                    result.append(NormalizedMessage(
                        channel=channel,
                        integration_external_id=account_id or recipient_id,
                        external_message_id=str(message.get('mid', '')),
                        timestamp=item.get('timestamp'),
                        status='sent',
                        metadata={'is_echo': True},
                    ))
                    continue
                attachments = []
                message_type = 'text'
                for attachment in message.get('attachments', []):
                    attachment_type = attachment.get('type', 'document')
                    message_type = attachment_type if attachment_type in {'image', 'audio', 'video', 'sticker'} else 'document'
                    payload_data = attachment.get('payload', {})
                    attachments.append({
                        'id': payload_data.get('attachment_id', ''),
                        'url': payload_data.get('url', ''),
                        'type': attachment_type,
                    })
                result.append(NormalizedMessage(
                    channel=channel,
                    integration_external_id=account_id or recipient_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    external_message_id=str(message.get('mid', '')),
                    text=message.get('text', ''),
                    message_type=message_type,
                    timestamp=item.get('timestamp'),
                    attachments=attachments,
                    reply_to_external_id=str(message.get('reply_to', {}).get('mid', '')),
                    metadata={
                        'entry_account_id': account_id,
                        'is_echo': bool(message.get('is_echo', False)),
                        'quick_reply_payload': message.get('quick_reply', {}).get('payload', ''),
                    },
                ))
            elif item.get('postback'):
                postback = item['postback']
                result.append(NormalizedMessage(
                    channel=channel,
                    integration_external_id=account_id or recipient_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    external_message_id=str(postback.get('mid', '')),
                    text=postback.get('title') or postback.get('payload', ''),
                    message_type='interactive',
                    timestamp=item.get('timestamp'),
                    metadata={'postback_payload': postback.get('payload', '')},
                ))
            elif item.get('delivery'):
                delivery = item['delivery']
                for message_id in delivery.get('mids', []) or ['']:
                    result.append(NormalizedMessage(
                        channel=channel,
                        integration_external_id=account_id or recipient_id,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        external_message_id=str(message_id),
                        timestamp=item.get('timestamp'),
                        status='delivered',
                        metadata={'watermark': delivery.get('watermark')},
                    ))
            elif item.get('read'):
                result.append(NormalizedMessage(
                    channel=channel,
                    integration_external_id=account_id or recipient_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    timestamp=item.get('timestamp'),
                    status='read',
                    metadata={'watermark': item['read'].get('watermark')},
                ))
    return result
