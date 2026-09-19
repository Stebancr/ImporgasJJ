"""Alta segura de WhatsApp Business App Coexistence mediante Embedded Signup.

El flujo solo autoriza la cuenta, valida sus identificadores y suscribe el
webhook. No envía mensajes, no crea plantillas y no habilita el bot.
"""

import logging
import secrets

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from crmChat.apps.meta.services import (
    MetaAPIError,
    SecretConfigurationError,
    graph_request,
    secret_store,
    validate_integration_connection,
    validate_whatsapp_token_permissions,
)
from crmChat.models import ChannelIntegration


logger = logging.getLogger(__name__)
STATE_PREFIX = 'whatsapp-coexistence-state:'
COMPLETION_EVENT = 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING'
FEATURE_TYPE = 'whatsapp_business_app_onboarding'


def _required_setting(name):
    value = getattr(settings, name, '')
    if not value:
        raise SecretConfigurationError(f'Falta configurar {name}.')
    return str(value)


def create_signup_configuration(user_id):
    """Entrega solo parámetros públicos y un nonce de un uso ligado al admin."""

    app_id = _required_setting('META_APP_ID')
    _required_setting('META_APP_SECRET')
    config_id = _required_setting('META_WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID')
    graph_version = _required_setting('META_GRAPH_API_VERSION').strip('/')
    signup_version = str(getattr(settings, 'META_WHATSAPP_EMBEDDED_SIGNUP_VERSION', '4'))
    nonce = secrets.token_urlsafe(32)
    timeout = getattr(settings, 'META_WHATSAPP_EMBEDDED_SIGNUP_STATE_MAX_AGE', 600)
    cache.set(f'{STATE_PREFIX}{nonce}', {'user_id': user_id}, timeout=timeout)
    return {
        'app_id': app_id,
        'config_id': config_id,
        'graph_api_version': graph_version,
        'embedded_signup_version': signup_version,
        'feature_type': FEATURE_TYPE,
        'state': nonce,
    }


def consume_signup_state(state, user_id):
    """Consume el nonce antes de intercambiar el código para impedir replay."""

    key = f'{STATE_PREFIX}{state}'
    cached = cache.get(key) if state else None
    if not cached or cached.get('user_id') != user_id:
        raise MetaAPIError('La sesión de conexión de WhatsApp expiró o ya fue utilizada.')
    cache.delete(key)


def exchange_signup_code(code):
    """Intercambia el código de Facebook Login sin exponer el App Secret."""

    if not code:
        raise MetaAPIError('Meta no devolvió el código de autorización de WhatsApp.')
    root = _required_setting('META_GRAPH_API_URL').rstrip('/')
    version = _required_setting('META_GRAPH_API_VERSION').strip('/')
    try:
        response = requests.get(
            f'{root}/{version}/oauth/access_token',
            params={
                'client_id': _required_setting('META_APP_ID'),
                'client_secret': _required_setting('META_APP_SECRET'),
                'code': code,
            },
            timeout=getattr(settings, 'META_HTTP_TIMEOUT', 15),
        )
        data = response.json() if response.content else {}
    except (requests.RequestException, ValueError) as exc:
        raise MetaAPIError('No fue posible intercambiar la autorización de WhatsApp con Meta.') from exc
    if not response.ok or not isinstance(data, dict) or not data.get('access_token'):
        error = data.get('error', {}) if isinstance(data, dict) else {}
        code_value = error.get('code', 'desconocido') if isinstance(error, dict) else 'desconocido'
        subcode = error.get('error_subcode') if isinstance(error, dict) else None
        detail = (
            error.get('error_data', {}).get('details')
            if isinstance(error, dict) and isinstance(error.get('error_data'), dict)
            else ''
        ) or (error.get('message') if isinstance(error, dict) else '') or 'Meta no proporcionó más detalles.'
        detail = ' '.join(str(detail).replace(str(code), '[código oculto]').split())[:500]
        request_id = str(
            response.headers.get('x-fb-request-id')
            or response.headers.get('x-fb-trace-id')
            or (error.get('fbtrace_id') if isinstance(error, dict) else '')
            or ''
        )[:120]
        logger.warning(
            'Meta rechazó Embedded Signup: phase=code_exchange endpoint=/oauth/access_token '
            'status=%s code=%s subcode=%s request_id=%s detail=%s',
            response.status_code, code_value, subcode or '-', request_id or '-', detail,
        )
        raise MetaAPIError(
            f'Meta rechazó la autorización de WhatsApp '
            f'({response.status_code}, código {code_value}): {detail}',
            http_status=response.status_code,
            meta_code=code_value,
            meta_subcode=subcode,
            request_id=request_id,
            endpoint='/oauth/access_token',
            phase='code_exchange',
        )
    return data['access_token']


def _validate_waba(integration, requested_business_id):
    """Confirma el WABA y, si Meta lo informa, el negocio propietario."""

    data = graph_request(
        integration,
        'GET',
        integration.external_account_id,
        params={'fields': 'id,name,owner_business_info'},
    )
    if str(data.get('id', '')) != integration.external_account_id:
        raise MetaAPIError('El WABA devuelto por Meta no corresponde a la cuenta autorizada.')
    owner = data.get('owner_business_info') or {}
    owner_business_id = str(owner.get('id') or '') if isinstance(owner, dict) else ''
    if requested_business_id and owner_business_id != requested_business_id:
        raise MetaAPIError('El Business ID informado no es el propietario del WABA autorizado.')
    if owner_business_id:
        integration.business_id = owner_business_id
        integration.save(update_fields=['business_id', 'updated_at'])
    return data


def _phone_inventory(integration):
    phones = []
    after = ''
    while True:
        params = {
            'fields': 'id,display_phone_number,verified_name,quality_rating,platform_type',
            'limit': 100,
        }
        if after:
            params['after'] = after
        result = graph_request(
            integration, 'GET', f'{integration.external_account_id}/phone_numbers', params=params,
        )
        phones.extend(item for item in (result.get('data') or []) if isinstance(item, dict))
        paging = result.get('paging') or {}
        after = ((paging.get('cursors') or {}).get('after') or '') if paging.get('next') else ''
        if not after:
            return phones


def _select_phone(phones, requested_phone_id):
    if requested_phone_id:
        match = next((item for item in phones if str(item.get('id', '')) == requested_phone_id), None)
        if not match:
            raise MetaAPIError('El Phone Number ID informado por Embedded Signup no pertenece al WABA autorizado.')
        return match
    if len(phones) != 1:
        raise MetaAPIError(
            'Meta no identificó un único número en el WABA. Reinicia Embedded Signup y selecciona un número concreto.'
        )
    return phones[0]


def _prepare_integration(user, token, waba_id, phone_id, business_id=''):
    integration = ChannelIntegration.objects.filter(
        channel=ChannelIntegration.CHANNEL_WHATSAPP,
        external_account_id=waba_id,
    ).first()
    if integration and integration.active:
        raise MetaAPIError('Este WABA ya está conectado. Desconéctalo antes de iniciar una nueva autorización.')
    if integration and phone_id and integration.phone_number_id and integration.phone_number_id != phone_id:
        raise MetaAPIError('Este WABA ya conserva historial asociado a otro Phone Number ID.')
    phone_conflict = None
    if phone_id:
        phone_conflict = ChannelIntegration.objects.filter(
            channel=ChannelIntegration.CHANNEL_WHATSAPP,
            phone_number_id=phone_id,
        ).exclude(pk=getattr(integration, 'pk', None)).first()
    if phone_conflict:
        raise MetaAPIError('Este número ya pertenece a otra integración de WhatsApp del CRM.')
    if integration is None:
        integration = ChannelIntegration(
            channel=ChannelIntegration.CHANNEL_WHATSAPP,
            external_account_id=waba_id,
            created_by=user,
        )
    integration.name = integration.name or 'WhatsApp Business App'
    integration.phone_number_id = phone_id or integration.phone_number_id
    integration.business_id = business_id
    integration.app_id = _required_setting('META_APP_ID')
    integration.graph_api_version = _required_setting('META_GRAPH_API_VERSION').strip('/')
    integration.access_token_encrypted = secret_store.encrypt(token)
    integration.active = False
    integration.connection_status = 'pending'
    integration.last_error = ''
    integration.disconnected_at = None
    integration.configuration = {
        **(integration.configuration or {}),
        'onboarding_method': 'embedded_signup',
        'coexistence': True,
        'embedded_signup_version': str(
            getattr(settings, 'META_WHATSAPP_EMBEDDED_SIGNUP_VERSION', '4')
        ),
        'bot_enabled': False,
    }
    integration.save()
    return integration


def complete_coexistence_signup(*, user, state, code, waba_id, phone_number_id='', business_id=''):
    """Completa el alta y activa la cuenta solo después de validarla en Graph."""

    consume_signup_state(state, user.pk)
    token = exchange_signup_code(code)
    waba_id = str(waba_id or '')
    phone_number_id = str(phone_number_id or '')
    business_id = str(business_id or '')
    if not waba_id:
        raise MetaAPIError('Embedded Signup no devolvió el WABA ID.')

    integration = None
    try:
        # Se guarda primero como inactiva para que cualquier error de Meta deje
        # una conexión diagnosticable que nunca pueda enviar mensajes.
        integration = _prepare_integration(user, token, waba_id, phone_number_id, business_id)
        validate_whatsapp_token_permissions(integration)
        _validate_waba(integration, business_id)
        phone = _select_phone(
            _phone_inventory(integration), phone_number_id or integration.phone_number_id,
        )
        selected_phone_id = str(phone.get('id', ''))
        if not selected_phone_id:
            raise MetaAPIError('Meta no devolvió un Phone Number ID válido.')
        conflict = ChannelIntegration.objects.filter(
            channel=ChannelIntegration.CHANNEL_WHATSAPP,
            phone_number_id=selected_phone_id,
        ).exclude(pk=integration.pk).first()
        if conflict:
            raise MetaAPIError('Este número ya pertenece a otra integración de WhatsApp del CRM.')
        integration.phone_number_id = selected_phone_id
        integration.display_phone_number = str(phone.get('display_phone_number') or '')
        integration.name = str(phone.get('verified_name') or integration.name)
        integration.save(update_fields=[
            'phone_number_id', 'display_phone_number', 'name', 'updated_at',
        ])

        # Suscribir el webhook no envía mensajes ni activa plantillas.
        subscribed = graph_request(
            integration, 'POST', f'{waba_id}/subscribed_apps', json_body={},
        )
        if subscribed.get('success') not in (True, 'true'):
            raise MetaAPIError('Meta no confirmó la suscripción del webhook para el WABA.')
        result = validate_integration_connection(integration)
        with transaction.atomic():
            integration = ChannelIntegration.objects.select_for_update().get(pk=integration.pk)
            if ChannelIntegration.objects.filter(
                channel=ChannelIntegration.CHANNEL_WHATSAPP,
                phone_number_id=selected_phone_id,
                active=True,
            ).exclude(pk=integration.pk).exists():
                raise MetaAPIError('Ya existe una integración activa para este número de WhatsApp.')
            integration.active = True
            integration.connection_status = 'pending'
            integration.last_validated_at = timezone.now()
            integration.last_error = ''
            integration.save(update_fields=[
                'active', 'connection_status', 'last_validated_at', 'last_error', 'updated_at',
            ])
        return integration, result
    except MetaAPIError as exc:
        if integration and integration.pk:
            ChannelIntegration.objects.filter(pk=integration.pk).update(
                active=False,
                connection_status='error',
                last_error=str(exc)[:500],
            )
        logger.warning(
            'Falló WhatsApp Coexistence: integration_id=%s onboarding=embedded_signup '
            'phase=%s endpoint=%s status=%s meta_code=%s request_id=%s detail=%s',
            integration.pk if integration and integration.pk else '-',
            getattr(exc, 'phase', '') or 'validation',
            getattr(exc, 'endpoint', '') or '-',
            getattr(exc, 'http_status', None) or '-',
            getattr(exc, 'meta_code', None) or '-',
            getattr(exc, 'request_id', '') or '-',
            str(exc)[:500],
        )
        raise
    except IntegrityError as exc:
        if integration and integration.pk:
            ChannelIntegration.objects.filter(pk=integration.pk).update(
                active=False,
                connection_status='error',
                last_error='Ya existe una integración activa para este número de WhatsApp.',
            )
        raise MetaAPIError('Ya existe una integración activa para este número de WhatsApp.') from exc
