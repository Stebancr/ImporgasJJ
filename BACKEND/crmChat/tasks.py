"""Tareas asíncronas del webhook y del bot omnicanal."""

import ipaddress
import logging
import socket
from datetime import timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .apps.meta.services import (
    dispatch_outbound_message,
    graph_request,
    process_webhook_event,
    secret_store,
    send_read_receipt,
)
from .models import (
    ChannelIntegration,
    ChatAttachment,
    ChatAuditEvent,
    ChatMessage,
    ChatSession,
    MetaConnection,
    WebhookEvent,
)
from .ollama_service import ollama_service
from .realtime import publish_crm_event

logger = logging.getLogger(__name__)

INACTIVITY_WARNING_TEXT = 'Este chat se cerrará por inactividad en 1 minuto. Si necesitas continuar, envía un mensaje.'


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def process_meta_webhook_task(self, event_id):
    """Procesa un envelope Meta una sola vez y programa respuestas del bot."""

    logger.info('Procesando webhook Meta event_id=%s.', event_id)
    event = WebhookEvent.objects.get(pk=event_id)
    if event.status == 'processed':
        return {'duplicate': True}
    messages = process_webhook_event(event)
    for message in messages:
        publish_crm_event('message.created', session_id=message.session_id, message_id=message.id)
        for attachment in message.attachments.all():
            download_meta_attachment.delay(attachment.id)
        if message.direction == 'inbound':
            send_meta_read_receipt.delay(message.id)
        integration = message.session.integration
        bot_enabled = bool(integration and integration.configuration.get('bot_enabled', False))
        if message.sender_type == 'user' and message.session.status == 'bot' and bot_enabled:
            generate_omnichannel_bot_reply.delay(message.id)
            logger.info('Respuesta bot programada para message_id=%s session_id=%s.', message.id, message.session_id)
    return {'processed': len(messages)}


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def send_meta_read_receipt(message_id):
    """Confirma lectura fuera del request del webhook."""

    message = ChatMessage.objects.select_related('session__integration').get(pk=message_id)
    send_read_receipt(message)


def _assert_public_https(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError('La URL del adjunto no es HTTPS.')
    for address in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError('La URL del adjunto apunta a una red no permitida.')


def _open_public_stream(url, headers):
    """Abre una URL pública sin permitir redirecciones hacia redes internas.

    ``requests`` sigue redirecciones automáticamente, lo que permitiría que una
    URL externa redirigiera a un servicio privado. Por eso cada salto se valida
    antes de abrirlo y la autorización se elimina si cambia el host.
    """

    current_url = url
    current_headers = dict(headers)
    maximum_redirects = getattr(settings, 'CRM_ATTACHMENT_MAX_REDIRECTS', 3)
    for _ in range(maximum_redirects + 1):
        _assert_public_https(current_url)
        response = requests.get(
            current_url,
            headers=current_headers,
            stream=True,
            allow_redirects=False,
            timeout=getattr(settings, 'META_HTTP_TIMEOUT', 15),
        )
        if response.status_code not in {301, 302, 303, 307, 308}:
            return current_url, response
        destination = urljoin(current_url, response.headers.get('Location', ''))
        if not destination:
            raise ValueError('Meta devolvió una redirección sin destino.')
        if urlparse(destination).hostname != urlparse(current_url).hostname:
            current_headers.pop('Authorization', None)
        response.close()
        current_url = destination
    raise ValueError('El adjunto excede el máximo de redirecciones permitido.')


def _validate_attachment_content_type(value):
    """Rechaza contenido activo que no corresponde a un adjunto de chat."""

    content_type = (value or '').split(';')[0].strip().lower()
    allowed_prefixes = ('image/', 'audio/', 'video/')
    allowed_types = {
        'application/pdf',
        'application/octet-stream',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    if not content_type or not (content_type.startswith(allowed_prefixes) or content_type in allowed_types):
        raise ValueError('El tipo de contenido del adjunto no está permitido.')
    return content_type


@shared_task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, retry_jitter=True, max_retries=4)
def download_meta_attachment(self, attachment_id):
    """Descarga un adjunto Meta con límite de tamaño y protección SSRF."""

    attachment = ChatAttachment.objects.select_related('message__session__integration').get(pk=attachment_id)
    if attachment.file:
        return {'duplicate': True}
    integration = attachment.message.session.integration
    if not integration:
        raise ValueError('Adjunto sin integración.')
    url = attachment.metadata.get('url', '')
    headers = {}
    if attachment.message.session.channel == 'whatsapp' and attachment.external_media_id:
        media = graph_request(integration, 'GET', attachment.external_media_id)
        url = media.get('url', '')
        attachment.mime_type = media.get('mime_type', attachment.mime_type)
        headers['Authorization'] = f"Bearer {secret_store.decrypt(integration.access_token_encrypted)}"
    maximum = getattr(settings, 'CRM_ATTACHMENT_MAX_BYTES', 25 * 1024 * 1024)
    final_url, response = _open_public_stream(url, headers)
    response.raise_for_status()
    response_type = _validate_attachment_content_type(response.headers.get('Content-Type', ''))
    declared = int(response.headers.get('Content-Length') or 0)
    if declared > maximum:
        raise ValueError('El adjunto supera el tamaño permitido.')
    content = bytearray()
    for chunk in response.iter_content(64 * 1024):
        content.extend(chunk)
        if len(content) > maximum:
            raise ValueError('El adjunto supera el tamaño permitido.')
    extension = Path(urlparse(final_url).path).suffix[:12]
    name = Path(attachment.original_name).name or f'meta-{attachment.id}{extension}'
    attachment.mime_type = attachment.mime_type or response_type
    attachment.size = len(content)
    attachment.file.save(name, ContentFile(bytes(content)), save=False)
    attachment.save(update_fields=['file', 'mime_type', 'size'])
    publish_crm_event('attachment.ready', session_id=attachment.message.session_id, message_id=attachment.message_id)
    return {'attachment_id': attachment.id, 'size': attachment.size}


@shared_task
def audit_meta_tokens():
    """Registra tokens vencidos o próximos a vencer sin leer ni exponerlos.

    Meta no ofrece un flujo universal de renovación para WhatsApp, Messenger e
    Instagram. Esta vigilancia diaria permite rotarlos desde el panel antes de
    que interrumpan el canal y evita fingir una renovación incompatible.
    """

    now = timezone.now()
    warning_limit = now + timedelta(days=getattr(settings, 'META_TOKEN_WARNING_DAYS', 7))
    integrations = ChannelIntegration.objects.filter(
        active=True,
        token_expires_at__isnull=False,
        token_expires_at__lte=warning_limit,
    )
    created = 0
    for integration in integrations:
        action = 'integration.token_expired' if integration.token_expires_at <= now else 'integration.token_expiring'
        already_reported = ChatAuditEvent.objects.filter(
            action=action,
            details__integration_id=integration.id,
            created_at__date=now.date(),
        ).exists()
        if not already_reported:
            ChatAuditEvent.objects.create(
                action=action,
                details={
                    'integration_id': integration.id,
                    'channel': integration.channel,
                    'expires_at': integration.token_expires_at.isoformat(),
                },
            )
            created += 1
    return {'audits_created': created}


@shared_task
def validate_meta_oauth_connections():
    """Valida conexiones activas sin asumir una duración fija del token."""

    from .apps.meta.oauth import get_token_info

    checked = 0
    disabled = 0
    for connection in MetaConnection.objects.filter(is_active=True):
        checked += 1
        try:
            info = get_token_info(secret_store.decrypt(connection.access_token_encrypted))
            connection.token_last_validated_at = timezone.now()
            if info.get('is_valid'):
                connection.token_status = 'valid'
                connection.save(update_fields=['token_status', 'token_last_validated_at', 'updated_at'])
                continue
            connection.token_status = 'expired'
        except Exception:
            logger.warning('No fue posible validar la conexión Meta %s.', connection.pk, exc_info=True)
            connection.token_status = 'error'
            connection.token_last_validated_at = timezone.now()
        connection.is_active = False
        connection.save(update_fields=['token_status', 'token_last_validated_at', 'is_active', 'updated_at'])
        connection.channel_integrations.update(active=False)
        disabled += 1
    return {'checked': checked, 'disabled': disabled}


def _typing(session, enabled):
    if not session.integration or session.channel not in {'facebook', 'instagram'}:
        return
    if session.channel == 'facebook':
        from .apps.facebook.services import sender_action
    else:
        from .apps.instagram.services import sender_action
    try:
        sender_action(session.integration, session.external_thread_id, 'typing_on' if enabled else 'typing_off')
    except Exception:
        # El indicador es una mejora visual; nunca debe bloquear una respuesta.
        logger.warning('No fue posible actualizar el indicador de escritura.', exc_info=True)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def generate_omnichannel_bot_reply(self, user_message_id):
    """Usa la misma memoria estructurada de Ollama en cualquier canal."""

    logger.info('Iniciando respuesta omnicanal para message_id=%s.', user_message_id)

    retry_reply_id = None
    with transaction.atomic():
        user_message = ChatMessage.objects.select_for_update().select_related('session').get(pk=user_message_id)
        session = ChatSession.objects.select_for_update().get(pk=user_message.session_id)
        stale_before = timezone.now() - timedelta(minutes=5)
        if user_message.sender_type != 'user' or user_message.direction != 'inbound':
            return {'skipped': 'not_a_customer_message'}
        if session.channel != 'ecommerce' and not user_message.external_message_id:
            return {'skipped': 'missing_meta_message_id'}
        if session.status != 'bot':
            return {'skipped': 'conversation_not_in_bot_mode'}
        existing_reply = getattr(user_message, 'bot_reply', None)
        if existing_reply:
            if existing_reply.status != 'failed':
                return {'duplicate': True}
            # La respuesta ya fue generada: reintenta exactamente el mismo
            # mensaje sin volver a consultar Ollama ni crear duplicados.
            existing_reply.status = 'queued'
            existing_reply.save(update_fields=['status'])
            user_message.bot_processing_at = timezone.now()
            user_message.save(update_fields=['bot_processing_at'])
            retry_reply_id = existing_reply.id
        if user_message.bot_processing_at and user_message.bot_processing_at > stale_before:
            if retry_reply_id is None:
                return {'skipped': 'already_processing'}
        elif retry_reply_id is None:
            user_message.bot_processing_at = timezone.now()
            user_message.save(update_fields=['bot_processing_at'])

    if retry_reply_id is not None:
        reply = ChatMessage.objects.select_related('session__integration').get(pk=retry_reply_id)
        try:
            dispatch_outbound_message(reply)
        except Exception:
            ChatMessage.objects.filter(pk=user_message_id).update(bot_processing_at=None)
            raise
        ChatMessage.objects.filter(pk=user_message_id).update(bot_processing_at=None)
        publish_crm_event('message.created', session_id=reply.session_id, message_id=reply.id)
        return {'message_id': reply.id, 'retried': True}

    previous = list(session.messages.exclude(pk=user_message.pk).order_by('-created_at')[:8])
    history = [
        {
            'role': 'assistant' if item.sender_type in ('bot', 'agent') else 'user',
            'content': item.text,
        }
        for item in reversed(previous)
    ]
    try:
        _typing(session, True)
        result = ollama_service.get_bot_response(
            user_message.text,
            conversation_history=history,
            conversation_state=session.conversation_state,
            summary=session.conversation_summary,
        )
    except Exception:
        logger.exception('Falló Ollama para message_id=%s; Celery reintentará según la política configurada.', user_message_id)
        ChatMessage.objects.filter(pk=user_message.pk).update(bot_processing_at=None)
        raise
    finally:
        _typing(session, False)
    with transaction.atomic():
        session = ChatSession.objects.select_for_update().get(pk=session.pk)
        user_message = ChatMessage.objects.select_for_update().get(pk=user_message.pk)
        if session.status != 'bot' or hasattr(user_message, 'bot_reply'):
            return {'skipped': 'conversation_taken_or_replied'}
        session.conversation_state = result.get('state', session.conversation_state)
        session.conversation_summary = result.get('summary', session.conversation_summary)
        if result.get('needs_agent'):
            session.status = 'waiting'
        session.save(update_fields=['conversation_state', 'conversation_summary', 'status', 'updated_at'])
        reply = ChatMessage.objects.create(
            session=session, reply_to_message=user_message,
            text=result.get('response', 'No pude procesar el mensaje.'),
            sender_type='bot', direction='outbound', status='queued',
            metadata={'reply_to_message_id': user_message.id},
        )
        session.last_bot_message_at = reply.created_at
        session.inactivity_warning_at = None
        session.save(update_fields=['last_bot_message_at', 'inactivity_warning_at', 'updated_at'])
        if result.get('needs_agent'):
            publish_crm_event('session.pending', session_id=session.id, message_id=user_message.id)
    try:
        dispatch_outbound_message(reply)
    except Exception:
        ChatMessage.objects.filter(pk=user_message_id).update(bot_processing_at=None)
        raise
    ChatMessage.objects.filter(pk=user_message_id).update(bot_processing_at=None)
    logger.info('Respuesta omnicanal enviada message_id=%s reply_id=%s session_id=%s.', user_message_id, reply.id, session.id)
    publish_crm_event('message.created', session_id=session.id, message_id=reply.id)
    return {'message_id': reply.id}


@shared_task
def close_inactive_bot_sessions():
    """Advierte una sola vez a los 2 minutos y cierra al minuto siguiente."""
    now = timezone.now()
    warned = closed = 0
    candidates = ChatSession.objects.filter(status__in=('bot', 'waiting'), last_bot_message_at__isnull=False)
    for session in candidates.iterator():
        # Una respuesta posterior del cliente cancela cualquier cierre pendiente.
        if session.last_customer_message_at and session.last_customer_message_at > session.last_bot_message_at:
            if session.inactivity_warning_at:
                ChatSession.objects.filter(pk=session.pk).update(inactivity_warning_at=None)
            continue
        if session.inactivity_warning_at:
            if session.inactivity_warning_at <= now - timedelta(minutes=1):
                updated = ChatSession.objects.filter(
                    pk=session.pk, status__in=('bot', 'waiting'),
                    inactivity_warning_at=session.inactivity_warning_at,
                ).update(status='closed')
                if updated:
                    closed += 1
                    publish_crm_event('session.closed', session_id=session.id)
            continue
        if session.last_bot_message_at > now - timedelta(minutes=2):
            continue
        message = session.messages.filter(
            metadata__system_event='inactivity_warning',
            created_at__gte=session.last_bot_message_at,
            status__in=('queued', 'failed'),
        ).order_by('-created_at').first()
        if message is None:
            message = ChatMessage.objects.create(
                session=session, text=INACTIVITY_WARNING_TEXT, sender_type='bot',
                direction='outbound', status='queued', metadata={'system_event': 'inactivity_warning'},
            )
        elif message.status == 'failed':
            message.status = 'queued'
            message.save(update_fields=['status'])
        try:
            dispatch_outbound_message(message)
        except Exception:
            logger.exception('No se pudo enviar aviso de inactividad de la sesión %s.', session.id)
            continue
        # El minuto para cerrar empieza solamente cuando el aviso sí se envió.
        updated = ChatSession.objects.filter(
            pk=session.pk,
            status__in=('bot', 'waiting'),
            inactivity_warning_at__isnull=True,
            last_bot_message_at=session.last_bot_message_at,
        ).update(inactivity_warning_at=timezone.now())
        if not updated:
            continue
        warned += 1
        publish_crm_event('message.created', session_id=session.id, message_id=message.id)
    logger.info('Barrido de inactividad finalizado: avisos=%s cierres=%s.', warned, closed)
    return {'warned': warned, 'closed': closed}
