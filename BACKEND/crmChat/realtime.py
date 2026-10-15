"""Publicación de eventos de dominio hacia Django Channels."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)


def publish_crm_event(event_type, *, session_id, message_id=None):
    """Notifica cambios sin incluir datos privados ni credenciales."""

    layer = get_channel_layer()
    if not layer:
        return
    payload = {'type': event_type, 'session_id': session_id}
    if message_id is not None:
        payload['message_id'] = message_id
    try:
        async_to_sync(layer.group_send)('crm_agents', {'type': 'crm.event', 'payload': payload})
    except Exception as exc:
        # Redis availability must not turn a committed message into an HTTP 500.
        # Polling/reconnection retrieves the authoritative persisted state.
        logger.warning('CRM realtime unavailable type=%s session_id=%s reason=%s',
                       event_type, session_id, type(exc).__name__)
