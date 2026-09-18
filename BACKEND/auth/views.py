from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from auth.serializers import TokenLMSSerializer, PasswordVersionRefreshSerializer


class TokenLMSView(TokenObtainPairView):
    """
    Extends TokenObtainPairView to include additional user information
    in the token response.
    """
    serializer_class = TokenLMSSerializer
    throttle_scope = 'login'


class PasswordVersionRefreshView(TokenRefreshView):
    serializer_class = PasswordVersionRefreshSerializer
