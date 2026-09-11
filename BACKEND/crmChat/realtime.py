"""Publicación de eventos de dominio hacia Django Channels."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_crm_event(event_type, *, session_id, message_id=None):
    """Notifica cambios sin incluir datos privados ni credenciales."""

    layer = get_channel_layer()
    if not layer:
        return
    payload = {'type': event_type, 'session_id': session_id}
    if message_id is not None:
        payload['message_id'] = message_id
    async_to_sync(layer.group_send)('crm_agents', {'type': 'crm.event', 'payload': payload})
