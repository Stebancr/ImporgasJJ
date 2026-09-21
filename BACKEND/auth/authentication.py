from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class PasswordVersionJWTAuthentication(JWTAuthentication):
    """Reject tokens issued before this particular user's password changed."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if validated_token.get('password_version', 0) != user.password_version:
            raise AuthenticationFailed('La sesión expiró. Inicia sesión de nuevo.')
        return user
