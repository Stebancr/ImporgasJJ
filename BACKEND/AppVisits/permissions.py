"""
Permisos para el módulo de Visitas Técnicas.
- Admins (tipo_usuario >= 2): acceso completo CRUD
- Técnicos (tipo_usuario == 1): solo lectura de sus propias visitas + enviar reporte
- Usuarios ecommerce (tipo_usuario == 0): sin acceso a visitas
"""
from rest_framework.permissions import BasePermission


class IsAdminOrReadOwn(BasePermission):
    """Admin: acceso total. Técnico: solo sus propias visitas."""
    message = 'No tiene permiso para acceder a este recurso.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        tipo = getattr(request.user, 'tipo_usuario', 0)
        if tipo >= 2:
            return True
        # Technician: only own visits
        from AppVisits.models import VisitaTecnica
        if isinstance(obj, VisitaTecnica):
            return obj.tecnico_id == request.user.id
        # ReporteVisita, EvidenciaFotografica
        visita = getattr(obj, 'visita', None)
        if visita:
            return visita.tecnico_id == request.user.id
        return False


class IsAdminUser(BasePermission):
    """Solo admins (tipo_usuario >= 2)."""
    message = 'Solo administradores pueden realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'tipo_usuario', 0) >= 2
