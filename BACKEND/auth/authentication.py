from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from .session_security import validate_claims, validate_versions, validate_django_session, revoked


class PasswordVersionJWTAuthentication(JWTAuthentication):
    """Reject tokens issued before this particular user's password changed."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        validate_claims(user, validated_token, credential_type='jwt')
        return user


class VersionedTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        from usuarios.models import PersistentTokenVersion
        metadata = PersistentTokenVersion.objects.filter(token=token).first()
        if not metadata:
            raise revoked()
        validate_versions(user, metadata.global_auth_version, metadata.password_version)
        validate_claims(user, {'global_auth_version': metadata.global_auth_version,
            'password_version': metadata.password_version, 'session_id': str(metadata.session_id), 'user_id': user.pk}, credential_type='drf')
        return user, token


class VersionedSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result:
            user, _ = result
            validate_django_session(user, request.session)
        return result
