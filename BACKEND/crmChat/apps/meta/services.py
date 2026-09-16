"""Servicios compartidos de seguridad, Graph API y persistencia omnicanal."""

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone as datetime_timezone

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from crmChat.models import (
    ChannelIdentity,
    ChannelIntegration,
    ChatAttachment,
    ChatMessage,
    ChatSession,
    CRMContact,
    WebhookEvent,
)

from .webhooks import detect_channel, normalize_payload

logger = logging.getLogger(__name__)


class SecretConfigurationError(RuntimeError):
    """Indica que falta o no es válida la clave de cifrado del backend."""


class MetaAPIError(RuntimeError):
    """Error seguro de comunicación con Graph API."""


class SecretStore:
    """Cifra secretos con Fernet y compara verify tokens mediante SHA-256."""

    def _fernet(self):
        key = getattr(settings, 'META_CREDENTIALS_ENCRYPTION_KEY', '')
        if not key:
            raise SecretConfigurationError('Falta META_CREDENTIALS_ENCRYPTION_KEY.')
        try:
            return Fernet(key.encode('ascii'))
        except (ValueError, TypeError) as exc:
            raise SecretConfigurationError('META_CREDENTIALS_ENCRYPTION_KEY no es una clave Fernet válida.') from exc

    def encrypt(self, value):
        return self._fernet().encrypt(value.encode('utf-8')).decode('ascii')

    def decrypt(self, value):
        if not value:
            return ''
        try:
            return self._fernet().decrypt(value.encode('ascii')).decode('utf-8')
        except InvalidToken as exc:
            raise SecretConfigurationError('No fue posible descifrar una credencial Meta.') from exc

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


secret_store = SecretStore()


def verify_webhook_token(candidate):
    """Compara el token de verificación global o los hashes configurados."""

    if not candidate:
        return False
    global_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', '')
    if global_token and hmac.compare_digest(candidate, global_token):
        return True
    digest = secret_store.digest(candidate)
    return ChannelIntegration.objects.filter(active=True, verify_token_digest=digest).exists()


def _candidate_app_secrets(channel=''):
    global_secret = getattr(settings, 'META_APP_SECRET', '')
    if global_secret:
        yield global_secret
    integrations = ChannelIntegration.objects.filter(active=True).exclude(app_secret_encrypted='')
    if channel:
        integrations = integrations.filter(channel=channel)
    for encrypted in integrations.values_list('app_secret_encrypted', flat=True):
        try:
            yield secret_store.decrypt(encrypted)
        except SecretConfigurationError:
            logger.error('Una integración Meta tiene un App Secret que no se puede descifrar.')


def verify_webhook_signature(raw_body, signature_header, channel=''):
    """Valida ``X-Hub-Signature-256`` sobre los bytes exactos recibidos."""

    if not signature_header or not signature_header.startswith('sha256='):
        return False
    supplied = signature_header.removeprefix('sha256=')
    for secret in _candidate_app_secrets(channel):
        expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, supplied):
            return True
    return False


def graph_request(integration, method, path, *, json_body=None, params=None, base_url=None):
    """Ejecuta una solicitud Graph sin incluir tokens en URL, logs o errores."""

    encrypted_token = integration.access_token_encrypted
    if not encrypted_token and integration.meta_facebook_page_id:
        encrypted_token = integration.meta_facebook_page.page_access_token_encrypted
    token = secret_store.decrypt(encrypted_token)
    if not token:
        raise MetaAPIError('La integración no tiene token de acceso.')
    version = integration.graph_api_version
    if not version:
        raise MetaAPIError('La integración no tiene versión de Graph API.')
    root = (base_url or getattr(settings, 'META_GRAPH_API_URL', 'https://graph.facebook.com')).rstrip('/')
    url = f"{root}/{version}/{path.lstrip('/')}"
    try:
        response = requests.request(
            method,
            url,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json=json_body,
            params=params,
            timeout=getattr(settings, 'META_HTTP_TIMEOUT', 15),
        )
        data = response.json() if response.content else {}
        if not response.ok:
            error = data.get('error', {}) if isinstance(data, dict) else {}
            code = error.get('code', 'desconocido')
            subcode = error.get('error_subcode')
            details = error.get('error_data', {}).get('details') if isinstance(error.get('error_data'), dict) else ''
            detail = details or error.get('message') or 'Meta no proporcionó más detalles.'
            # Graph puede devolver saltos de línea y textos extensos. Se conserva el
            # motivo útil, sin registrar URL, cabeceras ni el token de acceso.
            detail = ' '.join(str(detail).split())[:500]
            logger.warning(
                'Meta Graph API rechazó una solicitud: status=%s code=%s subcode=%s detail=%s',
                response.status_code, code, subcode or '-', detail,
            )
            subcode_text = f', subcódigo {subcode}' if subcode else ''
            raise MetaAPIError(
                f'Graph API rechazó la solicitud ({response.status_code}, código {code}{subcode_text}): {detail}'
            )
        return data
    except requests.RequestException as exc:
        raise MetaAPIError('No fue posible conectar con Meta Graph API.') from exc


def validate_integration_connection(integration):
    """Comprueba el token contra el activo configurado sin devolver secretos."""

    if integration.channel == 'whatsapp':
        path = integration.phone_number_id
        params = {'fields': 'id,display_phone_number,verified_name'}
        base_url = None
    elif integration.channel == 'facebook':
        path = integration.page_id
        params = {'fields': 'id,name'}
        base_url = None
    elif integration.channel == 'instagram':
        path = integration.instagram_account_id
        params = {'fields': 'id,username'}
        base_url = None if integration.meta_facebook_page_id else integration.configuration.get('api_base_url', 'https://graph.instagram.com')
    else:
        raise MetaAPIError('Canal no soportado.')
    data = graph_request(integration, 'GET', path, params=params, base_url=base_url)
    return {'valid': True, 'remote_id': str(data.get('id', '')), 'name': data.get('name') or data.get('username') or data.get('verified_name', '')}


def accept_webhook(raw_body, signature_header, forced_channel=''):
    """Valida, limita y registra idempotentemente un webhook de Meta."""

    max_bytes = getattr(settings, 'META_WEBHOOK_MAX_BYTES', 2 * 1024 * 1024)
    if len(raw_body) > max_bytes:
        raise ValueError('El webhook supera el tamaño permitido.')
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('El webhook no contiene JSON válido.') from exc
    channel = forced_channel or detect_channel(payload)
    if channel not in {'whatsapp', 'facebook', 'instagram'}:
        raise ValueError('El objeto del webhook no corresponde a un canal soportado.')
    if forced_channel and detect_channel(payload) != forced_channel:
        raise ValueError('El payload no corresponde al endpoint del canal.')
    if not verify_webhook_signature(raw_body, signature_header, channel):
        raise PermissionError('Firma Meta inválida.')

    digest = hashlib.sha256(raw_body).hexdigest()
    event, created = WebhookEvent.objects.get_or_create(
        event_key=f'{channel}:{digest}',
        defaults={'channel': channel, 'payload': payload, 'payload_sha256': digest},
    )
    return event, created


def _timestamp(value):
    if value in (None, ''):
        return None
    try:
        return datetime.fromtimestamp(int(value) / (1000 if int(value) > 99_999_999_999 else 1), tz=datetime_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _find_integration(event):
    query = ChannelIntegration.objects.filter(channel=event.channel, active=True)
    external_id = event.integration_external_id
    if event.channel == 'whatsapp':
        return query.filter(models_query('phone_number_id', external_id, 'external_account_id')).first()
    if event.channel == 'facebook':
        return query.filter(models_query('page_id', external_id, 'external_account_id')).first()
    return query.filter(models_query('instagram_account_id', external_id, 'external_account_id')).first()


def models_query(primary_field, value, fallback_field):
    """Construye una consulta OR local sin exponer Django ORM a adaptadores."""

    from django.db.models import Q

    return Q(**{primary_field: value}) | Q(**{fallback_field: value})


@transaction.atomic
def persist_normalized_message(event):
    """Guarda un evento normalizado y devuelve el mensaje creado o actualizado."""

    integration = _find_integration(event)
    if not integration:
        raise ValueError(f'No hay una integración activa para {event.channel}.')

    if event.status:
        if event.external_message_id:
            message = ChatMessage.objects.filter(external_message_id=event.external_message_id).first()
            if message:
                message.status = event.status
                message.metadata = {
                    **message.metadata,
                    'meta_status': event.status,
                    **({'meta_errors': event.metadata.get('errors', [])} if event.metadata.get('errors') else {}),
                }
                message.save(update_fields=['status', 'metadata'])
                if event.status == 'failed':
                    errors = event.metadata.get('errors') or []
                    first_error = errors[0] if errors and isinstance(errors[0], dict) else {}
                    logger.warning(
                        'Meta reportó entrega fallida: session_id=%s message_id=%s channel=%s '
                        'code=%s title=%s',
                        message.session_id, message.id, event.channel,
                        first_error.get('code', 'desconocido'),
                        str(first_error.get('title') or first_error.get('message') or 'sin detalle')[:300],
                    )
            return message
        watermark = _timestamp(event.metadata.get('watermark'))
        if event.sender_id:
            messages = ChatMessage.objects.filter(
                session__integration=integration,
                session__external_thread_id=event.sender_id,
                direction='outbound',
                status__in=('queued', 'sent', 'delivered'),
            )
            if watermark:
                messages = messages.filter(created_at__lte=watermark)
            messages.update(status=event.status)
        return None

    if not event.sender_id:
        raise ValueError(f'El mensaje entrante de {event.channel} no contiene identificador de remitente.')

    if event.external_message_id:
        existing = ChatMessage.objects.filter(external_message_id=event.external_message_id).first()
        if existing:
            return existing

    identity = ChannelIdentity.objects.select_related('contact').filter(
        integration=integration,
        external_id=event.sender_id,
    ).first()
    if not identity:
        contact = CRMContact.objects.create(name=event.sender_name or f'Cliente {event.channel}')
        identity = ChannelIdentity.objects.create(
            integration=integration,
            external_id=event.sender_id,
            contact=contact,
            display_name=event.sender_name,
        )
    contact = identity.contact
    if event.sender_name and contact.name != event.sender_name:
        contact.name = event.sender_name
        contact.save(update_fields=['name', 'updated_at'])

    session = ChatSession.objects.filter(
        integration=integration,
        external_thread_id=event.sender_id,
    ).exclude(status='closed').order_by('-created_at').first()
    if session is None:
        session_defaults = {
            'contact': contact,
            'channel': event.channel,
            'user_name': event.sender_name or contact.name,
            'user_cedula': event.sender_id,
            'status': 'bot',
        }
        try:
            # La restricción parcial garantiza una única sesión activa por hilo,
            # sin impedir conservar todas las sesiones cerradas anteriores.
            with transaction.atomic():
                session = ChatSession.objects.create(
                    integration=integration,
                    external_thread_id=event.sender_id,
                    **session_defaults,
                )
        except IntegrityError:
            session = ChatSession.objects.exclude(status='closed').get(
                integration=integration,
                external_thread_id=event.sender_id,
            )
    message = ChatMessage.objects.create(
        session=session,
        text=event.text,
        sender_type='user',
        sender_name=event.sender_name or contact.name,
        direction='inbound',
        message_type=event.message_type,
        external_message_id=event.external_message_id or None,
        external_timestamp=_timestamp(event.timestamp),
        reply_to_external_id=event.reply_to_external_id,
        metadata=event.metadata,
        status='received',
    )
    for attachment in event.attachments:
        ChatAttachment.objects.create(
            message=message,
            external_media_id=attachment.get('id', ''),
            original_name=attachment.get('name', ''),
            mime_type=attachment.get('mime_type', ''),
            metadata={key: value for key, value in attachment.items() if key not in {'token'}},
        )
    session.last_customer_message_at = message.created_at
    session.inactivity_warning_at = None
    session.unread_by_agent += 1
    session.save(update_fields=['last_customer_message_at', 'inactivity_warning_at', 'unread_by_agent', 'updated_at'])
    return message


def _mask_destination(value):
    """Identifica un destino en logs sin revelar el número o ID completo."""

    value = str(value or '')
    if not value:
        return '(vacío)'
    visible = value[-4:]
    return f'{"*" * max(0, len(value) - len(visible))}{visible}'


def dispatch_outbound_message(message):
    """Envía un mensaje por su canal y actualiza su estado sin ocultar fallos."""

    session = message.session
    if session.channel == ChannelIntegration.CHANNEL_ECOMMERCE:
        message.direction = 'outbound'
        message.status = 'sent'
        message.save(update_fields=['direction', 'status'])
        return message
    if message.message_type == 'template':
        detail = (
            'El envío de plantillas está deshabilitado por la política de cero costos. '
            'El sistema esperará una nueva interacción del cliente.'
        )
        message.status = 'failed'
        message.metadata = {**message.metadata, 'error': detail, 'error_code': 'paid_messaging_disabled'}
        message.save(update_fields=['status', 'metadata'])
        logger.warning(
            'Plantilla bloqueada por política de cero costos: session_id=%s message_id=%s channel=%s',
            session.id, message.id, session.channel,
        )
        raise MetaAPIError(detail)
    if not session.messages.filter(sender_type='user', direction='inbound', external_message_id__isnull=False).exists():
        message.status = 'failed'
        message.metadata = {**message.metadata, 'error': 'No existe un mensaje entrante previo de Meta.'}
        message.save(update_fields=['status', 'metadata'])
        raise MetaAPIError('No se permite enviar mensajes sin un mensaje entrante previo de Meta.')
    if not session.integration or not session.integration.active:
        message.status = 'failed'
        message.metadata = {'error': 'Integración inactiva o inexistente.'}
        message.save(update_fields=['status', 'metadata'])
        raise MetaAPIError('La conversación no tiene una integración activa.')

    recipient = session.external_thread_id
    if not recipient:
        message.status = 'failed'
        message.metadata = {
            **message.metadata,
            'error': 'La conversación no tiene identificador del destinatario en Meta.',
        }
        message.save(update_fields=['status', 'metadata'])
        raise MetaAPIError(
            'La conversación no tiene identificador del destinatario. '
            'Es necesario recibir nuevamente el mensaje de Meta antes de responder.'
        )
    if (
        session.channel in {
            ChannelIntegration.CHANNEL_WHATSAPP,
            ChannelIntegration.CHANNEL_FACEBOOK,
            ChannelIntegration.CHANNEL_INSTAGRAM,
        }
        and (
            session.last_customer_message_at is None
            or session.last_customer_message_at < timezone.now() - timedelta(hours=24)
        )
    ):
        detail = (
            f'La ventana reactiva de {session.get_channel_display()} está cerrada. '
            'No se enviará el mensaje; el sistema esperará una nueva interacción del cliente.'
        )
        message.status = 'failed'
        message.metadata = {**message.metadata, 'error': detail, 'error_code': 'reactive_window_closed'}
        message.save(update_fields=['status', 'metadata'])
        logger.warning(
            'Envío Meta bloqueado por ventana cerrada: session_id=%s message_id=%s '
            'channel=%s type=%s destination=%s',
            session.id, message.id, session.channel, message.message_type, _mask_destination(recipient),
        )
        raise MetaAPIError(detail)

    logger.info(
        'Enviando mensaje externo: session_id=%s message_id=%s contact_id=%s channel=%s '
        'type=%s status=%s destination=%s',
        session.id, message.id, session.contact_id, session.channel,
        message.message_type, message.status, _mask_destination(recipient),
    )
    try:
        outbound_payload = message.metadata.get('outbound_payload', {})
        if session.channel == ChannelIntegration.CHANNEL_WHATSAPP:
            from crmChat.apps.whatsapp import services as channel_service
            if message.message_type == 'interactive':
                response = channel_service.send_interactive(session.integration, recipient, outbound_payload)
            elif message.message_type in {'image', 'audio', 'video', 'document', 'sticker'}:
                response = channel_service.send_media(
                    session.integration, recipient, message.message_type,
                    media_id=outbound_payload.get('id', ''), link=outbound_payload.get('url', ''),
                    caption=message.text, filename=outbound_payload.get('filename', ''),
                )
            else:
                response = channel_service.send_text(session.integration, recipient, message.text, message.reply_to_external_id)
            external_id = ((response.get('messages') or [{}])[0]).get('id', '')
        elif session.channel == ChannelIntegration.CHANNEL_FACEBOOK:
            from crmChat.apps.facebook import services as channel_service
            if message.message_type in {'image', 'audio', 'video', 'document'}:
                response = channel_service.send_attachment(session.integration, recipient, message.message_type, outbound_payload.get('url', ''))
            else:
                response = channel_service.send_text(session.integration, recipient, message.text, outbound_payload.get('quick_replies'))
            external_id = response.get('message_id', '')
        elif session.channel == ChannelIntegration.CHANNEL_INSTAGRAM:
            from crmChat.apps.instagram import services as channel_service
            response = channel_service.send_text(session.integration, recipient, message.text, outbound_payload.get('quick_replies'))
            external_id = response.get('message_id', '')
        else:
            raise MetaAPIError('Canal de salida no soportado.')
        message.external_message_id = external_id or None
        message.status = 'sent'
        message.direction = 'outbound'
        message.save(update_fields=['external_message_id', 'status', 'direction'])
        logger.info(
            'Meta aceptó el mensaje: session_id=%s message_id=%s channel=%s '
            'external_message_id=%s status=%s',
            session.id, message.id, session.channel, external_id or '-', message.status,
        )
        return message
    except Exception as exc:
        message.status = 'failed'
        message.metadata = {**message.metadata, 'error': str(exc)[:500]}
        message.save(update_fields=['status', 'metadata'])
        logger.warning(
            'Falló envío externo: session_id=%s message_id=%s contact_id=%s channel=%s '
            'type=%s destination=%s error=%s',
            session.id, message.id, session.contact_id, session.channel,
            message.message_type, _mask_destination(recipient), str(exc)[:500],
        )
        if isinstance(exc, MetaAPIError):
            raise
        raise MetaAPIError('No fue posible construir o enviar el mensaje por el canal externo.') from exc


def send_read_receipt(message):
    """Confirma lectura usando la operación disponible en cada canal."""

    session = message.session
    if not message.external_message_id or not session.integration or not session.integration.active:
        return
    if session.channel == 'whatsapp':
        from crmChat.apps.whatsapp.services import mark_read
        return mark_read(session.integration, message.external_message_id)
    if session.channel == 'facebook':
        from crmChat.apps.facebook.services import sender_action
        return sender_action(session.integration, session.external_thread_id, 'mark_seen')
    if session.channel == 'instagram':
        from crmChat.apps.instagram.services import sender_action
        return sender_action(session.integration, session.external_thread_id, 'mark_seen')


def process_webhook_event(webhook_event):
    """Procesa un evento registrado; es seguro repetirlo por sus IDs externos."""

    webhook_event.status = 'processing'
    webhook_event.attempts += 1
    webhook_event.save(update_fields=['status', 'attempts'])
    try:
        normalized = normalize_payload(webhook_event.payload, webhook_event.channel)
        messages = []
        for event in normalized:
            message = persist_normalized_message(event)
            if message is not None:
                messages.append(message)
        webhook_event.status = 'processed'
        webhook_event.processed_at = timezone.now()
        webhook_event.error_message = ''
        webhook_event.save(update_fields=['status', 'processed_at', 'error_message'])
        return messages
    except Exception as exc:
        webhook_event.status = 'failed'
        webhook_event.error_message = str(exc)[:2000]
        webhook_event.save(update_fields=['status', 'error_message'])
        raise
