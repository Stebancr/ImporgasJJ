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
    cache.set(
        f'instagram-oauth-state:{nonce}',
        {'integration_id': integration.pk, 'user_id': user_id},
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
    except requests.RequestException as exc:
        raise MetaAPIError('No fue posible conectar con Instagram para completar el acceso.') from exc

    account_id = str(short_data.get('user_id') or long_data.get('user_id') or '')
    if not account_id:
        raise MetaAPIError('Instagram no devolvió el identificador de la cuenta profesional.')
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
    integration.save(update_fields=[
        'access_token_encrypted', 'instagram_account_id', 'external_account_id',
        'token_expires_at', 'updated_at',
    ])
    return integration


def _send(integration, recipient_id, payload):
    # Las cuentas conectadas mediante Facebook Login usan graph.facebook.com
    # y el Page Access Token relacionado; se conserva Instagram Login legado.
    base_url = None if integration.meta_facebook_page_id else integration.configuration.get('api_base_url', 'https://graph.instagram.com')
    body = {'recipient': {'id': recipient_id}}
    body.update(payload)
    return graph_request(
        integration,
        'POST',
        f'{integration.instagram_account_id}/messages',
        json_body=body,
        base_url=base_url,
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
