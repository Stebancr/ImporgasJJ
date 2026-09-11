"""Webhook y acceso OAuth de Instagram Business."""

from urllib.parse import urlencode

from django.core import signing
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from crmChat.apps.meta.services import MetaAPIError, SecretConfigurationError
from crmChat.apps.meta.views import IsCRMAdministrator
from crmChat.apps.meta.views import MetaWebhookView
from crmChat.models import ChannelIntegration, ChatAuditEvent

from .services import build_authorization_url, consume_oauth_state, exchange_authorization_code


class InstagramWebhookView(MetaWebhookView):
    forced_channel = 'instagram'


class InstagramOAuthStartView(APIView):
    """Entrega al administrador la URL de Meta; nunca expone secretos."""

    permission_classes = [IsCRMAdministrator]
    throttle_scope = 'meta_admin'

    def post(self, request, pk):
        try:
            integration = ChannelIntegration.objects.get(pk=pk, channel='instagram')
            authorization_url, redirect_uri = build_authorization_url(integration, request.user.pk)
            ChatAuditEvent.objects.create(
                actor=request.user,
                action='integration.instagram_oauth_started',
                details={'integration_id': integration.pk, 'channel': 'instagram'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return Response({'authorization_url': authorization_url, 'redirect_uri': redirect_uri})
        except ChannelIntegration.DoesNotExist:
            return Response({'detail': 'Integración de Instagram no encontrada.'}, status=404)
        except (SecretConfigurationError, ValueError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class InstagramOAuthCallbackView(APIView):
    """Callback público registrado en Meta; el token queda solo en backend."""

    authentication_classes = []
    permission_classes = []
    throttle_scope = 'meta_admin'

    @staticmethod
    def _redirect(result, integration_id=''):
        query = urlencode({'instagram_oauth': result, 'integration_id': integration_id})
        return HttpResponseRedirect(f'/admin/chat/integraciones?{query}')

    def get(self, request):
        if request.query_params.get('error'):
            return self._redirect('denied')
        try:
            payload = consume_oauth_state(request.query_params.get('state', ''))
            integration = ChannelIntegration.objects.get(pk=payload['integration_id'], channel='instagram')
            exchange_authorization_code(integration, request.query_params.get('code', ''))
            ChatAuditEvent.objects.create(
                actor_id=payload.get('user_id'),
                action='integration.instagram_oauth_completed',
                details={'integration_id': integration.pk, 'channel': 'instagram'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return self._redirect('success', integration.pk)
        except (signing.BadSignature, signing.SignatureExpired, KeyError):
            return self._redirect('invalid_state')
        except ChannelIntegration.DoesNotExist:
            return self._redirect('not_found')
        except (MetaAPIError, SecretConfigurationError, ValueError):
            return self._redirect('error')
