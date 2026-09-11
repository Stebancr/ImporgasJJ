from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db.models import F, Q

from .models import AssignmentQueue, ChatAuditEvent, ChatSession, ChatMessage, QueueMember
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
    return {
        'id':          m.id,
        'text':        m.text,
        'sender_type': m.sender_type,
        'sender_name': m.sender_name,
        'direction':   m.direction,
        'message_type': m.message_type,
        'status':      m.status,
        'external_message_id': m.external_message_id,
        'attachments': [
            {
                'id': attachment.id,
                'url': attachment.file.url if attachment.file else '',
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

        qs = ChatSession.objects.all()
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
            last = s.messages.last()
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

        qs = session.messages.all()
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
        message_type = request.data.get('message_type', 'text')
        payload = request.data.get('payload') or {}
        allowed_types = {'text', 'image', 'audio', 'video', 'document', 'sticker', 'template', 'interactive'}
        if message_type not in allowed_types:
            return Response({'error': 'Tipo de mensaje no permitido'}, status=400)
        if not text and message_type == 'text':
            return Response({'error': 'El texto no puede estar vacío'}, status=400)
        if not isinstance(payload, dict):
            return Response({'error': 'El payload debe ser un objeto'}, status=400)
        if message_type == 'template' and not payload.get('name'):
            return Response({'error': 'La plantilla requiere name'}, status=400)
        if message_type in {'image', 'audio', 'video', 'document', 'sticker'} and not (payload.get('id') or payload.get('url')):
            return Response({'error': 'El archivo requiere id o url'}, status=400)

        is_agent = _is_agent(request.user)
        sender_type = 'agent' if is_agent else 'user'
        sender_name, _ = _resolve_name(request.user)

        # Auto-take session when agent sends first message
        if is_agent and session.status == 'waiting':
            session.agent_id_ref = request.user.pk
            session.assigned_to = request.user
            session.agent_name = sender_name
            session.status = 'active'
            session.save()

        msg = ChatMessage.objects.create(
            session=session,
            text=text,
            sender_type=sender_type,
            sender_name=sender_name if sender_type != 'bot' else '',
            direction='outbound' if is_agent else 'inbound',
            status='queued' if is_agent else 'received',
            message_type=message_type,
            metadata={'outbound_payload': payload} if payload else {},
        )

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
                unread_by_agent=session.unread_by_agent + 1
            )

        publish_crm_event('message.created', session_id=session.id, message_id=msg.id)

        return Response(_serialize_message(msg), status=201)


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
        valid_channels = {'ecommerce', 'whatsapp', 'facebook', 'instagram'}
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
        valid_channels = {'ecommerce', 'whatsapp', 'facebook', 'instagram'}
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

        # Crear nueva sesión si no existe
        if not session:
            session = ChatSession.objects.create(
                user_id_ref=user_id_ref,
                user_name=user_name,
                user_cedula=user_cedula,
                status='bot',  # Inicialmente con bot
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

        # Obtener historial de conversación para contexto
        conversation_history = []
        previous_messages = list(
            session.messages.exclude(pk=user_message.pk).order_by('-created_at')[:8]
        )
        for msg in reversed(previous_messages):
            conversation_history.append({
                'role': 'assistant' if msg.sender_type in ('bot', 'agent') else 'user',
                'content': msg.text,
            })

        # Obtener respuesta del bot
        bot_result = ollama_service.get_bot_response(
            message_text,
            conversation_history=conversation_history,
            conversation_state=session.conversation_state,
            summary=session.conversation_summary,
        )

        bot_response_text = bot_result.get('response', 'Lo siento, no pude procesar tu mensaje.')
        needs_agent = bot_result.get('needs_agent', False)
        session.conversation_state = bot_result.get('state', session.conversation_state)
        session.conversation_summary = bot_result.get('summary', session.conversation_summary)
        session.save(update_fields=['conversation_state', 'conversation_summary', 'updated_at'])

        # Guardar respuesta del bot
        bot_message = ChatMessage.objects.create(
            session=session,
            text=bot_response_text,
            sender_type='bot',
            sender_name='',
            direction='outbound',
            status='sent',
        )

        # Si necesita agente:
        # - Usuario autenticado → marcar sesión como 'waiting' (en cola para asesor)
        # - Usuario anónimo    → NOT marcar como waiting; pedir que inicie sesión
        needs_login = False
        if needs_agent:
            is_authenticated = request.user and request.user.is_authenticated
            if is_authenticated:
                if session.status == 'bot':
                    session.status = 'waiting'
                    session.unread_by_agent = 1
                    session.save()
                    logger.info(f"Sesión {session.id} → 'waiting' (usuario autenticado)")
            else:
                # Usuario anónimo: conservar historial pero no poner en cola aún
                needs_login = True
                needs_agent = False  # No cambiar status todavía
                logger.info(f"Sesión {session.id}: necesita login para hablar con asesor")

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
