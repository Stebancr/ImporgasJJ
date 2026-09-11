import hashlib
import json


def visit_sync_version(visit):
    """Opaque optimistic version covering schedule, assignment, client and report."""
    report = getattr(visit, 'reporte', None)
    payload = {
        'visit': {key: getattr(visit, key) for key in ('id', 'tecnico_id', 'tipo_tarea', 'fecha', 'hora', 'descripcion', 'observaciones_iniciales', 'valor_visita', 'estado', 'fecha_actualizacion')},
        'client': {key: getattr(visit.cliente, key) for key in ('id', 'nombre', 'identificacion', 'telefono', 'correo', 'direccion')},
        'report': report.actualizado_en if report else None,
        'photos': list(visit.evidencias.values_list('id', flat=True)),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def serialize_visit_mutation(method):
    """Legacy writes take the same row lock as atomic offline completion."""
    from functools import wraps
    from django.db import transaction
    from .models import VisitaTecnica

    @wraps(method)
    def wrapped(self, request, pk, *args, **kwargs):
        with transaction.atomic():
            VisitaTecnica.objects.select_for_update().filter(pk=pk).first()
            return method(self, request, pk, *args, **kwargs)
    return wrapped
