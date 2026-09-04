"""Adaptador de visitas al servicio FCM existente de ecommerce."""
import logging

from ecommerce.firebase_service import send_push_to_user
from ecommerce.models import Notification


logger = logging.getLogger(__name__)


def notify_technician_visit_assigned(visita):
    """Registra y envía la notificación cuando una visita se asigna a un técnico."""
    if not visita.tecnico_id:
        return {'sent': 0, 'failed': 0, 'deactivated': 0}

    title = 'Nueva visita técnica asignada'
    body = (
        f'Tarea {visita.numero_tarea}: {visita.cliente.nombre}, '
        f'{visita.fecha:%d/%m/%Y} a las {visita.hora:%H:%M}.'
    )
    data = {
        'type': 'visit_assigned',
        'visit_id': visita.pk,
        'task_number': visita.numero_tarea,
    }
    Notification.objects.create(
        user=visita.tecnico,
        type=Notification.Type.GENERAL,
        title=title,
        message=body,
        link=f'/admin/visitas/{visita.pk}',
    )
    try:
        return send_push_to_user(visita.tecnico, title, body, data)
    except Exception:
        # La visita queda creada/asignada aunque Firebase aún no tenga credenciales.
        logger.exception('No fue posible enviar FCM de la visita %s', visita.pk)
        return {'sent': 0, 'failed': 1, 'deactivated': 0}
