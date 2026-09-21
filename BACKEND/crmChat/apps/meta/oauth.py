"""OAuth de Meta para Facebook Pages e Instagram Professional.

Este módulo no contiene ni solicita permisos de WhatsApp. Las credenciales de
aplicación se leen exclusivamente desde ``settings`` y los tokens persistidos
se cifran con el almacén de secretos existente del CRM.
"""

import logging
import secrets
from datetime import datetime, timezone as datetime_timezone
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from crmChat.models import (
    ChannelIntegration,
    MetaConnection,
    MetaFacebookPage,
    MetaInstagramAccount,
)

from .services import MetaAPIError, SecretConfigurationError, disconnect_integration, secret_store


logger = logging.getLogger(__name__)


OAUTH_STATE_SALT = 'crmChat.meta.facebook-instagram'
STATE_CACHE_PREFIX = 'meta-oauth-state:'
STATE_GENERATION_PREFIX = 'meta-oauth-generation:'
REQUIRED_SCOPES = {
    'pages_show_list',
    'pages_read_engagement',
    'pages_manage_metadata',
    'pages_messaging',
    'instagram_basic',
    'instagram_manage_messages',
}
FACEBOOK_WEBHOOK_FIELDS = ('messages', 'messaging_postbacks', 'message_deliveries', 'message_reads')
INSTAGRAM_WEBHOOK_FIELDS = ('messages', 'messaging_postbacks')


def _required_setting(name):
    value = getattr(settings, name, '')
    if not value:
        raise SecretConfigurationError(f'Falta configurar {name}.')
    return value


def _graph_url(path):
    root = _required_setting('META_GRAPH_API_URL').rstrip('/')
    version = _required_setting('META_GRAPH_API_VERSION').strip('/')
    return f'{root}/{version}/{path.lstrip("/")}'


def _safe_json(response, operation):
    try:
        data = response.json() if response.content else {}
    except ValueError as exc:
        raise MetaAPIError(f'Meta devolvió una respuesta inválida durante {operation}.') from exc
    if not response.ok:
        error = data.get('error', {}) if isinstance(data, dict) else {}
        code = error.get('code', 'desconocido')
        error_type = error.get('type', 'MetaAPIError')
        raise MetaAPIError(f'Meta rechazó {operation} ({response.status_code}, {error_type}, código {code}).')
    return data


def _request(method, url, *, token='', params=None, data=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        return requests.request(
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            timeout=getattr(settings, 'META_HTTP_TIMEOUT', 15),
        )
    except requests.RequestException as exc:
        raise MetaAPIError('No fue posible conectar con Meta Graph API.') from exc


def _webhook_configuration(channel):
    if channel == 'facebook':
        callback_url = getattr(settings, 'META_FACEBOOK_WEBHOOK_URL', '')
        verify_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN_FACEBOOK', '')
        return 'page', callback_url, verify_token or settings.META_WEBHOOK_VERIFY_TOKEN, FACEBOOK_WEBHOOK_FIELDS
    if channel == 'instagram':
        callback_url = getattr(settings, 'META_INSTAGRAM_WEBHOOK_URL', '')
        verify_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN_INSTAGRAM', '')
        return 'instagram', callback_url, verify_token or settings.META_WEBHOOK_VERIFY_TOKEN, INSTAGRAM_WEBHOOK_FIELDS
    raise ValueError('Canal Meta no soportado para suscripción webhook.')


def _validate_public_webhook_url(url, channel):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise SecretConfigurationError(f'La URL pública del webhook de {channel} debe usar HTTPS.')


def _subscribe_app_webhook(channel):
    object_name, callback_url, verify_token, fields = _webhook_configuration(channel)
    _validate_public_webhook_url(callback_url, channel)
    if not verify_token:
        raise SecretConfigurationError(f'Falta el token de verificación del webhook de {channel}.')
    app_id = _required_setting('META_APP_ID')
    app_access_token = f'{app_id}|{_required_setting("META_APP_SECRET")}'
    data = _safe_json(_request(
        'POST', _graph_url(f'{app_id}/subscriptions'), token=app_access_token,
        data={
            'object': object_name,
            'callback_url': callback_url,
            'fields': ','.join(fields),
            'verify_token': verify_token,
        },
    ), f'la suscripción del webhook de {channel}')
    if data.get('success') is not True:
        raise MetaAPIError(f'Meta no confirmó la suscripción del webhook de {channel}.')


def ensure_oauth_webhook_subscriptions(page_id, page_token, *, facebook=False, instagram=False):
    """Configura webhooks requeridos sin enviar mensajes ni habilitar campañas."""

    if not facebook and not instagram:
        return
    if facebook:
        _subscribe_app_webhook('facebook')
    if instagram:
        _subscribe_app_webhook('instagram')
    page_fields = set(INSTAGRAM_WEBHOOK_FIELDS if instagram else ())
    if facebook:
        page_fields.update(FACEBOOK_WEBHOOK_FIELDS)
    data = _safe_json(_request(
        'POST', _graph_url(f'{page_id}/subscribed_apps'), token=page_token,
        data={'subscribed_fields': ','.join(sorted(page_fields))},
    ), 'la asociación del webhook con la página')
    if data.get('success') is not True:
        raise MetaAPIError('Meta no confirmó la asociación del webhook con la página.')
    logger.info(
        'Suscripciones webhook Meta confirmadas: page_id=%s facebook=%s instagram=%s.',
        page_id, facebook, instagram,
    )


def validate_oauth_webhook_subscriptions(channel, page_id, page_token):
    """Comprueba la suscripción remota sin cambiar la configuración de Meta."""

    object_name, expected_url, _verify_token, expected_fields = _webhook_configuration(channel)
    _validate_public_webhook_url(expected_url, channel)
    app_id = _required_setting('META_APP_ID')
    app_access_token = f'{app_id}|{_required_setting("META_APP_SECRET")}'
    subscriptions = _safe_json(_request(
        'GET', _graph_url(f'{app_id}/subscriptions'), token=app_access_token,
    ), 'la consulta de suscripciones de la aplicación')
    matching = next((item for item in subscriptions.get('data') or [] if item.get('object') == object_name), None)
    fields = {
        item.get('name') if isinstance(item, dict) else item
        for item in ((matching or {}).get('fields') or [])
    }
    if (
        not matching
        or matching.get('active') is not True
        or matching.get('callback_url') != expected_url
        or not set(expected_fields).issubset(fields)
    ):
        raise MetaAPIError(f'La suscripción de webhook de {channel} está incompleta o usa otra URL.')
    page_subscriptions = _safe_json(_request(
        'GET', _graph_url(f'{page_id}/subscribed_apps'), token=page_token,
    ), 'la consulta de aplicaciones suscritas a la página')
    page_entry = next((item for item in page_subscriptions.get('data') or [] if str(item.get('id', '')) == app_id), None)
    page_fields = set((page_entry or {}).get('subscribed_fields') or [])
    if not page_entry or not set(expected_fields).issubset(page_fields):
        raise MetaAPIError('La aplicación no está suscrita a los mensajes de la página seleccionada.')
    return {
        'valid': True,
        'object': object_name,
        'callback_url': expected_url,
        'fields': sorted(expected_fields),
    }


def build_authorization_url(user_id):
    """Genera un state firmado, aleatorio, de un solo uso y la URL OAuth."""

    app_id = _required_setting('META_APP_ID')
    _required_setting('META_APP_SECRET')
    redirect_uri = _required_setting('META_REDIRECT_URI')
    version = _required_setting('META_GRAPH_API_VERSION').strip('/')
    parsed = urlparse(redirect_uri)
    development_http = settings.DEBUG and parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1'}
    if not parsed.netloc or (parsed.scheme != 'https' and not development_http):
        raise SecretConfigurationError('META_REDIRECT_URI debe ser HTTPS (HTTP solo se permite en localhost con DEBUG).')

    configured_scopes = {item.strip() for item in settings.META_OAUTH_SCOPES.split(',') if item.strip()}
    whatsapp_scopes = {scope for scope in configured_scopes if scope.startswith('whatsapp_')}
    if whatsapp_scopes:
        raise SecretConfigurationError('META_OAUTH_SCOPES no puede contener permisos de WhatsApp.')
    missing = REQUIRED_SCOPES - configured_scopes
    if missing:
        raise SecretConfigurationError(f'Faltan permisos Meta requeridos: {", ".join(sorted(missing))}.')

    # El state es opaco: el nonce aleatorio se conserva únicamente en Redis.
    # Así no depende de SECRET_KEY entre procesos y sigue siendo CSRF-safe,
    # con expiración y uso único.
    nonce = secrets.token_urlsafe(32)
    timeout = getattr(settings, 'META_OAUTH_STATE_MAX_AGE', 600)
    generation = cache.get_or_set(f'{STATE_GENERATION_PREFIX}{user_id}', secrets.token_urlsafe(32), timeout=86400)
    cache.set(f'{STATE_CACHE_PREFIX}{nonce}', {'user_id': user_id, 'generation': generation}, timeout=timeout)
    query = urlencode({
        'client_id': app_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ','.join(sorted(configured_scopes)),
        'state': nonce,
    })
    authorize_root = settings.META_OAUTH_AUTHORIZE_URL.rstrip('/')
    return f'{authorize_root}/{version}/dialog/oauth?{query}'


def consume_oauth_state(state):
    """Valida firma/caducidad y consume el nonce para impedir replay."""

    if not state:
        raise signing.BadSignature('Falta el state OAuth.')
    key = f'{STATE_CACHE_PREFIX}{state}'
    cached = cache.get(key)
    if not cached or not cached.get('user_id'):
        raise signing.BadSignature('El state OAuth expiró o ya fue utilizado.')
    cache.delete(key)
    if cached.get('generation') != cache.get(f'{STATE_GENERATION_PREFIX}{cached["user_id"]}'):
        raise signing.BadSignature('El state OAuth fue invalidado al desconectar la cuenta.')
    return cached


def exchange_code_for_token(code):
    """Intercambia el código y solicita el token persistente soportado por Meta."""

    if not code:
        raise MetaAPIError('Meta no devolvió un código de autorización.')
    common = {
        'client_id': _required_setting('META_APP_ID'),
        'client_secret': _required_setting('META_APP_SECRET'),
        'redirect_uri': _required_setting('META_REDIRECT_URI'),
        'code': code,
    }
    initial = _safe_json(
        _request('GET', _graph_url('oauth/access_token'), params=common),
        'el intercambio del código OAuth',
    )
    token = initial.get('access_token', '')
    if not token:
        raise MetaAPIError('Meta no devolvió un access token.')

    # No se presume una duración fija. Se intenta el intercambio oficial y la
    # fecha real se obtiene posteriormente mediante debug_token.
    response = _request('GET', _graph_url('oauth/access_token'), params={
        'grant_type': 'fb_exchange_token',
        'client_id': _required_setting('META_APP_ID'),
        'client_secret': _required_setting('META_APP_SECRET'),
        'fb_exchange_token': token,
    })
    if response.ok:
        long_lived = _safe_json(response, 'el intercambio del token de usuario')
        return long_lived.get('access_token') or token
    # Algunos flujos de Facebook Login for Business ya entregan un token con
    # otra duración. En ese caso se valida el token inicial con debug_token en
    # lugar de asumir que el intercambio es obligatorio.
    return token


def get_token_info(token):
    """Consulta debug_token sin registrar ni devolver credenciales al cliente."""

    app_access_token = f'{_required_setting("META_APP_ID")}|{_required_setting("META_APP_SECRET")}'
    response = _request('GET', _graph_url('debug_token'), params={
        'input_token': token,
        'access_token': app_access_token,
    })
    return _safe_json(response, 'la validación del token').get('data', {})


def validate_access_token(token):
    info = get_token_info(token)
    if not info.get('is_valid') or not info.get('user_id'):
        raise MetaAPIError('El token devuelto por Meta no es válido.')
    granted = set(info.get('scopes') or [])
    missing = REQUIRED_SCOPES - granted
    if missing:
        raise MetaAPIError(f'La autorización no concedió estos permisos: {", ".join(sorted(missing))}.')
    return info


def _get_all_pages(user_token):
    pages = []
    after = ''
    while True:
        params = {
            'fields': 'id,name,access_token,tasks,instagram_business_account{id,username,name,profile_picture_url}',
            'limit': 100,
        }
        if after:
            params['after'] = after
        data = _safe_json(
            _request('GET', _graph_url('me/accounts'), token=user_token, params=params),
            'la consulta de páginas administradas',
        )
        pages.extend(data.get('data') or [])
        cursors = (data.get('paging') or {}).get('cursors') or {}
        next_url = (data.get('paging') or {}).get('next')
        after = cursors.get('after', '') if next_url else ''
        if not after:
            break
    return pages


def get_facebook_pages(user_token):
    """Devuelve activos de Meta aún con tokens; solo debe usarse internamente."""

    return _get_all_pages(user_token)


def get_page_details(page_id, user_token):
    """Obtiene una página y sus tareas desde el inventario administrado.

    Meta expone ``tasks`` en ``/me/accounts``. Solicitar ese campo
    directamente sobre el nodo Page devuelve OAuthException código 100 en
    versiones actuales de Graph API.
    """

    expected = str(page_id)
    for page in _get_all_pages(user_token):
        if str(page.get('id', '')) == expected:
            return page
    raise MetaAPIError('Meta ya no confirmó el acceso a la página vinculada.')


def get_instagram_account(instagram_account_id, page_token):
    """Obtiene metadatos verificables de una cuenta Professional asociada."""

    response = _request(
        'GET',
        _graph_url(instagram_account_id),
        token=page_token,
        params={'fields': 'id,username,name,profile_picture_url'},
    )
    return _safe_json(response, 'la consulta de la cuenta de Instagram')


def get_instagram_accounts(pages):
    """Extrae cuentas profesionales enlazadas sin inventar cuentas ausentes."""

    return [page['instagram_business_account'] for page in pages if page.get('instagram_business_account')]


def _timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=datetime_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


@transaction.atomic
def persist_oauth_inventory(user_id, user_token, token_info):
    """Guarda el token validado y los activos pendientes de selección."""

    facebook_user_id = str(token_info['user_id'])
    connection, _ = MetaConnection.objects.update_or_create(
        created_by_id=user_id,
        facebook_user_id=facebook_user_id,
        defaults={
            'access_token_encrypted': secret_store.encrypt(user_token),
            'granted_scopes': sorted(token_info.get('scopes') or []),
            'token_created_at': timezone.now(),
            'token_expires_at': _timestamp(token_info.get('expires_at')),
            'token_last_validated_at': timezone.now(),
            'token_status': 'pending',
            'is_active': False,
        },
    )
    connection.channel_integrations.update(active=False, connection_status='pending')
    seen_page_ids = []
    for page_data in get_facebook_pages(user_token):
        page_id = str(page_data.get('id', ''))
        page_token = page_data.get('access_token', '')
        if not page_id or not page_token:
            continue
        existing = MetaFacebookPage.objects.filter(page_id=page_id).exclude(connection=connection).first()
        if existing:
            raise MetaAPIError(f'La página {page_id} ya pertenece a otra conexión del CRM.')
        page, _ = MetaFacebookPage.objects.update_or_create(
            connection=connection,
            page_id=page_id,
            defaults={
                'page_name': page_data.get('name') or page_id,
                'page_access_token_encrypted': secret_store.encrypt(page_token),
                'tasks': page_data.get('tasks') or [],
            },
        )
        seen_page_ids.append(page_id)
        instagram_data = page_data.get('instagram_business_account') or {}
        instagram_id = str(instagram_data.get('id', ''))
        if instagram_id:
            conflict = MetaInstagramAccount.objects.filter(instagram_account_id=instagram_id).exclude(facebook_page=page).first()
            if conflict:
                raise MetaAPIError(f'La cuenta de Instagram {instagram_id} ya pertenece a otra conexión del CRM.')
            MetaInstagramAccount.objects.update_or_create(
                facebook_page=page,
                defaults={
                    'instagram_account_id': instagram_id,
                    'username': instagram_data.get('username', ''),
                    'name': instagram_data.get('name', ''),
                    'profile_picture_url': instagram_data.get('profile_picture_url', ''),
                },
            )
        else:
            MetaInstagramAccount.objects.filter(facebook_page=page).delete()
    stale_pages = connection.facebook_pages.exclude(page_id__in=seen_page_ids)
    stale_pages.update(is_selected=False, is_active=False, page_access_token_encrypted='')
    MetaInstagramAccount.objects.filter(facebook_page__in=stale_pages).update(is_selected=False, is_active=False)
    return connection


@transaction.atomic
def select_accounts(connection, facebook_page_ids, instagram_account_ids):
    """Activa activos seleccionados y crea adaptadores del chat sin duplicar tokens."""

    facebook_page_ids = {str(value) for value in facebook_page_ids}
    instagram_account_ids = {str(value) for value in instagram_account_ids}
    pages = list(connection.facebook_pages.select_related('instagram_account').all())
    available_pages = {page.page_id for page in pages}
    available_instagram = {
        page.instagram_account.instagram_account_id
        for page in pages
        if hasattr(page, 'instagram_account')
    }
    if facebook_page_ids - available_pages or instagram_account_ids - available_instagram:
        raise ValueError('La selección contiene una cuenta que no pertenece a esta conexión.')

    if not connection.access_token_encrypted or connection.token_status in {'revoked', 'expired', 'error'}:
        raise MetaAPIError('La autorización Meta no está vigente. Inicia nuevamente OAuth.')
    user_token = secret_store.decrypt(connection.access_token_encrypted)
    token_info = validate_access_token(user_token)
    if str(token_info.get('user_id', '')) != connection.facebook_user_id:
        raise MetaAPIError('El token ya no corresponde al usuario de Facebook autorizado.')
    verified_pages = {}
    verified_instagram = {}
    for page in pages:
        instagram = page.instagram_account if hasattr(page, 'instagram_account') else None
        facebook_selected = page.page_id in facebook_page_ids
        instagram_selected = bool(instagram and instagram.instagram_account_id in instagram_account_ids)
        if not facebook_selected and not instagram_selected:
            continue
        details = get_page_details(page.page_id, user_token)
        if str(details.get('id', '')) != page.page_id or not details.get('access_token'):
            raise MetaAPIError(f'Meta no confirmó el acceso a la página {page.page_id}.')
        tasks = details.get('tasks') or []
        if facebook_selected and 'MESSAGING' not in tasks:
            raise MetaAPIError(f'La página {page.page_id} no tiene tarea de mensajería.')
        verified_pages[page.page_id] = details
        if instagram_selected:
            linked = details.get('instagram_business_account') or {}
            if str(linked.get('id', '')) != instagram.instagram_account_id:
                raise MetaAPIError('La cuenta de Instagram ya no está asociada a la página seleccionada.')
            account = get_instagram_account(instagram.instagram_account_id, details['access_token'])
            if str(account.get('id', '')) != instagram.instagram_account_id:
                raise MetaAPIError('Meta no confirmó la cuenta profesional de Instagram.')
            verified_instagram[instagram.instagram_account_id] = account
        ensure_oauth_webhook_subscriptions(
            page.page_id,
            details['access_token'],
            facebook=facebook_selected,
            instagram=instagram_selected,
        )

    for page in pages:
        instagram = page.instagram_account if hasattr(page, 'instagram_account') else None
        facebook_selected = page.page_id in facebook_page_ids
        instagram_selected = bool(instagram and instagram.instagram_account_id in instagram_account_ids)
        if page.page_id in verified_pages:
            details = verified_pages[page.page_id]
            page.page_name = details.get('name') or page.page_name
            page.page_access_token_encrypted = secret_store.encrypt(details['access_token'])
            page.tasks = details.get('tasks') or []
        page.is_selected = facebook_selected
        page.is_active = facebook_selected or instagram_selected
        page.save(update_fields=[
            'page_name', 'page_access_token_encrypted', 'tasks', 'is_selected', 'is_active', 'updated_at',
        ])

        current_facebook = ChannelIntegration.objects.filter(
            channel='facebook', external_account_id=page.page_id,
        ).first()
        facebook_configuration = dict(current_facebook.configuration) if current_facebook else {}
        facebook_configuration['oauth_provider'] = 'facebook'
        facebook_defaults = {
            'name': page.page_name,
            'active': facebook_selected,
            'connection_status': 'pending',
            'last_validated_at': timezone.now() if facebook_selected else None,
            'last_error': '',
            'disconnected_at': None if facebook_selected else timezone.now(),
            'app_id': settings.META_APP_ID,
            'page_id': page.page_id,
            'graph_api_version': settings.META_GRAPH_API_VERSION,
            'meta_connection': connection,
            'meta_facebook_page': page,
            'created_by': connection.created_by,
            'configuration': facebook_configuration,
        }
        ChannelIntegration.objects.update_or_create(
            channel='facebook',
            external_account_id=page.page_id,
            defaults=facebook_defaults,
        )

        if instagram:
            if instagram.instagram_account_id in verified_instagram:
                account = verified_instagram[instagram.instagram_account_id]
                instagram.username = account.get('username') or instagram.username
                instagram.name = account.get('name') or instagram.name
            instagram.is_selected = instagram_selected
            instagram.is_active = instagram_selected
            instagram.save(update_fields=['username', 'name', 'is_selected', 'is_active', 'updated_at'])
            current_instagram = ChannelIntegration.objects.filter(
                channel='instagram', external_account_id=instagram.instagram_account_id,
            ).first()
            instagram_configuration = dict(current_instagram.configuration) if current_instagram else {}
            instagram_configuration['oauth_provider'] = 'facebook'
            ChannelIntegration.objects.update_or_create(
                channel='instagram',
                external_account_id=instagram.instagram_account_id,
                defaults={
                    'name': instagram.username or instagram.name or instagram.instagram_account_id,
                    'active': instagram_selected,
                    'connection_status': 'pending',
                    'last_validated_at': timezone.now() if instagram_selected else None,
                    'last_error': '',
                    'disconnected_at': None if instagram_selected else timezone.now(),
                    'app_id': settings.META_APP_ID,
                    'page_id': page.page_id,
                    'instagram_account_id': instagram.instagram_account_id,
                    'graph_api_version': settings.META_GRAPH_API_VERSION,
                    'meta_connection': connection,
                    'meta_facebook_page': page,
                    'meta_instagram_account': instagram,
                    'created_by': connection.created_by,
                    'configuration': instagram_configuration,
                },
            )

    connection.is_active = bool(facebook_page_ids or instagram_account_ids)
    connection.token_status = 'valid' if connection.is_active else 'pending'
    connection.token_last_validated_at = timezone.now()
    connection.save(update_fields=['is_active', 'token_status', 'token_last_validated_at', 'updated_at'])
    return connection


@transaction.atomic
def disconnect_connection(connection):
    """Desactiva la conexión sin borrar conversaciones ni auditoría."""

    for integration in connection.channel_integrations.all():
        disconnect_integration(integration)
    connection.facebook_pages.update(
        is_active=False,
        is_selected=False,
        page_access_token_encrypted='',
    )
    MetaInstagramAccount.objects.filter(facebook_page__connection=connection).update(is_active=False, is_selected=False)
    connection.is_active = False
    connection.token_status = 'revoked'
    connection.access_token_encrypted = ''
    connection.save(update_fields=['is_active', 'token_status', 'access_token_encrypted', 'updated_at'])
    cache.set(f'{STATE_GENERATION_PREFIX}{connection.created_by_id}', secrets.token_urlsafe(32), timeout=86400)
    return connection
