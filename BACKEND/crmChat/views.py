from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.conf import settings
from django.core import signing
from django.db import IntegrityError
from django.http import FileResponse
from django.utils import timezone
from pathlib import Path
from urllib.parse import urlencode
import uuid

from .models import AssignmentQueue, ChannelIntegration, ChatAttachment, ChatAuditEvent, CRMContact, ChatSession, ChatMessage, QueueMember
from .attachment_validation import validate_chat_upload
from .ollama_service import ollama_service
from .apps.meta.services import MetaAPIError, dispatch_outbound_message
from .realtime import publish_crm_event
import logging

logger = logging.getLogger(__name__)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _is_agent(user):
    return getattr(user, 'tipo_usuario', 0) in [1, 4]


def _resolve_name(user):
    """Return a display name for the authenticated user."""
    try:
        rel = getattr(user, 'usuario_rel', None)
        if rel and rel.nombre_completo:
            return rel.nombre_completo, getattr(rel, 'cedula', '')
    except Exception:
        pass
    return getattr(user, 'usuario', 'Usuario'), ''


def _serialize_session(s, last_msg=None):
    return {
        'id':              s.id,
        'user_name':       s.user_name,
        'user_cedula':     s.user_cedula,
        'status':          s.status,
        'channel':         s.channel,
        'priority':        s.priority,
        'queue_id':        s.queue_id,
        'contact_id':      s.contact_id,
        'avatar_url':      s.contact.avatar_url if s.contact_id else '',
        'external_thread_id': s.external_thread_id,
        'agent_name':      s.agent_name,
        'unread_by_agent': s.unread_by_agent,
        'conversation_state': s.conversation_state,
        'conversation_summary': s.conversation_summary,
        'created_at':      s.created_at,
        'updated_at':      s.updated_at,
        'last_message':    last_msg,
    }


def _serialize_message(m):
    metadata = m.metadata or {}
    origin = metadata.get('origin')
    if not origin:
        origin = 'bot' if m.sender_type == 'bot' else ('customer' if m.direction == 'inbound' else 'crm')
    return {
        'id':          m.id,
        'text':        m.text,
        'sender_type': m.sender_type,
        'sender_name': m.sender_name,
        'direction':   m.direction,
        'message_type': m.message_type,
        'status':      m.status,
        'error':       str(metadata.get('error') or '')[:500],
        'external_message_id': m.external_message_id,
        'client_message_id': m.client_message_id,
        'origin': origin,
        'external_timestamp': m.external_timestamp,
        'timestamp': m.external_timestamp or m.created_at,
        'attachments': [
            {
                'id': attachment.id,
                'url': f'/api/crm-chat/attachments/{attachment.id}/' if attachment.file else '',
                'name': attachment.original_name,
                'mime_type': attachment.mime_type,
                'size': attachment.size,
            }
            for attachment in m.attachments.all()
        ],
        'created_at':  m.created_at,
    }


# ─── Views ────────────────────────────────────────────────────────────────────

class SessionListCreateView(APIView):
    """
    GET  — agent/admin: list sessions (filterable by ?status=)
    POST — authenticated user: create a new chat session
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)

        qs = ChatSession.objects.select_related('contact').all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        channel_filter = request.query_params.get('channel')
        if channel_filter:
            qs = qs.filter(channel=channel_filter)
        priority_filter = request.query_params.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
        search = (request.query_params.get('search') or '').strip()
        if search:
            qs = qs.filter(Q(user_name__icontains=search) | Q(user_cedula__icontains=search))
        if request.query_params.get('unanswered') == 'true':
            qs = qs.filter(last_customer_message_at__isnull=False).filter(
                Q(last_agent_message_at__isnull=True) | Q(last_agent_message_at__lt=F('last_customer_message_at'))
            )

        result = []
        for s in qs.order_by('-updated_at')[:100]:
            last = s.messages.annotate(
                activity_at=Coalesce('external_timestamp', 'created_at'),
            ).order_by('-activity_at', '-id').first()
            result.append(_serialize_session(s, last.text if last else None))
        return Response(result)

    def post(self, request):
        user = request.user
        user_name, user_cedula = _resolve_name(user)

        session = ChatSession.objects.create(
            user_id_ref=user.pk,
            user_name=user_name,
            user_cedula=user_cedula,
            status='waiting',
        )

        # Persist initial messages (conversation history with bot)
        initial = request.data.get('initial_messages', [])
        for msg in initial:
            text = (msg.get('text') or '').strip()
            if not text:
                continue
            sender = 'bot' if msg.get('is_bot') else 'user'
            ChatMessage.objects.create(
                session=session,
                text=text,
                sender_type=sender,
                sender_name='' if sender == 'bot' else user_name,
            )

        return Response(_serialize_session(session), status=201)


class PendingCountView(APIView):
    """GET — agent/admin: number of sessions waiting for an agent (for badge)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)
        count = ChatSession.objects.filter(status='waiting').count()
        return Response({'count': count})


class ContactListView(APIView):
    """Contactos consultables por CRM web o móvil autenticado como agente."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)
        contacts = CRMContact.objects.all()
        search = (request.query_params.get('search') or '').strip()
        if search:
            contacts = contacts.filter(
                Q(name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search)
            )
        return Response([
            {
                'id': contact.id,
                'name': contact.name,
                'phone': contact.phone,
                'email': contact.email,
                'avatar_url': contact.avatar_url,
                'last_interaction_at': contact.last_interaction_at,
                'updated_at': contact.updated_at,
            }
            for contact in contacts.order_by('-last_interaction_at', 'name', 'id')[:100]
        ])


class SessionDetailView(APIView):
    """
    GET   — session owner or agent: full session info
    PATCH — session owner (close only) or agent (take / close)
    """
    permission_classes = [IsAuthenticated]

    def _get_session(self, pk, user):
        try:
            s = ChatSession.objects.get(pk=pk)
        except ChatSession.DoesNotExist:
            return None, Response({'error': 'Sesión no encontrada'}, status=404)

        if not _is_agent(user) and s.user_id_ref != user.pk:
            return None, Response({'error': 'No autorizado'}, status=403)
        return s, None

    def get(self, request, pk):
        session, err = self._get_session(pk, request.user)
        if err:
            return err
        return Response(_serialize_session(session))

    def patch(self, request, pk):
        session, err = self._get_session(pk, request.user)
        if err:
            return err

        new_status = request.data.get('status')
        take = request.data.get('take')  # agent takes the session

        if take and _is_agent(request.user):
            agent_name, _ = _resolve_name(request.user)
            session.agent_id_ref = request.user.pk
            session.assigned_to = request.user
            session.agent_name = agent_name
            session.status = 'active'
            session.unread_by_agent = 0
            session.save()

        assign_to_id = request.data.get('assign_to_id')
        if assign_to_id is not None and _is_agent(request.user):
            from django.contrib.auth import get_user_model
            try:
                advisor = get_user_model().objects.get(pk=assign_to_id, tipo_usuario__in=(1, 4), estado=1)
            except get_user_model().DoesNotExist:
                return Response({'error': 'Asesor no válido'}, status=400)
            session.assigned_to = advisor
            session.agent_id_ref = advisor.pk
            session.agent_name = _resolve_name(advisor)[0]
            session.status = 'active'
            session.save()
            ChatAuditEvent.objects.create(actor=request.user, session=session, action='conversation.assigned', details={'advisor_id': advisor.pk})

        queue_id = request.data.get('queue_id')
        if queue_id is not None and _is_agent(request.user):
            try:
                session.queue = AssignmentQueue.objects.get(pk=queue_id, active=True)
            except AssignmentQueue.DoesNotExist:
                return Response({'error': 'Cola no válida'}, status=400)
            session.save(update_fields=['queue', 'updated_at'])

        elif new_status:
            allowed = ['active', 'closed'] if _is_agent(request.user) else ['closed']
            if new_status not in allowed:
                return Response({'error': 'Estado no permitido'}, status=400)
            session.status = new_status
            if new_status == 'active' and _is_agent(request.user):
                agent_name, _ = _resolve_name(request.user)
                session.agent_id_ref = request.user.pk
                session.assigned_to = request.user
                session.agent_name = agent_name
                session.unread_by_agent = 0
            session.save()

        priority = request.data.get('priority')
        if priority is not None and _is_agent(request.user):
            if priority not in {'low', 'normal', 'high', 'urgent'}:
                return Response({'error': 'Prioridad no permitida'}, status=400)
            session.priority = priority
            session.save(update_fields=['priority', 'updated_at'])

        return Response(_serialize_session(session))


class MessageListCreateView(APIView):
    """
    GET  — owner or agent: fetch messages, optionally ?after=<id> for polling
    POST — owner (user msg) or agent (agent msg)
    """
    permission_classes = [IsAuthenticated]

    def _get_session(self, pk, user):
        try:
            s = ChatSession.objects.get(pk=pk)
        except ChatSession.DoesNotExist:
            return None, Response({'error': 'Sesión no encontrada'}, status=404)
        if not _is_agent(user) and s.user_id_ref != user.pk:
            return None, Response({'error': 'No autorizado'}, status=403)
        return s, None

    def get(self, request, pk):
        session, err = self._get_session(pk, request.user)
        if err:
            return err

        qs = session.messages.annotate(
            activity_at=Coalesce('external_timestamp', 'created_at'),
        ).order_by('activity_at', 'id')
        after = request.query_params.get('after')
        if after:
            try:
                qs = qs.filter(id__gt=int(after))
            except ValueError:
                pass

        # Mark session as read by agent
        if _is_agent(request.user) and session.unread_by_agent:
            session.unread_by_agent = 0
            session.save(update_fields=['unread_by_agent'])

        return Response({
            'messages': [_serialize_message(m) for m in qs],
            'status':   session.status,
            'agent_name': session.agent_name,
        })

    def post(self, request, pk):
        session, err = self._get_session(pk, request.user)
        if err:
            return err

        if session.status == 'closed':
            return Response({'error': 'La sesión está cerrada'}, status=400)

        text = (request.data.get('text') or '').strip()
        upload = request.FILES.get('file')
        message_type = request.data.get('message_type', 'text')
        payload = request.data.get('payload') or {}
        client_message_id = (request.data.get('client_message_id') or '').strip()
        allowed_types = {'text', 'image', 'audio', 'video', 'document', 'sticker', 'interactive'}
        if message_type not in allowed_types:
            return Response({'error': 'Tipo de mensaje no permitido'}, status=400)
        if not text and not upload:
            return Response({'error': 'El mensaje requiere texto o un archivo'}, status=400)
        if not isinstance(payload, dict):
            return Response({'error': 'El payload debe ser un objeto'}, status=400)
        if message_type in {'image', 'audio', 'video', 'document', 'sticker'} and not upload and not (payload.get('id') or payload.get('url')):
            return Response({'error': 'El archivo requiere id o url'}, status=400)

        is_agent = _is_agent(request.user)
        origin = (request.data.get('origin') or ('crm' if is_agent else 'customer')).strip().lower()
        if origin == 'mobile' and not is_agent:
            return Response({'error': 'Solo un agente puede enviar con origen mobile'}, status=403)
        if origin not in ({'crm', 'mobile'} if is_agent else {'customer'}):
            return Response({'error': 'Origen de mensaje no permitido'}, status=400)
        if client_message_id:
            try:
                client_message_id = str(uuid.UUID(client_message_id))
            except ValueError:
                return Response({'error': 'client_message_id debe ser un UUID válido'}, status=400)
            existing = ChatMessage.objects.filter(client_message_id=client_message_id).first()
            if existing:
                if existing.session_id != session.id:
                    return Response({'error': 'client_message_id ya pertenece a otra conversación'}, status=409)
                return Response(_serialize_message(existing), status=200)

        attachment_data = None
        if upload:
            if not is_agent:
                return Response({'error': 'La carga de archivos está disponible para agentes autenticados'}, status=403)
            try:
                attachment_data = validate_chat_upload(upload)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=400)
            message_type = attachment_data[2]

        sender_type = 'agent' if is_agent else 'user'
        sender_name, _ = _resolve_name(request.user)

        # Auto-take session when agent sends first message
        if is_agent and session.status == 'waiting':
            session.agent_id_ref = request.user.pk
            session.assigned_to = request.user
            session.agent_name = sender_name
            session.status = 'active'
            session.save()

        try:
            with transaction.atomic():
                msg = ChatMessage.objects.create(
                    session=session,
                    text=text,
                    sender_type=sender_type,
                    sender_name=sender_name if sender_type != 'bot' else '',
                    direction='outbound' if is_agent else 'inbound',
                    status='queued' if is_agent else 'received',
                    message_type=message_type,
                    client_message_id=client_message_id or None,
                    metadata={
                        'origin': origin,
                        **({'outbound_payload': payload} if payload else {}),
                    },
                )
                if upload and attachment_data:
                    original_name, mime_type, _ = attachment_data
                    attachment = ChatAttachment.objects.create(
                        message=msg,
                        file=upload,
                        original_name=original_name,
                        mime_type=mime_type,
                        size=upload.size,
                        metadata={'protected': True, 'uploaded_by': origin},
                    )
                    token = signing.dumps(attachment.id, salt='crm-chat-delivery')
                    public_base = settings.FRONTEND_PUBLIC_URL.rstrip('/')
                    delivery_url = (
                        f'{public_base}/api/crm-chat/attachments/{attachment.id}/delivery/'
                        f'?{urlencode({"token": token})}'
                    )
                    msg.metadata = {
                        **msg.metadata,
                        'outbound_payload': {
                            'url': delivery_url,
                            'filename': original_name,
                            'mime_type': mime_type,
                        },
                    }
                    msg.save(update_fields=['metadata'])
        except IntegrityError:
            if client_message_id:
                existing = ChatMessage.objects.filter(client_message_id=client_message_id, session=session).first()
                if existing:
                    return Response(_serialize_message(existing), status=200)
            raise

        if is_agent:
            try:
                dispatch_outbound_message(msg)
            except MetaAPIError as exc:
                return Response(
                    {'error': str(exc), 'message': _serialize_message(msg)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            session.last_agent_message_at = msg.created_at
            session.save(update_fields=['last_agent_message_at', 'updated_at'])

        # Increment unread counter for agent when user sends
        if not is_agent:
            ChatSession.objects.filter(pk=session.pk).update(
                unread_by_agent=F('unread_by_agent') + 1,
                updated_at=timezone.now(),
            )
        else:
            ChatSession.objects.filter(pk=session.pk).update(updated_at=timezone.now())

        publish_crm_event('message.created', session_id=session.id, message_id=msg.id)

        return Response(_serialize_message(msg), status=201)


class ProtectedAttachmentView(APIView):
    """Entrega archivos del chat únicamente al dueño o a un agente autorizado."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        attachment = ChatAttachment.objects.select_related('message__session').filter(pk=pk).first()
        if not attachment or not attachment.file:
            return Response({'error': 'Archivo no encontrado'}, status=404)
        session = attachment.message.session
        if not _is_agent(request.user) and session.user_id_ref != request.user.pk:
            return Response({'error': 'No autorizado'}, status=403)
        inline = attachment.mime_type.startswith('image/')
        response = FileResponse(
            attachment.file.open('rb'),
            as_attachment=not inline,
            filename=Path(attachment.original_name).name or f'adjunto-{attachment.id}',
            content_type=attachment.mime_type or 'application/octet-stream',
        )
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class AttachmentDeliveryView(APIView):
    """URL firmada y breve para que Meta o el gateway descarguen un envío."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        token = request.query_params.get('token', '')
        try:
            signed_id = signing.loads(
                token,
                salt='crm-chat-delivery',
                max_age=getattr(settings, 'CRM_ATTACHMENT_DELIVERY_TTL', 300),
            )
        except signing.BadSignature:
            return Response({'error': 'Enlace vencido o inválido'}, status=403)
        if signed_id != pk:
            return Response({'error': 'Enlace inválido'}, status=403)
        attachment = ChatAttachment.objects.filter(pk=pk).first()
        if not attachment or not attachment.file:
            return Response({'error': 'Archivo no encontrado'}, status=404)
        response = FileResponse(
            attachment.file.open('rb'),
            as_attachment=False,
            filename=Path(attachment.original_name).name or f'adjunto-{attachment.id}',
            content_type=attachment.mime_type or 'application/octet-stream',
        )
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, max-age=60'
        return response


class AssignmentQueueListCreateView(APIView):
    """Lista colas y permite a administradores crear su distribución."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)
        return Response([self._serialize(queue) for queue in AssignmentQueue.objects.prefetch_related('memberships')])

    def post(self, request):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)
        name = (request.data.get('name') or '').strip()
        channels = request.data.get('channels') or []
        if not name or not isinstance(channels, list):
            return Response({'error': 'Nombre y channels son obligatorios'}, status=400)
        valid_channels = {'ecommerce', 'whatsapp', 'whatsapp_web', 'facebook', 'instagram'}
        if any(channel not in valid_channels for channel in channels):
            return Response({'error': 'Canal no permitido'}, status=400)
        queue = AssignmentQueue.objects.create(
            name=name,
            channels=channels,
            auto_assign=bool(request.data.get('auto_assign', False)),
        )
        self._replace_members(queue, request.data.get('members', []))
        return Response(self._serialize(queue), status=201)

    @staticmethod
    def _replace_members(queue, members):
        from django.contrib.auth import get_user_model
        for item in members if isinstance(members, list) else []:
            user_id = item.get('user_id') if isinstance(item, dict) else item
            user = get_user_model().objects.filter(pk=user_id, tipo_usuario__in=(1, 4), estado=1).first()
            if user:
                QueueMember.objects.update_or_create(
                    queue=queue,
                    user=user,
                    defaults={'capacity': max(1, int(item.get('capacity', 10))) if isinstance(item, dict) else 10, 'active': True},
                )

    @staticmethod
    def _serialize(queue):
        return {
            'id': queue.id, 'name': queue.name, 'active': queue.active,
            'auto_assign': queue.auto_assign, 'channels': queue.channels,
            'members': [
                {'user_id': member.user_id, 'capacity': member.capacity, 'active': member.active}
                for member in queue.memberships.all()
            ],
        }


class AssignmentQueueDetailView(AssignmentQueueListCreateView):
    """Actualiza o desactiva una cola sin borrar conversaciones asociadas."""

    def patch(self, request, pk):
        if not _is_agent(request.user):
            return Response({'error': 'No autorizado'}, status=403)
        try:
            queue = AssignmentQueue.objects.get(pk=pk)
        except AssignmentQueue.DoesNotExist:
            return Response({'error': 'Cola no encontrada'}, status=404)
        valid_channels = {'ecommerce', 'whatsapp', 'whatsapp_web', 'facebook', 'instagram'}
        if 'name' in request.data and not str(request.data['name']).strip():
            return Response({'error': 'El nombre no puede estar vacío'}, status=400)
        if 'channels' in request.data:
            channels = request.data['channels']
            if not isinstance(channels, list) or any(channel not in valid_channels for channel in channels):
                return Response({'error': 'Lista de canales no válida'}, status=400)
        for field in ('name', 'channels', 'auto_assign', 'active'):
            if field in request.data:
                value = str(request.data[field]).strip() if field == 'name' else request.data[field]
                setattr(queue, field, value)
        queue.save()
        if 'members' in request.data:
            queue.memberships.update(active=False)
            self._replace_members(queue, request.data['members'])
        return Response(self._serialize(queue))


class BotChatView(APIView):
    """
    POST — Endpoint público para chatear con el bot (sin autenticación requerida)
    Permite a usuarios del ecommerce chatear con el bot Ollama.
    Si el bot detecta intención de compra/servicio, deriva a un agente humano.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'chat'

    def post(self, request):
        """
        Procesa un mensaje del usuario y retorna la respuesta del bot.
        
        Body:
        {
            "message": "texto del mensaje",
            "session_id": null|int (opcional, para continuar conversación),
            "user_name": "Nombre" (opcional, para usuarios no autenticados),
            "user_email": "email@example.com" (opcional)
        }
        
        Response:
        {
            "session_id": int,
            "message": "respuesta del bot",
            "sender_type": "bot",
            "status": "bot|waiting|active",
            "needs_agent": bool
        }
        """
        message_text = (request.data.get('message') or '').strip()
        if not message_text:
            return Response(
                {'error': 'El mensaje no puede estar vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(message_text) > 2000:
            return Response(
                {'error': 'El mensaje no puede superar 2000 caracteres'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.data.get('session_id')
        user_name = request.data.get('user_name', 'Usuario')
        user_email = request.data.get('user_email', '')

        # Si el usuario está autenticado, usar sus datos
        if request.user and request.user.is_authenticated:
            user_name, user_cedula = _resolve_name(request.user)
            user_id_ref = request.user.pk
        else:
            user_cedula = user_email
            user_id_ref = None

        # Obtener o crear sesión
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(pk=session_id)
                # Verificar que la sesión pertenezca al usuario (si está autenticado)
                if user_id_ref and session.user_id_ref and session.user_id_ref != user_id_ref:
                    return Response(
                        {'error': 'Sesión no válida'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except ChatSession.DoesNotExist:
                session = None

        # Una sesión cerrada es histórica e inmutable para efectos de contexto.
        # Si el cliente vuelve a escribir, se crea una conversación independiente.
        create_new_session = session is None or session.status == 'closed'
        if create_new_session:
            previous_session = session
            ecommerce_integration = (
                previous_session.integration
                if previous_session and previous_session.integration_id
                else ChannelIntegration.objects.filter(
                    channel=ChannelIntegration.CHANNEL_ECOMMERCE, active=True,
                ).first()
            )
            session = ChatSession.objects.create(
                user_id_ref=user_id_ref,
                user_name=(
                    user_name if user_name != 'Usuario'
                    else getattr(previous_session, 'user_name', user_name)
                ),
                user_cedula=user_cedula or getattr(previous_session, 'user_cedula', ''),
                status='bot',  # Inicialmente con bot
                channel=ChannelIntegration.CHANNEL_ECOMMERCE,
                integration=ecommerce_integration,
                contact=getattr(previous_session, 'contact', None),
            )
            logger.info(f"Nueva sesión de chat creada: {session.id} para {user_name}")

        # Guardar mensaje del usuario
        user_message = ChatMessage.objects.create(
            session=session,
            text=message_text,
            sender_type='user',
            sender_name=user_name,
            direction='inbound',
            status='received',
        )
        session.refresh_from_db()
        session.last_customer_message_at = user_message.created_at
        session.inactivity_warning_at = None
        session.save(update_fields=['last_customer_message_at', 'inactivity_warning_at', 'updated_at'])

        # Cuando un asesor ya tomó la conversación, el mensaje queda en el CRM
        # y Ollama no interviene. También admite apagar el bot del ecommerce.
        ecommerce_bot_enabled = getattr(settings, 'OLLAMA_ECOMMERCE_ENABLED', True)
        if session.integration_id:
            ecommerce_bot_enabled = bool(session.integration.configuration.get('bot_enabled', False))
        if session.status != 'bot' or not ecommerce_bot_enabled:
            return Response({
                'session_id': session.id, 'message': '', 'sender_type': 'bot',
                'status': session.status, 'needs_agent': session.status == 'waiting',
                'needs_login': False, 'user_message_id': user_message.id,
                'bot_message_id': None, 'conversation_state': session.conversation_state,
            }, status=status.HTTP_202_ACCEPTED)

        # Obtener historial de conversación para contexto
        conversation_history = []
        previous_messages = list(
            session.messages.exclude(pk=user_message.pk).order_by('-created_at')[:12]
        )
        for msg in reversed(previous_messages):
            conversation_history.append({
                'role': 'assistant' if msg.sender_type in ('bot', 'agent') else 'user',
                'content': msg.text,
            })

        # Obtener respuesta del bot
        try:
            conversation_state = dict(session.conversation_state or {})
            conversation_state['greeting_shown'] = True
            bot_result = ollama_service.get_bot_response(
                message_text, conversation_history=conversation_history,
                conversation_state=conversation_state,
                summary=session.conversation_summary,
                channel=ChannelIntegration.CHANNEL_ECOMMERCE,
            )
        except Exception:
            logger.exception('Fallo de Ollama para sesión ecommerce %s, mensaje %s.', session.id, user_message.id)
            return Response({'error': 'No fue posible procesar el mensaje en este momento.', 'session_id': session.id}, status=503)

        bot_response_text = bot_result.get('response', 'Lo siento, no pude procesar tu mensaje.')
        next_state = bot_result.get('state', session.conversation_state)
        next_state['last_response'] = bot_response_text[:2000]
        needs_agent = bot_result.get('needs_agent', False)
        with transaction.atomic():
            session = ChatSession.objects.select_for_update().get(pk=session.pk)
            if session.status != 'bot':
                return Response({
                    'session_id': session.id, 'message': '', 'sender_type': 'bot',
                    'status': session.status, 'needs_agent': session.status == 'waiting',
                    'needs_login': False, 'user_message_id': user_message.id,
                    'bot_message_id': None, 'conversation_state': session.conversation_state,
                }, status=status.HTTP_202_ACCEPTED)
            session.conversation_state = next_state
            session.conversation_summary = bot_result.get('summary', session.conversation_summary)
            if needs_agent:
                session.status = 'waiting'
                session.unread_by_agent += 1
            session.save(update_fields=[
                'conversation_state', 'conversation_summary', 'status', 'unread_by_agent', 'updated_at',
            ])
            bot_message = ChatMessage.objects.create(
                session=session, reply_to_message=user_message, text=bot_response_text,
                sender_type='bot', sender_name='', direction='outbound', status='sent',
            )
            session.last_bot_message_at = bot_message.created_at
            session.inactivity_warning_at = None
            session.save(update_fields=['last_bot_message_at', 'inactivity_warning_at', 'updated_at'])
            if needs_agent:
                publish_crm_event('session.pending', session_id=session.id, message_id=user_message.id)
        if needs_agent and session.status == 'waiting' and session.assigned_to_id is None:
            from .assignment import assign_session_automatically
            assign_session_automatically(session)
            session.refresh_from_db()
        needs_login = False

        return Response({
            'session_id': session.id,
            'message': bot_response_text,
            'sender_type': 'bot',
            'status': session.status,
            'needs_agent': needs_agent,
            'needs_login': needs_login,   # Frontend muestra botón de login
            'user_message_id': user_message.id,
            'bot_message_id': bot_message.id,
            'conversation_state': session.conversation_state,
        })


class BotSessionMessagesView(APIView):
    """
    GET — Obtener todos los mensajes de una sesión de bot (público)
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        """
        Obtiene todos los mensajes de una sesión.
        
        Query params:
        - after: id del último mensaje recibido (para polling)
        """
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Sesión no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        qs = session.messages.all()
        after = request.query_params.get('after')
        if after:
            try:
                qs = qs.filter(id__gt=int(after))
            except ValueError:
                pass

        messages = [_serialize_message(m) for m in qs]

        return Response({
            'session_id': session.id,
            'status': session.status,
            'messages': messages,
            'agent_name': session.agent_name if session.status in ['active', 'closed'] else None,
        })
