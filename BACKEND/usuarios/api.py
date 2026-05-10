from rest_framework import viewsets, permissions
from .models import Colaboradores
from .serializers import usuarioSerialaizer


class UsuariosViewSet(viewsets.ModelViewSet):
    queryset = Colaboradores.objects.all()
    serializer_class = usuarioSerialaizer
    permission_classes = [permissions.AllowAny]
