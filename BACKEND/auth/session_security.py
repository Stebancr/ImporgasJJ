"""One authority for HTTP, refresh, Django sessions and realtime credentials."""
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.exceptions import AuthenticationFailed
from usuarios.models import GlobalAuthState, AuthSession


def current_version():
    return GlobalAuthState.objects.get_or_create(pk=1, defaults={'version': 1})[0].version


def revoked():
    return AuthenticationFailed({'detail': 'La plataforma fue actualizada. Por seguridad, inicia sesión nuevamente.',
        'code': 'SESSION_REVOKED'}, code='SESSION_REVOKED')


def validate_versions(user, global_version, password_version):
    if (not user or not user.is_active or type(global_version) is not int
            or type(password_version) is not int or global_version != current_version()
            or password_version != user.password_version):
        raise revoked()


def validate_claims(user, claims, credential_type=None):
    validate_versions(user, claims.get('global_auth_version'), claims.get('password_version'))
    try:
        session = AuthSession.objects.get(pk=claims.get('session_id'), user=user,
            revoked_at__isnull=True, expires_at__gt=timezone.now(),
            global_auth_version=claims['global_auth_version'], password_version=user.password_version)
    except (AuthSession.DoesNotExist, ValueError, TypeError, KeyError, ValidationError):
        raise revoked()
    if str(claims.get('user_id')) != str(user.pk):
        raise revoked()
    if credential_type and session.credential_type != credential_type:
        raise revoked()
    return session


def validate_django_session(user, data):
    return validate_claims(user, {'global_auth_version': data.get('global_auth_version'),
        'password_version': data.get('password_version'), 'session_id': data.get('auth_session_id'),
        'user_id': user.pk}, credential_type='django_session')


def attach_claims(token, user):
    session = AuthSession.objects.create(user=user, global_auth_version=current_version(),
        password_version=user.password_version,
        expires_at=datetime.fromtimestamp(token['exp'], tz=dt_timezone.utc))
    token['global_auth_version'] = session.global_auth_version
    token['password_version'] = session.password_version
    token['session_id'] = str(session.pk)
    return token
