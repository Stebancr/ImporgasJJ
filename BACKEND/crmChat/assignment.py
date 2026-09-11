"""Reglas de asignación de conversaciones a colas y asesores."""

from django.db.models import Count, Q

from .models import AssignmentQueue, ChatSession, QueueMember


def _display_name(user):
    profile = getattr(user, 'usuario_rel', None)
    return getattr(profile, 'nombre_completo', '') or getattr(user, 'usuario', 'Asesor')


def assign_session_automatically(session):
    """Asigna al asesor activo con menor carga sin superar su capacidad."""

    queues = AssignmentQueue.objects.filter(active=True, auto_assign=True).prefetch_related('memberships__user')
    queue = next((item for item in queues if not item.channels or session.channel in item.channels), None)
    if not queue:
        return session
    members = QueueMember.objects.filter(queue=queue, active=True, user__tipo_usuario__in=(1, 4)).select_related('user')
    loads = {
        row['assigned_to_id']: row['total']
        for row in ChatSession.objects.filter(status__in=('waiting', 'active'), assigned_to__isnull=False)
        .values('assigned_to_id').annotate(total=Count('id'))
    }
    candidates = [member for member in members if loads.get(member.user_id, 0) < member.capacity]
    session.queue = queue
    if candidates:
        selected = min(candidates, key=lambda member: (loads.get(member.user_id, 0), member.user_id))
        session.assigned_to = selected.user
        session.agent_id_ref = selected.user_id
        session.agent_name = _display_name(selected.user)
        session.status = 'active'
    elif session.status == 'bot':
        session.status = 'waiting'
    session.save()
    return session
