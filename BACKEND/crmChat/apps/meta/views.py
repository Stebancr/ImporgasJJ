"""Endpoints de configuración y recepción de Meta."""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crmChat.models import ChannelIntegration, ChatAuditEvent, MetaConnection

from .oauth import (
    build_authorization_url,
    consume_oauth_state,
    disconnect_connection,
    exchange_code_for_token,
    persist_oauth_inventory,
    select_accounts,
    validate_access_token,
)
from .serializers import (
    ChannelIntegrationSerializer,
    MetaAccountSelectionSerializer,
    MetaConnectionSerializer,
)
from .services import (
    MetaAPIError,
    SecretConfigurationError,
    accept_webhook,
    validate_integration_connection,
    verify_webhook_token,
)
from crmChat.tasks import process_meta_webhook_task

logger = logging.getLogger(__name__)


class IsCRMAdministrator(IsAuthenticated):
    """Restringe configuraciones sensibles a administradores y superadmins."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and getattr(request.user, 'tipo_usuario', 0) in (1, 4)


class IntegrationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsCRMAdministrator]
    serializer_class = ChannelIntegrationSerializer

    def get_queryset(self):
        # El serializer informa el estado de credenciales sin N+1 queries.
        return ChannelIntegration.objects.select_related(
            'meta_connection',
            'meta_facebook_page__connection',
        )


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
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        try:
            event, created = accept_webhook(
                request.body,
                signature_header,
                self.forced_channel,
            )
            if created or event.status == 'failed':
                process_meta_webhook_task.delay(event.id)
            return Response({'received': True}, status=status.HTTP_200_OK)
        except PermissionError:
            logger.warning(
                'Webhook Meta rechazado por firma inválida (canal=%s, header_presente=%s, formato_sha256=%s).',
                self.forced_channel or 'auto',
                bool(signature_header),
                signature_header.startswith('sha256='),
            )
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


class MetaConnectView(APIView):
    """Inicia Facebook Login para Pages e Instagram; no solicita WhatsApp."""

    permission_classes = [IsCRMAdministrator]
    throttle_scope = 'meta_admin'

    def get(self, request):
        try:
            authorization_url = build_authorization_url(request.user.pk)
            ChatAuditEvent.objects.create(
                actor=request.user,
                action='meta.oauth_started',
                details={'provider': 'facebook_instagram'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return Response({'authorization_url': authorization_url})
        except SecretConfigurationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class MetaOAuthCallbackView(APIView):
    """Callback público: consume state, valida token y descubre activos."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'meta_admin'

    @staticmethod
    def _redirect(result, connection_id=''):
        target = getattr(settings, 'META_OAUTH_FRONTEND_REDIRECT', '/admin/chat/integraciones')
        query = urlencode({'meta_oauth': result, 'connection_id': connection_id})
        separator = '&' if '?' in target else '?'
        return HttpResponseRedirect(f'{target}{separator}{query}')

    def get(self, request):
        if request.query_params.get('error'):
            return self._redirect('denied')
        try:
            state_payload = consume_oauth_state(request.query_params.get('state', ''))
            token = exchange_code_for_token(request.query_params.get('code', ''))
            token_info = validate_access_token(token)
            connection = persist_oauth_inventory(state_payload['user_id'], token, token_info)
            ChatAuditEvent.objects.create(
                actor_id=state_payload['user_id'],
                action='meta.oauth_completed',
                details={'connection_id': connection.pk, 'available_pages': connection.facebook_pages.count()},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return self._redirect('select', connection.pk)
        except (signing.BadSignature, signing.SignatureExpired, KeyError):
            logger.warning('OAuth Meta rechazado: state inválido, expirado o ya utilizado.')
            return self._redirect('invalid_state')
        except (MetaAPIError, SecretConfigurationError, ValueError) as exc:
            logger.warning('No se completó OAuth Meta: %s', exc)
            return self._redirect('error')
        except Exception:
            logger.exception('Error inesperado durante OAuth Meta.')
            return self._redirect('error')


class MetaConnectionListView(generics.ListAPIView):
    permission_classes = [IsCRMAdministrator]
    serializer_class = MetaConnectionSerializer
    throttle_scope = 'meta_admin'

    def get_queryset(self):
        return MetaConnection.objects.filter(created_by=self.request.user).prefetch_related(
            'facebook_pages__instagram_account',
        )


class MetaConnectionAccountsView(APIView):
    permission_classes = [IsCRMAdministrator]
    throttle_scope = 'meta_admin'

    def _connection(self, request, pk):
        return get_object_or_404(
            MetaConnection.objects.prefetch_related('facebook_pages__instagram_account'),
            pk=pk,
            created_by=request.user,
        )

    def get(self, request, pk):
        return Response(MetaConnectionSerializer(self._connection(request, pk)).data)

    def post(self, request, pk):
        connection = self._connection(request, pk)
        serializer = MetaAccountSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            select_accounts(connection, **serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        ChatAuditEvent.objects.create(
            actor=request.user,
            action='meta.accounts_selected',
            details={
                'connection_id': connection.pk,
                'facebook_count': len(serializer.validated_data['facebook_page_ids']),
                'instagram_count': len(serializer.validated_data['instagram_account_ids']),
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        connection.refresh_from_db()
        return Response(MetaConnectionSerializer(connection).data)


class MetaConnectionDetailView(APIView):
    permission_classes = [IsCRMAdministrator]
    throttle_scope = 'meta_admin'

    def delete(self, request, pk):
        connection = get_object_or_404(MetaConnection, pk=pk, created_by=request.user)
        disconnect_connection(connection)
        ChatAuditEvent.objects.create(
            actor=request.user,
            action='meta.connection_disconnected',
            details={'connection_id': connection.pk},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
