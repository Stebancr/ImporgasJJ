from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import ChatSession, ChatMessage


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
        'agent_name':      s.agent_name,
        'unread_by_agent': s.unread_by_agent,
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
            session.agent_name = agent_name
            session.status = 'active'
            session.unread_by_agent = 0
            session.save()

        elif new_status:
            allowed = ['active', 'closed'] if _is_agent(request.user) else ['closed']
            if new_status not in allowed:
                return Response({'error': 'Estado no permitido'}, status=400)
            session.status = new_status
            if new_status == 'active' and _is_agent(request.user):
                agent_name, _ = _resolve_name(request.user)
                session.agent_id_ref = request.user.pk
                session.agent_name = agent_name
                session.unread_by_agent = 0
            session.save()

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
        if not text:
            return Response({'error': 'El texto no puede estar vacío'}, status=400)

        is_agent = _is_agent(request.user)
        sender_type = 'agent' if is_agent else 'user'
        sender_name, _ = _resolve_name(request.user)

        # Auto-take session when agent sends first message
        if is_agent and session.status == 'waiting':
            session.agent_id_ref = request.user.pk
            session.agent_name = sender_name
            session.status = 'active'
            session.save()

        msg = ChatMessage.objects.create(
            session=session,
            text=text,
            sender_type=sender_type,
            sender_name=sender_name if sender_type != 'bot' else '',
        )

        # Increment unread counter for agent when user sends
        if not is_agent:
            ChatSession.objects.filter(pk=session.pk).update(
                unread_by_agent=session.unread_by_agent + 1
            )

        return Response(_serialize_message(msg), status=201)
