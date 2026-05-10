from rest_framework_simplejwt.views import TokenObtainPairView
from auth.serializers import TokenLMSSerializer


class TokenLMSView(TokenObtainPairView):
    """
    Extends TokenObtainPairView to include additional user information
    in the token response.
    """
    serializer_class = TokenLMSSerializer