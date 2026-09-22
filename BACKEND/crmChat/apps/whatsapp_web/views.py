import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from urllib.parse import urlparse
from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crmChat.apps.meta.views import IsCRMAdministrator
from crmChat.models import ChannelIdentity, ChannelIntegration, ChatAttachment, ChatAuditEvent, ChatMessage, ChatSession, CRMContact
from crmChat.realtime import publish_crm_event
from .auth import internal_authenticate
from .jids import external_message_key, mask_jid, normalize_user_jid
from .services import gateway_request


ALLOWED_TYPES = {'text', 'image', 'audio', 'video', 'document', 'sticker', 'interactive'}
ALLOWED_STATES = {'disconnected', 'waiting_for_qr', 'qr_ready', 'connecting', 'connected', 'logged_out', 'reconnecting', 'error'}
ALLOWED_ORIGINS = {'customer', 'mobile', 'crm'}
ALLOWED_EVENT_SOURCES = {'notify', 'append', 'history'}

logger = logging.getLogger(__name__)


def _integration(connection_id, create=False):
    query = ChannelIntegration.objects.filter(channel=ChannelIntegration.CHANNEL_WHATSAPP_WEB, external_account_id=connection_id)
    integration = query.first()
    if not integration and create:
        integration = ChannelIntegration.objects.create(
            name='WhatsApp Web Gateway (experimental)', channel=ChannelIntegration.CHANNEL_WHATSAPP_WEB,
            external_account_id=connection_id, configuration={
                'bot_enabled': bool(getattr(settings, 'WHATSAPP_GATEWAY_BOT_ENABLED', False)),
                'experimental': True, 'gateway_status': 'disconnected',
            },
        )
    return integration


class InternalAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    # These private routes use a signed, time-limited request with replay
    # protection. The public anonymous limit (60/min) must not throttle a
    # WhatsApp history sync and amplify retries from the gateway.
    throttle_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        internal_authenticate(request)


class InternalStatusView(InternalAPIView):
    def post(self, request):
        connection_id = str(request.data.get('connection_id') or '')
        gateway_status = str(request.data.get('status') or '')
        if not connection_id or gateway_status not in ALLOWED_STATES:
            return Response({'detail': 'Estado del gateway inválido.'}, status=400)
        integration = _integration(connection_id, create=True)
        integration.configuration = {
            **(integration.configuration or {}), 'experimental': True, 'gateway_status': gateway_status,
            'last_connected_at': request.data.get('last_connected_at') or '',
        }
        integration.display_phone_number = str(request.data.get('phone_number') or '')[:40]
        integration.last_error = str(request.data.get('last_error') or '')[:500]
        integration.active = gateway_status == 'connected'
        integration.connection_status = 'connected' if integration.active else ('error' if gateway_status == 'error' else 'disconnected')
        integration.disconnected_at = None if integration.active else timezone.now()
        integration.save(update_fields=['configuration', 'display_phone_number', 'last_error', 'active', 'connection_status', 'disconnected_at', 'updated_at'])
        return Response({'updated': True})


class InternalMediaView(InternalAPIView):
    def post(self, request):
        connection_id = str(request.data.get('connection_id') or '')
        raw = str(request.data.get('data_base64') or '')
        if not _integration(connection_id) or not raw:
            return Response({'detail': 'Conexión o archivo inválido.'}, status=400)
        try:
            content = base64.b64decode(raw, validate=True)
        except ValueError:
            return Response({'detail': 'Archivo Base64 inválido.'}, status=400)
        if len(content) > settings.WHATSAPP_GATEWAY_MAX_MEDIA_BYTES:
            return Response({'detail': 'El archivo supera el límite permitido.'}, status=413)
        media_id = str(uuid.uuid4())
        supplied_name = os.path.basename(str(request.data.get('file_name') or 'archivo').replace('\\', '/'))
        safe_name = ''.join(char for char in supplied_name if char.isalnum() or char in '._-')[:120] or 'archivo'
        stored = default_storage.save(f'crm_gateway/{media_id}-{safe_name}', ContentFile(content))
        cache.set(f'whatsapp-web-media:{media_id}', {
            'path': stored, 'name': safe_name, 'mime_type': str(request.data.get('mime_type') or '')[:150], 'size': len(content),
        }, timeout=900)
        return Response({'media_id': media_id, 'url': ''}, status=201)


class InternalWebhookView(InternalAPIView):
    @transaction.atomic
    def post(self, request):
        data = request.data
        connection_id = str(data.get('connection_id') or '')
        raw_remote_jid = str(data.get('remote_jid') or '')
        remote_jid = normalize_user_jid(raw_remote_jid)
        message_id = str(data.get('message_id') or '').strip()
        key = external_message_key(connection_id, message_id)
        message_type = str(data.get('type') or '')
        origin = str(data.get('origin') or 'customer')
        event_source = str(data.get('event_source') or 'notify')
        if data.get('is_group'):
            return Response({'ignored': True})
        if not remote_jid:
            logger.warning(
                'WhatsApp Web rechazó JID: connection_id=%s jid=%s external_id=%s.',
                connection_id, mask_jid(raw_remote_jid), message_id or '-',
            )
            return Response({'ignored': True, 'reason': 'invalid_jid'})
        if (
            not connection_id or not key or message_type not in ALLOWED_TYPES
            or origin not in ALLOWED_ORIGINS or event_source not in ALLOWED_EVENT_SOURCES
        ):
            return Response({'detail': 'Evento entrante inválido.'}, status=400)
        integration = _integration(connection_id)
        if not integration:
            return Response({'detail': 'La conexión WhatsApp Web no está configurada.'}, status=409)
        # Recibir un evento autenticado del gateway confirma que Baileys está
        # conectado. Esto recupera el estado de Django si el primer POST de
        # estado ocurrió durante el arranque del backend.
        if not integration.active:
            integration.active = True
            integration.connection_status = 'connected'
            integration.disconnected_at = None
            integration.configuration = {
                **(integration.configuration or {}),
                'experimental': True,
                'gateway_status': 'connected',
            }
            integration.save(update_fields=['active', 'connection_status', 'disconnected_at', 'configuration', 'updated_at'])

        supplied_key = str(data.get('idempotency_key') or '')[:255]
        client_message_id = str(data.get('client_message_id') or '')[:255]
        existing_query = Q(external_message_id__in=[value for value in (key, message_id, supplied_key) if value])
        existing_query |= Q(metadata__gateway_message_id=message_id)
        if client_message_id:
            existing_query |= Q(client_message_id=client_message_id)
            existing_query |= Q(metadata__client_message_id=client_message_id)
        existing = ChatMessage.objects.filter(existing_query).order_by('id').first()
        if existing:
            metadata = {
                **(existing.metadata or {}), 'gateway_message_id': message_id,
                'origin': origin, 'event_source': event_source, 'gateway_echo_seen': True,
            }
            update_fields = ['metadata']
            existing.metadata = metadata
            if origin in {'mobile', 'crm'} and existing.status in {'queued', 'failed'}:
                existing.status = 'sent'
                update_fields.append('status')
            if existing.external_message_id != key and not ChatMessage.objects.filter(external_message_id=key).exclude(pk=existing.pk).exists():
                existing.external_message_id = key
                update_fields.append('external_message_id')
            existing.save(update_fields=update_fields)
            logger.info(
                'WhatsApp Web deduplicado: message_id=%s session_id=%s origin=%s source=%s.',
                existing.pk, existing.session_id, origin, event_source,
            )
            return Response({'created': False, 'message_id': existing.pk})

        supplied_aliases = data.get('jid_aliases') if isinstance(data.get('jid_aliases'), list) else []
        aliases = {
            normalize_user_jid(value)
            for value in [remote_jid, data.get('reply_jid'), data.get('source_jid'), *supplied_aliases]
        } - {''}
        identity = ChannelIdentity.objects.select_related('contact').filter(
            integration=integration, external_id__in=aliases,
        ).order_by('id').first()
        # pushName pertenece al remitente. En ecos enviados desde el CRM o el
        # teléfono representa nuestra cuenta y no debe reemplazar al cliente.
        name = str(data.get('push_name') or '')[:200] if origin == 'customer' else ''
        profile_picture_url = str(data.get('profile_picture_url') or '').strip()[:1000] if origin == 'customer' else ''
        if profile_picture_url:
            parsed_profile_picture = urlparse(profile_picture_url)
            if parsed_profile_picture.scheme != 'https' or not parsed_profile_picture.netloc:
                profile_picture_url = ''
        fallback_name = 'Usuario de WhatsApp'
        if not identity:
            identifier = str(data.get('number') or remote_jid.split('@', 1)[0])
            contact = CRMContact.objects.create(
                name=name or fallback_name,
                phone=identifier if remote_jid.endswith('@s.whatsapp.net') else '',
                avatar_url=profile_picture_url,
            )
            try:
                with transaction.atomic():
                    identity = ChannelIdentity.objects.create(
                        contact=contact, integration=integration, external_id=remote_jid,
                        display_name=name or fallback_name,
                    )
            except IntegrityError:
                contact.delete()
                identity = ChannelIdentity.objects.select_related('contact').get(
                    integration=integration, external_id=remote_jid,
                )
        reply_jid = normalize_user_jid(data.get('reply_jid')) or remote_jid
        identity.profile_data = {
            **(identity.profile_data or {}),
            'jid_aliases': sorted(aliases),
            'reply_jid': reply_jid,
        }
        if name and identity.display_name != name:
            identity.display_name = name
        identity.save(update_fields=['profile_data', 'display_name', 'updated_at'])
        contact_updates = []
        if name and identity.contact.name != name:
            identity.contact.name = name
            contact_updates.append('name')
        elif not identity.contact.name:
            identity.contact.name = fallback_name
            contact_updates.append('name')
        for alias in aliases - {identity.external_id}:
            alias_identity, alias_created = ChannelIdentity.objects.get_or_create(
                integration=integration,
                external_id=alias,
                defaults={
                    'contact': identity.contact,
                    'display_name': name or fallback_name,
                    'profile_data': {'jid_aliases': sorted(aliases), 'reply_jid': reply_jid},
                },
            )
            if not alias_created and alias_identity.contact_id != identity.contact_id:
                logger.warning(
                    'Alias WhatsApp Web ya pertenece a otro contacto: integration_id=%s jid=%s.',
                    integration.pk, mask_jid(alias),
                )
        if data.get('number') and not identity.contact.phone:
            identity.contact.phone = str(data.get('number'))[:40]
            contact_updates.append('phone')
        if profile_picture_url and identity.contact.avatar_url != profile_picture_url:
            identity.contact.avatar_url = profile_picture_url
            contact_updates.append('avatar_url')
        if contact_updates:
            identity.contact.save(update_fields=[*contact_updates, 'updated_at'])

        session = ChatSession.objects.filter(
            integration=integration, contact=identity.contact,
        ).filter(Q(external_thread_id__in=aliases) | Q(external_thread_id=remote_jid)).order_by('-updated_at', '-id').first()
        if not session:
            try:
                with transaction.atomic():
                    session = ChatSession.objects.create(
                        integration=integration, contact=identity.contact, channel=ChannelIntegration.CHANNEL_WHATSAPP_WEB,
                        external_thread_id=remote_jid, user_name=name or identity.contact.name,
                        user_cedula=str(data.get('number') or '')[:50],
                        status='bot' if origin == 'customer' else 'active',
                    )
            except IntegrityError:
                session = ChatSession.objects.get(
                    integration=integration, external_thread_id=remote_jid,
                    status__in=('bot', 'waiting', 'active'),
                )
        elif session.status == 'closed' and event_source == 'notify':
            session.status = 'bot' if origin == 'customer' else 'active'
            session.save(update_fields=['status', 'updated_at'])
        current_contact_name = name or identity.contact.name or fallback_name
        if session.user_name != current_contact_name:
            session.user_name = current_contact_name
            session.save(update_fields=['user_name', 'updated_at'])
        if session.external_thread_id != remote_jid:
            active_conflict = ChatSession.objects.filter(
                integration=integration, external_thread_id=remote_jid,
            ).exclude(status='closed').exclude(pk=session.pk).exists()
            if not active_conflict:
                session.external_thread_id = remote_jid
                session.save(update_fields=['external_thread_id', 'updated_at'])
        try:
            timestamp = datetime.fromtimestamp(int(data.get('timestamp') or 0), tz=datetime_timezone.utc)
        except (ValueError, TypeError, OSError):
            timestamp = timezone.now()
        sender_type = 'user' if origin == 'customer' else 'agent'
        sender_name = name or identity.contact.name if origin == 'customer' else ('Celular' if origin == 'mobile' else 'CRM')
        try:
            with transaction.atomic():
                message = ChatMessage.objects.create(
                    session=session, text=str(data.get('text') or ''), sender_type=sender_type, sender_name=sender_name,
                    direction='inbound' if origin == 'customer' else 'outbound',
                    message_type=message_type, status='received' if origin == 'customer' else 'sent',
                    client_message_id=client_message_id or None,
                    external_message_id=key, external_timestamp=timestamp,
                    reply_to_external_id=str(data.get('quoted_message_id') or '')[:255],
                    metadata={
                        'gateway_message_id': message_id,
                        'gateway_source_jid': str(data.get('source_jid') or '')[:255],
                        'client_message_id': client_message_id,
                        'origin': origin,
                        'event_source': event_source,
                        'experimental': True,
                        **({'media_error': str(data.get('media_error'))[:200]} if data.get('media_error') else {}),
                    },
                )
        except IntegrityError:
            recovery_query = Q(external_message_id=key)
            if client_message_id:
                recovery_query |= Q(client_message_id=client_message_id)
                recovery_query |= Q(metadata__client_message_id=client_message_id)
            message = ChatMessage.objects.filter(recovery_query).order_by('id').first()
            if message is None:
                raise
            logger.info(
                'WhatsApp Web recuperó colisión idempotente: message_id=%s session_id=%s origin=%s.',
                message.pk, message.session_id, origin,
            )
            return Response({'created': False, 'message_id': message.pk})
        media_id = str((data.get('media') or {}).get('media_id') or '')
        media = cache.get(f'whatsapp-web-media:{media_id}') if media_id else None
        if media:
            attachment = ChatAttachment.objects.create(
                message=message, external_media_id=media_id, original_name=media['name'], mime_type=media['mime_type'],
                size=media['size'], metadata={'protected': True, 'gateway': True},
            )
            attachment.file.name = media['path']
            attachment.save(update_fields=['file'])
            cache.delete(f'whatsapp-web-media:{media_id}')
        if origin == 'customer':
            if not session.last_customer_message_at or timestamp > session.last_customer_message_at:
                session.last_customer_message_at = timestamp
            if event_source == 'notify':
                session.unread_by_agent += 1
            session.save(update_fields=['last_customer_message_at', 'unread_by_agent', 'updated_at'])
        else:
            if not session.last_agent_message_at or timestamp > session.last_agent_message_at:
                session.last_agent_message_at = timestamp
                session.save(update_fields=['last_agent_message_at', 'updated_at'])
        integration.last_webhook_at = timezone.now()
        integration.save(update_fields=['last_webhook_at', 'updated_at'])
        publish_crm_event('message.created', session_id=session.pk, message_id=message.pk)
        bot_allowed = (
            origin == 'customer' and event_source == 'notify' and session.status == 'bot'
            and (integration.configuration or {}).get('bot_enabled')
        )
        logger.info(
            'WhatsApp Web persistido: message_id=%s session_id=%s contact_id=%s jid=%s '
            'origin=%s source=%s bot=%s.',
            message.pk, session.pk, identity.contact_id, mask_jid(remote_jid),
            origin, event_source, 'queued' if bot_allowed else 'skipped',
        )
        if bot_allowed:
            from crmChat.tasks import generate_omnichannel_bot_reply
            generate_omnichannel_bot_reply.delay(message.pk)
        return Response({'created': True, 'message_id': message.pk}, status=201)


class GatewayStatusView(APIView):
    permission_classes = [IsCRMAdministrator]
    def get(self, request):
        integration = _integration(settings.WHATSAPP_GATEWAY_CONNECTION_ID)
        config = (integration.configuration or {}) if integration else {}
        return Response({
            'connection_id': settings.WHATSAPP_GATEWAY_CONNECTION_ID,
            'status': config.get('gateway_status', 'disconnected'),
            'phone_number': integration.display_phone_number if integration else '',
            'last_connected_at': config.get('last_connected_at', ''),
            'last_error': integration.last_error if integration else '',
            'active': bool(integration and integration.active),
            'bot_enabled': bool(config.get('bot_enabled', False)),
            'experimental': True,
        })

    def patch(self, request):
        enabled = request.data.get('bot_enabled')
        if not isinstance(enabled, bool):
            return Response({'detail': 'bot_enabled debe ser booleano.'}, status=400)
        integration = _integration(settings.WHATSAPP_GATEWAY_CONNECTION_ID, create=True)
        integration.configuration = {**(integration.configuration or {}), 'bot_enabled': enabled, 'experimental': True}
        integration.save(update_fields=['configuration', 'updated_at'])
        ChatAuditEvent.objects.create(
            actor=request.user, action='whatsapp_web.bot_enabled_changed',
            details={'connection_id': settings.WHATSAPP_GATEWAY_CONNECTION_ID, 'enabled': enabled},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response({'bot_enabled': enabled})


class GatewayRealtimeTokenView(APIView):
    permission_classes = [IsCRMAdministrator]
    def post(self, request):
        if not settings.CRM_INTERNAL_SERVICE_TOKEN:
            return Response({'detail': 'Gateway no configurado.'}, status=503)
        encoded = base64.urlsafe_b64encode(json.dumps({'role': 'admin', 'user_id': request.user.pk, 'exp': int(time.time()) + 120}, separators=(',', ':')).encode()).rstrip(b'=').decode()
        signature = base64.urlsafe_b64encode(hmac.new(settings.CRM_INTERNAL_SERVICE_TOKEN.encode(), encoded.encode(), hashlib.sha256).digest()).rstrip(b'=').decode()
        return Response({'token': f'{encoded}.{signature}', 'expires_in': 120})


class GatewayCommandView(APIView):
    permission_classes = [IsCRMAdministrator]
    def post(self, request, command):
        if command not in {'qr', 'reconnect', 'logout'}:
            return Response({'detail': 'Comando inválido.'}, status=404)
        connection_id = settings.WHATSAPP_GATEWAY_CONNECTION_ID
        path = '/internal/whatsapp/logout/' if command == 'logout' else '/internal/whatsapp/connect/'
        result = gateway_request(path, {'connection_id': connection_id, 'force_qr': command == 'qr'})
        ChatAuditEvent.objects.create(actor=request.user, action=f'whatsapp_web.{command}', details={'connection_id': connection_id}, ip_address=request.META.get('REMOTE_ADDR'))
        return Response(result, status=status.HTTP_202_ACCEPTED if command != 'logout' else status.HTTP_200_OK)


class ProtectedAttachmentView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        attachment = ChatAttachment.objects.select_related('message__session').filter(pk=pk, metadata__protected=True).first()
        if not attachment or not attachment.file:
            return Response({'detail': 'Archivo no encontrado.'}, status=404)
        session = attachment.message.session
        is_agent = getattr(request.user, 'tipo_usuario', 0) in (1, 4)
        if not is_agent and session.user_id_ref != request.user.pk:
            return Response({'detail': 'No autorizado.'}, status=403)
        return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.original_name)
