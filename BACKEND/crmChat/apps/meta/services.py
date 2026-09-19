"""Servicios compartidos de seguridad, Graph API y persistencia omnicanal."""

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone as datetime_timezone

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
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

    def __init__(
        self, message, *, http_status=None, meta_code=None, meta_subcode=None,
        request_id='', endpoint='', phase='',
    ):
        super().__init__(message)
        self.http_status = http_status
        self.meta_code = meta_code
        self.meta_subcode = meta_subcode
        self.request_id = request_id
        self.endpoint = endpoint
        self.phase = phase


class UnmatchedIntegrationError(ValueError):
    """Evento auténtico de una cuenta no conectada; no debe reintentarse."""


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


def verify_webhook_token(candidate, channel=''):
    """Compara el token global/específico o el hash del canal configurado."""

    if not candidate:
        return False
    setting_by_channel = {
        ChannelIntegration.CHANNEL_INSTAGRAM: 'META_WEBHOOK_VERIFY_TOKEN_INSTAGRAM',
        ChannelIntegration.CHANNEL_FACEBOOK: 'META_WEBHOOK_VERIFY_TOKEN_FACEBOOK',
        ChannelIntegration.CHANNEL_WHATSAPP: 'META_WEBHOOK_VERIFY_TOKEN_WHATSAPP',
    }
    specific_name = setting_by_channel.get(channel)
    specific_token = getattr(settings, specific_name, '') if specific_name else ''
    # Si existe un token específico, el endpoint tipado no acepta el global.
    # Si no existe, conserva compatibilidad con la estrategia unificada.
    configured_token = specific_token or getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', '')
    if configured_token and hmac.compare_digest(candidate, configured_token):
        return True
    digest = secret_store.digest(candidate)
    integrations = ChannelIntegration.objects.filter(active=True, verify_token_digest=digest)
    if channel:
        integrations = integrations.filter(channel=channel)
    return integrations.exists()


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


def _record_integration_error(integration, detail):
    safe_detail = ' '.join(str(detail).split())[:500]
    if getattr(integration, 'pk', None):
        ChannelIntegration.objects.filter(pk=integration.pk).update(
            connection_status='error', last_error=safe_detail,
        )
    return safe_detail


def graph_request(
    integration, method, path, *, json_body=None, params=None, base_url=None,
    record_error=True,
):
    """Ejecuta una solicitud Graph sin incluir tokens en URL, logs o errores."""

    encrypted_token = integration.access_token_encrypted
    if not encrypted_token and integration.meta_facebook_page_id:
        encrypted_token = integration.meta_facebook_page.page_access_token_encrypted
    token = secret_store.decrypt(encrypted_token)
    if not token:
        detail = 'La integración no tiene token de acceso.'
        if record_error:
            detail = _record_integration_error(integration, detail)
        raise MetaAPIError(detail)
    version = integration.graph_api_version
    if not version:
        detail = 'La integración no tiene versión de Graph API.'
        if record_error:
            detail = _record_integration_error(integration, detail)
        raise MetaAPIError(detail)
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
            detail = ' '.join(str(detail).replace(token, '[credencial oculta]').split())[:500]
            request_id = str(
                response.headers.get('x-fb-request-id')
                or response.headers.get('x-fb-trace-id')
                or error.get('fbtrace_id')
                or ''
            )[:120]
            logger.warning(
                'Meta Graph API rechazó una solicitud: integration_id=%s method=%s endpoint=%s '
                'status=%s code=%s subcode=%s request_id=%s detail=%s',
                integration.pk, method.upper(), path.split('?', 1)[0], response.status_code,
                code, subcode or '-', request_id or '-', detail,
            )
            subcode_text = f', subcódigo {subcode}' if subcode else ''
            error_message = (
                f'Graph API rechazó la solicitud ({response.status_code}, código {code}{subcode_text}): {detail}'
            )
            visible_error = (
                _record_integration_error(integration, error_message)
                if record_error else error_message
            )
            raise MetaAPIError(
                visible_error,
                http_status=response.status_code,
                meta_code=code,
                meta_subcode=subcode,
                request_id=request_id,
                endpoint=path.split('?', 1)[0],
                phase='graph_validation',
            )
        return data
    except requests.RequestException as exc:
        detail = 'No fue posible conectar con Meta Graph API.'
        if record_error:
            detail = _record_integration_error(integration, detail)
        raise MetaAPIError(detail) from exc


def validate_whatsapp_token_permissions(integration):
    """Introspección de solo lectura; jamás envía mensajes de prueba."""

    app_id = integration.app_id or getattr(settings, 'META_APP_ID', '')
    encrypted_secret = integration.app_secret_encrypted
    app_secret = secret_store.decrypt(encrypted_secret) if encrypted_secret else getattr(settings, 'META_APP_SECRET', '')
    if not app_id or not app_secret:
        raise MetaAPIError('Faltan App ID y App Secret para comprobar permisos de WhatsApp.')
    token = secret_store.decrypt(integration.access_token_encrypted)
    if not token:
        raise MetaAPIError('Falta el Access Token de WhatsApp.')
    version = integration.graph_api_version
    if not version:
        raise MetaAPIError('Falta la versión de Graph API.')
    url = f"{settings.META_GRAPH_API_URL.rstrip('/')}/{version.strip('/')}/debug_token"
    try:
        response = requests.get(
            url,
            headers={'Authorization': f'Bearer {app_id}|{app_secret}'},
            params={'input_token': token},
            timeout=getattr(settings, 'META_HTTP_TIMEOUT', 15),
        )
        data = response.json() if response.content else {}
    except (requests.RequestException, ValueError) as exc:
        raise MetaAPIError('No fue posible comprobar los permisos del token de WhatsApp.') from exc
    if not response.ok:
        raise MetaAPIError(f'Meta rechazó la comprobación del token de WhatsApp ({response.status_code}).')
    info = data.get('data') if isinstance(data, dict) else None
    if not isinstance(info, dict):
        raise MetaAPIError('Meta devolvió una respuesta inválida al comprobar el token de WhatsApp.')
    if not info.get('is_valid') or str(info.get('app_id', '')) != app_id:
        raise MetaAPIError('El token de WhatsApp no es válido para la aplicación configurada.')
    missing = {'whatsapp_business_management', 'whatsapp_business_messaging'} - set(info.get('scopes') or [])
    if missing:
        raise MetaAPIError(f'El token de WhatsApp carece de permisos: {", ".join(sorted(missing))}.')
    expires_at = info.get('expires_at')
    if expires_at:
        try:
            expired = int(expires_at) <= int(timezone.now().timestamp())
        except (TypeError, ValueError) as exc:
            raise MetaAPIError('Meta devolvió una expiración de token inválida.') from exc
        if expired:
            raise MetaAPIError('El token de WhatsApp está vencido.')
    return info


def validate_integration_connection(integration):
    """Comprueba identidad y permisos sin enviar mensajes de prueba."""

    if integration.meta_connection_id:
        from .oauth import get_page_details, validate_access_token, validate_oauth_webhook_subscriptions

        connection = integration.meta_connection
        if not connection.access_token_encrypted or connection.token_status in {'revoked', 'expired', 'error'}:
            raise MetaAPIError('La autorización OAuth de esta cuenta fue revocada o está vencida.')
        user_token = secret_store.decrypt(connection.access_token_encrypted)
        token_info = validate_access_token(user_token)
        if str(token_info.get('user_id', '')) != connection.facebook_user_id:
            raise MetaAPIError('El token OAuth ya no corresponde al usuario de Facebook autorizado.')
        page = integration.meta_facebook_page
        if not page or not page.page_access_token_encrypted:
            raise MetaAPIError('No existe un Page Access Token vigente para esta cuenta.')
        page_data = get_page_details(page.page_id, user_token)
        if str(page_data.get('id', '')) != page.page_id or not page_data.get('access_token'):
            raise MetaAPIError('Meta ya no confirmó el acceso a la página vinculada.')
        if integration.channel == 'facebook' and 'MESSAGING' not in (page_data.get('tasks') or []):
            raise MetaAPIError('La página ya no tiene tarea de mensajería.')
        if integration.channel == 'instagram':
            linked = page_data.get('instagram_business_account') or {}
            if str(linked.get('id', '')) != integration.instagram_account_id:
                raise MetaAPIError('Instagram ya no está asociada a la página autorizada.')
        if integration.channel in {'facebook', 'instagram'}:
            validate_oauth_webhook_subscriptions(
                integration.channel,
                page.page_id,
                page_data['access_token'],
            )

    if integration.channel == 'whatsapp':
        if not integration.external_account_id or not integration.phone_number_id:
            raise MetaAPIError('WhatsApp requiere WABA ID y Phone Number ID.')
        validate_whatsapp_token_permissions(integration)
        # La relación real WABA → número se comprueba con el mismo token que
        # se usará para responder. Un ID de otro negocio nunca se activa.
        after = ''
        found = False
        while True:
            params = {'fields': 'id,display_phone_number,verified_name', 'limit': 100}
            if after:
                params['after'] = after
            inventory = graph_request(
                integration, 'GET', f'{integration.external_account_id}/phone_numbers', params=params,
            )
            for phone in inventory.get('data') or []:
                if str(phone.get('id', '')) == integration.phone_number_id:
                    found = True
                    break
            if found:
                break
            paging = inventory.get('paging') or {}
            after = ((paging.get('cursors') or {}).get('after') or '') if paging.get('next') else ''
            if not after:
                raise MetaAPIError('El Phone Number ID no pertenece al WABA configurado o el token no tiene acceso.')
        data = graph_request(
            integration, 'GET', integration.phone_number_id,
            params={'fields': 'id,display_phone_number,verified_name'},
        )
        if str(data.get('id', '')) != integration.phone_number_id or not data.get('display_phone_number'):
            raise MetaAPIError('Meta no confirmó el número de WhatsApp configurado.')
        subscriptions = graph_request(integration, 'GET', f'{integration.external_account_id}/subscribed_apps')
        if not isinstance(subscriptions, dict) or not isinstance(subscriptions.get('data'), list):
            raise MetaAPIError('Meta no confirmó las suscripciones del webhook del WABA.')
        subscribed_app_ids = {
            str(item.get('whatsapp_business_api_data', {}).get('id') or item.get('id') or '')
            for item in subscriptions.get('data') or []
            if isinstance(item, dict)
        }
        app_id = integration.app_id or getattr(settings, 'META_APP_ID', '')
        if app_id not in subscribed_app_ids:
            raise MetaAPIError('La aplicación no está suscrita al webhook de este WABA en Meta Developers.')
        return {
            'valid': True, 'remote_id': integration.phone_number_id,
            'name': data.get('verified_name') or data['display_phone_number'],
            'display_phone_number': data['display_phone_number'],
        }
    elif integration.channel == 'facebook':
        path = integration.page_id
        params = {'fields': 'id,name'}
        base_url = None
    elif integration.channel == 'instagram':
        path = integration.instagram_account_id
        params = {'fields': 'id,username' if integration.meta_facebook_page_id else 'id,username,account_type'}
        base_url = None if integration.meta_facebook_page_id else integration.configuration.get('api_base_url', 'https://graph.instagram.com')
    else:
        raise MetaAPIError('Canal no soportado.')
    if not path:
        raise MetaAPIError('Falta el identificador de la cuenta externa.')
    data = graph_request(integration, 'GET', path, params=params, base_url=base_url)
    if str(data.get('id', '')) != path:
        raise MetaAPIError('La cuenta devuelta por Meta no corresponde al ID configurado.')
    if integration.channel == 'instagram' and not integration.meta_facebook_page_id:
        if data.get('account_type') not in {'BUSINESS', 'MEDIA_CREATOR'}:
            raise MetaAPIError('La cuenta de Instagram no es Professional/Business.')
    return {'valid': True, 'remote_id': str(data.get('id', '')), 'name': data.get('name') or data.get('username') or data.get('verified_name', '')}


@transaction.atomic
def disconnect_integration(integration):
    """Revoca el acceso local conservando los IDs y conversaciones históricas."""

    if integration.channel == 'instagram':
        cache.set(f'instagram-oauth-generation:{integration.pk}', secrets.token_urlsafe(32), timeout=86400)
    integration.active = False
    integration.connection_status = 'disconnected'
    integration.disconnected_at = timezone.now()
    integration.last_error = ''
    integration.access_token_encrypted = ''
    integration.app_secret_encrypted = ''
    integration.verify_token_digest = ''
    integration.token_expires_at = None
    integration.meta_connection = None
    integration.meta_facebook_page = None
    integration.meta_instagram_account = None
    integration.configuration = {**integration.configuration, 'bot_enabled': False}
    integration.save(update_fields=[
        'active', 'connection_status', 'disconnected_at', 'last_error',
        'access_token_encrypted', 'app_secret_encrypted', 'verify_token_digest',
        'token_expires_at', 'meta_connection', 'meta_facebook_page',
        'meta_instagram_account', 'configuration', 'updated_at',
    ])
    return integration


def accept_webhook(raw_body, signature_header, forced_channel=''):
    """Valida, limita y registra idempotentemente un webhook de Meta."""

    max_bytes = getattr(settings, 'META_WEBHOOK_MAX_BYTES', 2 * 1024 * 1024)
    if len(raw_body) > max_bytes:
        raise ValueError('El webhook supera el tamaño permitido.')
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('El webhook no contiene JSON válido.') from exc
    if not isinstance(payload, dict) or not isinstance(payload.get('entry'), list):
        raise ValueError('El webhook no contiene la estructura de eventos de Meta.')
    if any(not isinstance(entry, dict) for entry in payload['entry']):
        raise ValueError('El webhook contiene una entrada inválida.')
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
    if not external_id:
        raise UnmatchedIntegrationError(f'El evento de {event.channel} no contiene ID de cuenta.')
    if event.channel == 'whatsapp':
        waba_id = str(event.metadata.get('waba_id', ''))
        if not waba_id:
            raise UnmatchedIntegrationError('El evento de WhatsApp no contiene WABA ID.')
        matches = query.filter(phone_number_id=external_id, external_account_id=waba_id)
    elif event.channel == 'facebook':
        matches = query.filter(models_query('page_id', external_id, 'external_account_id'))
    else:
        matches = query.filter(models_query('instagram_account_id', external_id, 'external_account_id'))
    integrations = list(matches[:2])
    if len(integrations) > 1:
        raise UnmatchedIntegrationError(f'Hay integraciones activas ambiguas para {event.channel}.')
    return integrations[0] if integrations else None


def models_query(primary_field, value, fallback_field):
    """Usa el ID principal; solo admite el ID legado si el principal falta."""

    from django.db.models import Q

    return Q(**{primary_field: value}) | (Q(**{primary_field: ''}) & Q(**{fallback_field: value}))


@transaction.atomic
def persist_normalized_message(event):
    """Guarda un evento normalizado y devuelve el mensaje creado o actualizado."""

    integration = _find_integration(event)
    if not integration:
        raise UnmatchedIntegrationError(f'No hay una integración activa para {event.channel}.')

    if event.status:
        if event.external_message_id:
            message = ChatMessage.objects.filter(
                external_message_id=event.external_message_id,
                session__integration=integration,
            ).first()
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
        existing = ChatMessage.objects.filter(
            external_message_id=event.external_message_id,
            session__integration=integration,
        ).first()
        if existing:
            return existing

    identity = ChannelIdentity.objects.select_related('contact').filter(
        integration=integration,
        external_id=event.sender_id,
    ).first()
    profile = {}
    resolved_sender_name = event.sender_name
    if event.channel == ChannelIntegration.CHANNEL_INSTAGRAM and (
        not identity
        or not identity.display_name
        or identity.contact.name == f'Cliente {event.channel}'
    ):
        try:
            from crmChat.apps.instagram.services import get_sender_profile

            profile = get_sender_profile(integration, event.sender_id)
            resolved_sender_name = (
                resolved_sender_name
                or str(profile.get('name') or '').strip()
                or str(profile.get('username') or '').strip()
            )[:200]
            logger.info(
                'Perfil Meta resuelto: channel=%s integration_id=%s sender=%s has_name=%s.',
                event.channel, integration.id, _mask_destination(event.sender_id),
                bool(resolved_sender_name),
            )
        except MetaAPIError as exc:
            logger.warning(
                'No fue posible enriquecer el perfil Meta: channel=%s integration_id=%s '
                'sender=%s error=%s.',
                event.channel, integration.id, _mask_destination(event.sender_id), str(exc)[:300],
            )
    contact_created = False
    if not identity:
        contact = CRMContact.objects.create(
            name=resolved_sender_name or f'Cliente {event.channel}',
            avatar_url=str(profile.get('profile_pic') or '')[:1000],
        )
        identity = ChannelIdentity.objects.create(
            integration=integration,
            external_id=event.sender_id,
            contact=contact,
            display_name=resolved_sender_name,
            profile_data={
                key: profile[key]
                for key in ('id', 'name', 'username', 'profile_pic')
                if profile.get(key)
            },
        )
        contact_created = True
    contact = identity.contact
    contact_update_fields = []
    if resolved_sender_name and contact.name != resolved_sender_name:
        contact.name = resolved_sender_name
        contact_update_fields.append('name')
    profile_picture = str(profile.get('profile_pic') or '')[:1000]
    if profile_picture and contact.avatar_url != profile_picture:
        contact.avatar_url = profile_picture
        contact_update_fields.append('avatar_url')
    if contact_update_fields:
        contact.save(update_fields=[*contact_update_fields, 'updated_at'])
    if resolved_sender_name and identity.display_name != resolved_sender_name:
        identity.display_name = resolved_sender_name
        identity.profile_data = {
            **(identity.profile_data or {}),
            **{
                key: profile[key]
                for key in ('id', 'name', 'username', 'profile_pic')
                if profile.get(key)
            },
        }
        identity.save(update_fields=['display_name', 'profile_data', 'updated_at'])
    logger.info(
        'Identidad Meta resuelta: channel=%s integration_id=%s contact_id=%s created=%s.',
        event.channel, integration.id, contact.id, contact_created,
    )

    session_query = ChatSession.objects.filter(
        integration=integration,
        external_thread_id=event.sender_id,
    )
    session = session_query.exclude(status='closed').order_by('-updated_at', '-id').first()
    session_created = False
    if session is None and event.channel == ChannelIntegration.CHANNEL_INSTAGRAM:
        session = session_query.order_by('-updated_at', '-id').first()
        if session is not None:
            session.status = 'bot'
            session.user_name = resolved_sender_name or contact.name
            session.inactivity_warning_at = None
            session.save(update_fields=['status', 'user_name', 'inactivity_warning_at', 'updated_at'])
    if session is None:
        session_defaults = {
            'contact': contact,
            'channel': event.channel,
            'user_name': resolved_sender_name or contact.name,
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
                session_created = True
        except IntegrityError:
            session = ChatSession.objects.exclude(status='closed').get(
                integration=integration,
                external_thread_id=event.sender_id,
            )
    logger.info(
        'Conversación Meta resuelta: channel=%s integration_id=%s contact_id=%s '
        'session_id=%s created=%s.',
        event.channel, integration.id, contact.id, session.id, session_created,
    )
    try:
        with transaction.atomic():
            message = ChatMessage.objects.create(
                session=session,
                text=event.text,
                sender_type='user',
                sender_name=resolved_sender_name or contact.name,
                direction='inbound',
                message_type=event.message_type,
                external_message_id=event.external_message_id or None,
                external_timestamp=_timestamp(event.timestamp),
                reply_to_external_id=event.reply_to_external_id,
                metadata=event.metadata,
                status='received',
            )
    except IntegrityError:
        if not event.external_message_id:
            raise
        return ChatMessage.objects.get(external_message_id=event.external_message_id)
    for attachment in event.attachments:
        ChatAttachment.objects.create(
            message=message,
            external_media_id=attachment.get('id', ''),
            original_name=attachment.get('name', ''),
            mime_type=attachment.get('mime_type', ''),
            metadata={key: value for key, value in attachment.items() if key not in {'token'}},
        )
    session.last_customer_message_at = message.external_timestamp or message.created_at
    session.inactivity_warning_at = None
    session.unread_by_agent += 1
    session.save(update_fields=['last_customer_message_at', 'inactivity_warning_at', 'unread_by_agent', 'updated_at'])
    logger.info(
        'Mensaje Meta persistido: channel=%s integration_id=%s contact_id=%s '
        'session_id=%s message_id=%s type=%s attachments=%s.',
        event.channel, integration.id, contact.id, session.id, message.id,
        message.message_type, len(event.attachments),
    )
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
            ChannelIntegration.CHANNEL_WHATSAPP_WEB,
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
        if session.channel == ChannelIntegration.CHANNEL_WHATSAPP_WEB:
            from crmChat.apps.whatsapp_web.services import send_message as gateway_send
            response = gateway_send(message, outbound_payload)
            external_id = response.get('external_message_id', '')
        elif session.channel == ChannelIntegration.CHANNEL_WHATSAPP:
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
        if not external_id:
            raise MetaAPIError('Meta no confirmó el identificador del mensaje enviado.')
        message.external_message_id = external_id or None
        message.status = 'sent'
        message.direction = 'outbound'
        if message.external_timestamp is None:
            message.external_timestamp = timezone.now()
        message.save(update_fields=['external_message_id', 'status', 'direction', 'external_timestamp'])
        ChannelIntegration.objects.filter(pk=session.integration_id, active=True).update(
            connection_status='connected', last_error='',
        )
        logger.info(
            'Meta aceptó el mensaje: session_id=%s message_id=%s channel=%s '
            'external_message_id=%s status=%s',
            session.id, message.id, session.channel, external_id or '-', message.status,
        )
        return message
    except Exception as exc:
        safe_error = ' '.join(str(exc).split())[:500]
        message.status = 'failed'
        message.metadata = {**message.metadata, 'error': safe_error}
        message.save(update_fields=['status', 'metadata'])
        if session.integration_id:
            ChannelIntegration.objects.filter(pk=session.integration_id).update(last_error=safe_error)
        logger.warning(
            'Falló envío externo: session_id=%s message_id=%s contact_id=%s channel=%s '
            'type=%s destination=%s error=%s',
            session.id, message.id, session.contact_id, session.channel,
            message.message_type, _mask_destination(recipient), safe_error,
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
    integration_ids = set()
    try:
        normalized = normalize_payload(webhook_event.payload, webhook_event.channel)
        logger.info(
            'Webhook Meta normalizado: event_id=%s channel=%s events=%s attempt=%s.',
            webhook_event.id, webhook_event.channel, len(normalized), webhook_event.attempts,
        )
        messages = []
        resolved = []
        for event in normalized:
            integration = _find_integration(event)
            if not integration:
                raise UnmatchedIntegrationError(f'No hay una integración activa para {event.channel}.')
            integration_ids.add(integration.pk)
            logger.info(
                'Integración Meta encontrada: event_id=%s channel=%s account_id=%s integration_id=%s.',
                webhook_event.id, event.channel, event.integration_external_id, integration.pk,
            )
            resolved.append((event, integration))
        if len(integration_ids) == 1:
            webhook_event.integration_id = next(iter(integration_ids))
            webhook_event.save(update_fields=['integration'])
        for event, integration in resolved:
            message = persist_normalized_message(event)
            if message is not None:
                messages.append(message)
        if integration_ids:
            ChannelIntegration.objects.filter(pk__in=integration_ids, active=True).update(
                last_webhook_at=timezone.now(),
                connection_status='connected',
                last_error='',
            )
        webhook_event.status = 'processed'
        webhook_event.processed_at = timezone.now()
        webhook_event.error_message = ''
        webhook_event.save(update_fields=['integration', 'status', 'processed_at', 'error_message'])
        logger.info(
            'Webhook Meta procesado: event_id=%s channel=%s integrations=%s messages=%s.',
            webhook_event.id, webhook_event.channel, len(integration_ids), len(messages),
        )
        return messages
    except Exception as exc:
        safe_error = ' '.join(str(exc).split())[:500]
        webhook_event.status = 'failed'
        webhook_event.error_message = safe_error
        webhook_event.save(update_fields=['status', 'error_message'])
        if integration_ids:
            ChannelIntegration.objects.filter(pk__in=integration_ids).update(
                connection_status='error', last_error=safe_error,
            )
        logger.warning(
            'Webhook Meta falló: event_id=%s channel=%s integrations=%s error=%s.',
            webhook_event.id, webhook_event.channel, len(integration_ids), safe_error,
        )
        raise
