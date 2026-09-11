"""Endpoints de configuración y recepción de Meta."""

import logging

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crmChat.models import ChannelIntegration, ChatAuditEvent

from .serializers import ChannelIntegrationSerializer
from .services import MetaAPIError, accept_webhook, validate_integration_connection, verify_webhook_token
from crmChat.tasks import process_meta_webhook_task

logger = logging.getLogger(__name__)


class IsCRMAdministrator(IsAuthenticated):
    """Restringe configuraciones sensibles a administradores y superadmins."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and getattr(request.user, 'tipo_usuario', 0) in (1, 4)


class IntegrationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsCRMAdministrator]
    serializer_class = ChannelIntegrationSerializer
    queryset = ChannelIntegration.objects.all()


class IntegrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsCRMAdministrator]
    serializer_class = ChannelIntegrationSerializer
    queryset = ChannelIntegration.objects.all()

    def perform_destroy(self, instance):
        """Desactivar conserva conversaciones, identidades y auditoría."""

        instance.active = False
        instance.save(update_fields=['active', 'updated_at'])
        ChatAuditEvent.objects.create(
            actor=self.request.user,
            action='integration.disabled',
            details={'integration_id': instance.id, 'channel': instance.channel},
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class MetaWebhookView(APIView):
    """Webhook unificado; acepta un canal forzado solo en los alias tipados."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'meta_webhook'
    forced_channel = ''

    def get(self, request):
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token', '')
        challenge = request.query_params.get('hub.challenge', '')
        if mode == 'subscribe' and verify_webhook_token(token):
            return HttpResponse(challenge, content_type='text/plain', status=200)
        return Response({'detail': 'Verificación rechazada.'}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        try:
            event, created = accept_webhook(
                request.body,
                request.headers.get('X-Hub-Signature-256', ''),
                self.forced_channel,
            )
            if created or event.status == 'failed':
                process_meta_webhook_task.delay(event.id)
            return Response({'received': True}, status=status.HTTP_200_OK)
        except PermissionError:
            return Response({'detail': 'Firma inválida.'}, status=status.HTTP_401_UNAUTHORIZED)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('Falló el procesamiento del webhook Meta.')
            # Un 500 permite que Meta reintente un evento no procesado.
            return Response({'detail': 'No fue posible procesar el evento.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IntegrationValidateView(APIView):
    """Valida una credencial contra Meta sin exponer el token."""

    permission_classes = [IsCRMAdministrator]
    throttle_scope = 'meta_admin'

    def post(self, request, pk):
        try:
            integration = ChannelIntegration.objects.get(pk=pk)
            return Response(validate_integration_connection(integration))
        except ChannelIntegration.DoesNotExist:
            return Response({'detail': 'Integración no encontrada.'}, status=404)
        except MetaAPIError as exc:
            return Response({'valid': False, 'detail': str(exc)}, status=400)
