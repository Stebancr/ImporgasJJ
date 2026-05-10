from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed

class TokenLMSSerializer(TokenObtainPairSerializer):
    """
    Extends TokenObtainPairSerializer to include additional user information
    in the token response.
    """

    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except Exception as e:
            raise AuthenticationFailed('El usuario no está activo o no tiene permiso para ingresar.')
        user = self.user
        if not getattr(user, 'is_active', False):
            raise AuthenticationFailed('El usuario no está activo o no tiene permiso para ingresar.')
        data["is_admin"] = int(getattr(user, "tipo_usuario", 0) or 0)
        return data