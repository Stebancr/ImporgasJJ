from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from usuarios.models import Credenciales

class TokenLMSSerializer(TokenObtainPairSerializer):
    """
    Extends TokenObtainPairSerializer to include additional user information
    in the token response.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['password_version'] = user.password_version
        return token

    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except Exception as e:
            raise AuthenticationFailed('El usuario no está activo o no tiene permiso para ingresar.')
        user = self.user
        if not getattr(user, 'is_active', False):
            raise AuthenticationFailed('El usuario no está activo o no tiene permiso para ingresar.')
        data["is_admin"] = int(getattr(user, "tipo_usuario", 0) or 0)
        location = getattr(user, 'location', None)
        data["location_id"] = location.id if location else None
        data["location_name"] = location.name if location else None
        return data


class PasswordVersionRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = Credenciales.objects.filter(pk=token.get('user_id'), estado=1).first()
        if not user or token.get('password_version', 0) != user.password_version:
            raise AuthenticationFailed('La sesión expiró. Inicia sesión de nuevo.')
        return super().validate(attrs)
