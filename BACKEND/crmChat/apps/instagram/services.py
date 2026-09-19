"""Operaciones de salida y OAuth para Instagram Messaging API."""

import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.utils import timezone

from crmChat.apps.meta.services import (
    MetaAPIError,
    SecretConfigurationError,
    graph_request,
    secret_store,
)
from crmChat.models import ChannelIntegration


OAUTH_STATE_SALT = 'crmChat.instagram.business-login'
STATE_GENERATION_PREFIX = 'instagram-oauth-generation:'


def _oauth_setting(name):
    value = getattr(settings, name, '')
    if not value:
        raise SecretConfigurationError(f'Falta configurar {name}.')
    return value


def build_authorization_url(integration, user_id):
    """Crea una URL de autorización con estado firmado y de un solo uso."""

    if integration.channel != 'instagram':
        raise ValueError('La integración seleccionada no corresponde a Instagram.')
    if not integration.app_id or not integration.app_secret_encrypted:
        raise SecretConfigurationError('Instagram requiere App ID y App Secret configurados.')

    redirect_uri = _oauth_setting('INSTAGRAM_OAUTH_REDIRECT_URI')
    parsed_redirect = urlparse(redirect_uri)
    if parsed_redirect.scheme != 'https' or not parsed_redirect.netloc:
        raise SecretConfigurationError('INSTAGRAM_OAUTH_REDIRECT_URI debe ser una URL HTTPS pública.')
    nonce = secrets.token_urlsafe(24)
    max_age = getattr(settings, 'INSTAGRAM_OAUTH_STATE_MAX_AGE', 600)
    generation = cache.get_or_set(
        f'{STATE_GENERATION_PREFIX}{integration.pk}', secrets.token_urlsafe(32), timeout=86400,
    )
    cache.set(
        f'instagram-oauth-state:{nonce}',
        {'integration_id': integration.pk, 'user_id': user_id, 'generation': generation},
        timeout=max_age,
    )
    state = signing.dumps(
        {'integration_id': integration.pk, 'user_id': user_id, 'nonce': nonce},
        salt=OAUTH_STATE_SALT,
        compress=True,
    )
    scopes = [scope.strip() for scope in settings.INSTAGRAM_OAUTH_SCOPES.split(',') if scope.strip()]
    query = urlencode({
        'client_id': integration.app_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ','.join(scopes),
        'state': state,
    })
    return f"{settings.INSTAGRAM_OAUTH_AUTHORIZE_URL.rstrip('/')}?{query}", redirect_uri


def consume_oauth_state(state):
    """Valida firma, caducidad y evita reutilizar el callback OAuth."""

    if not state:
        raise signing.BadSignature('Falta el estado OAuth.')
    payload = signing.loads(
        state,
        salt=OAUTH_STATE_SALT,
        max_age=getattr(settings, 'INSTAGRAM_OAUTH_STATE_MAX_AGE', 600),
    )
    nonce = payload.get('nonce', '')
    key = f'instagram-oauth-state:{nonce}'
    cached = cache.get(key)
    if not cached or cached.get('integration_id') != payload.get('integration_id'):
        raise signing.BadSignature('El estado OAuth expiró o ya fue utilizado.')
    cache.delete(key)
    if cached.get('generation') != cache.get(f'{STATE_GENERATION_PREFIX}{payload["integration_id"]}'):
        raise signing.BadSignature('El estado OAuth fue invalidado al desconectar la cuenta.')
    return payload


def exchange_authorization_code(integration, code):
    """Intercambia el código, obtiene token de larga duración y lo cifra."""

    if not code:
        raise MetaAPIError('Instagram no devolvió un código de autorización.')
    app_secret = secret_store.decrypt(integration.app_secret_encrypted)
    redirect_uri = _oauth_setting('INSTAGRAM_OAUTH_REDIRECT_URI')
    timeout = getattr(settings, 'META_HTTP_TIMEOUT', 15)
    try:
        short_response = requests.post(
            settings.INSTAGRAM_OAUTH_TOKEN_URL,
            data={
                'client_id': integration.app_id,
                'client_secret': app_secret,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
                'code': code,
            },
            timeout=timeout,
        )
        short_data = short_response.json() if short_response.content else {}
        if not short_response.ok or not short_data.get('access_token'):
            raise MetaAPIError(f'Instagram rechazó el código OAuth ({short_response.status_code}).')

        long_response = requests.get(
            f"{settings.INSTAGRAM_GRAPH_API_URL.rstrip('/')}/access_token",
            params={
                'grant_type': 'ig_exchange_token',
                'client_secret': app_secret,
                'access_token': short_data['access_token'],
            },
            timeout=timeout,
        )
        long_data = long_response.json() if long_response.content else {}
        if not long_response.ok or not long_data.get('access_token'):
            raise MetaAPIError(f'Instagram rechazó el intercambio del token ({long_response.status_code}).')
        account_response = requests.get(
            f"{settings.INSTAGRAM_GRAPH_API_URL.rstrip('/')}/me",
            headers={'Authorization': f"Bearer {long_data['access_token']}"},
            params={'fields': 'id,username,account_type'},
            timeout=timeout,
        )
        account_data = account_response.json() if account_response.content else {}
        if not account_response.ok:
            raise MetaAPIError(f'Instagram no permitió consultar la cuenta profesional ({account_response.status_code}).')
    except requests.RequestException as exc:
        raise MetaAPIError('No fue posible conectar con Instagram para completar el acceso.') from exc

    account_id = str(short_data.get('user_id') or long_data.get('user_id') or '')
    if not account_id:
        raise MetaAPIError('Instagram no devolvió el identificador de la cuenta profesional.')
    if str(account_data.get('id', '')) != account_id or account_data.get('account_type') not in {'BUSINESS', 'MEDIA_CREATOR'}:
        raise MetaAPIError('Instagram no confirmó una cuenta Professional/Business elegible.')
    if ChannelIntegration.objects.filter(
        channel='instagram',
        external_account_id=account_id,
    ).exclude(pk=integration.pk).exists():
        raise MetaAPIError('Esta cuenta de Instagram ya está conectada a otra integración.')
    expires_in = int(long_data.get('expires_in') or 0)
    integration.access_token_encrypted = secret_store.encrypt(long_data['access_token'])
    integration.instagram_account_id = account_id
    integration.external_account_id = account_id
    integration.token_expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    integration.active = False
    integration.connection_status = 'pending'
    integration.last_validated_at = timezone.now()
    integration.last_error = ''
    integration.save(update_fields=[
        'access_token_encrypted', 'instagram_account_id', 'external_account_id',
        'token_expires_at', 'active', 'connection_status', 'last_validated_at', 'last_error', 'updated_at',
    ])
    return integration


def _send(integration, recipient_id, payload):
    # Facebook Login usa el Messenger Platform Send API de la página enlazada
    # y su Page Access Token. Instagram Login usa el host/API nativo de Instagram.
    if integration.meta_facebook_page_id:
        account_id = integration.meta_facebook_page.page_id
        base_url = None
    else:
        account_id = integration.instagram_account_id
        base_url = integration.configuration.get('api_base_url', 'https://graph.instagram.com')
    body = {'recipient': {'id': recipient_id}}
    if integration.meta_facebook_page_id:
        body['messaging_type'] = 'RESPONSE'
    body.update(payload)
    return graph_request(
        integration,
        'POST',
        f'{account_id}/messages',
        json_body=body,
        base_url=base_url,
    )


def get_sender_profile(integration, sender_id):
    """Obtiene el perfil público del remitente sin convertir un fallo opcional en error de conexión."""

    base_url = (
        None
        if integration.meta_facebook_page_id
        else integration.configuration.get('api_base_url', 'https://graph.instagram.com')
    )
    return graph_request(
        integration,
        'GET',
        sender_id,
        params={'fields': 'id,name,username,profile_pic'},
        base_url=base_url,
        record_error=False,
    )


def send_text(integration, recipient_id, text, quick_replies=None):
    message = {'text': text}
    if quick_replies:
        message['quick_replies'] = quick_replies
    return _send(integration, recipient_id, {'message': message})


def sender_action(integration, recipient_id, action):
    if action not in {'mark_seen', 'typing_on', 'typing_off'}:
        raise ValueError('Sender action no soportada.')
    return _send(integration, recipient_id, {'sender_action': action})
