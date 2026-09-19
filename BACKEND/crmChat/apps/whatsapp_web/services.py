import json
import logging
import uuid

import requests
from django.conf import settings

from crmChat.apps.meta.services import MetaAPIError
from crmChat.models import ChannelIdentity
from .auth import signed_headers
from .jids import external_message_key, mask_jid, normalize_user_jid


logger = logging.getLogger(__name__)


def gateway_request(path, payload):
    if not settings.CRM_INTERNAL_SERVICE_TOKEN:
        raise MetaAPIError('Falta CRM_INTERNAL_SERVICE_TOKEN para WhatsApp Web Gateway.')
    raw = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()
    try:
        response = requests.post(
            f"{settings.WHATSAPP_GATEWAY_URL.rstrip('/')}{path}", data=raw,
            headers=signed_headers(raw), timeout=20,
        )
        data = response.json() if response.content else {}
    except (requests.RequestException, ValueError) as exc:
        raise MetaAPIError('No fue posible contactar WhatsApp Web Gateway.') from exc
    if not response.ok:
        raise MetaAPIError(str(data.get('detail') or 'WhatsApp Web Gateway rechazó la operación.')[:300])
    return data


def send_message(message, payload):
    session = message.session
    canonical_jid = normalize_user_jid(session.external_thread_id)
    identity = ChannelIdentity.objects.filter(
        integration_id=session.integration_id,
        external_id=canonical_jid,
    ).first()
    reply_jid = normalize_user_jid((identity.profile_data or {}).get('reply_jid')) if identity else ''
    destination = reply_jid or canonical_jid
    if not destination:
        raise MetaAPIError('La conversación tiene un JID inválido; espere un mensaje nuevo del cliente.')
    client_message_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'crm-message:{message.pk}'))
    message.metadata = {**(message.metadata or {}), 'client_message_id': client_message_id, 'origin': 'crm'}
    message.save(update_fields=['metadata'])
    gateway_payload = {
        'connection_id': session.integration.external_account_id,
        'to': destination,
        'type': message.message_type,
        'text': message.text,
        'url': payload.get('url'),
        'file_name': payload.get('filename'),
        'mime_type': payload.get('mime_type'),
        'reply_to': message.reply_to_external_id or None,
        'client_message_id': client_message_id,
    }
    response = gateway_request('/internal/whatsapp/send/', {
        key: value for key, value in gateway_payload.items() if value is not None
    })
    raw_external_id = str(response.get('external_message_id') or '')
    if not raw_external_id:
        raise MetaAPIError('WhatsApp Web no confirmó el identificador del mensaje enviado.')
    logger.info(
        'WhatsApp Web aceptó salida: session_id=%s message_id=%s destination=%s external_id=%s.',
        session.pk, message.pk, mask_jid(destination), raw_external_id,
    )
    return {
        **response,
        'gateway_message_id': raw_external_id,
        'external_message_id': external_message_key(session.integration.external_account_id, raw_external_id),
    }
