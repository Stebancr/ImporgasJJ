"""Customer account actions backed by Django password validation and reset tokens."""
import logging
import ipaddress

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import Credenciales
from . import password_recovery
from django.utils.crypto import salted_hmac
from django.utils.translation import override
from types import SimpleNamespace
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)
RESET_RESPONSE = {'message': 'Si existe una cuenta asociada a este correo, recibirás un enlace para restablecer tu contraseña.'}


class NewPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Las contraseñas no coinciden.'})
        try:
            user = self.context.get('user')
            profile = user.usuario_rel if user else None
            subject = SimpleNamespace(_meta=Credenciales._meta, username=user.usuario if user else '', email=profile.correo if profile else '',
                                      first_name=profile.nombre_completo if profile else '', last_name='')
            with override('es'):
                validate_password(attrs['new_password'], user=subject)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)}) from exc
        return attrs


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.tipo_usuario != 0:
            return Response({'error': 'Este flujo es exclusivo para clientes.'}, status=403)
        current = request.data.get('current_password', '')
        if not isinstance(current, str) or not request.user.check_password(current):
            return Response({'current_password': 'La contraseña actual no es correcta.'}, status=400)
        serializer = NewPasswordSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        if current == serializer.validated_data['new_password']:
            return Response({'new_password': 'Elige una contraseña diferente a la actual.'}, status=400)
        with transaction.atomic():
            user = Credenciales.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(current):
                return Response({'current_password': 'La contraseña actual no es correcta.'}, status=400)
            user.set_password(serializer.validated_data['new_password'])
            user.password_version += 1
            user.save(update_fields=['password', 'password_version'])
            Token.objects.filter(user=user).delete()
        return Response({'message': 'Contraseña actualizada. Vuelve a iniciar sesión.'})


class RecoveryIPThrottle(SimpleRateThrottle):
    rate = '10/hour'

    def get_cache_key(self, request, view):
        # Nginx overwrites X-Real-IP; X-Forwarded-For may include client-controlled entries.
        raw = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')
        try:
            raw = str(ipaddress.ip_address(raw))
        except ValueError:
            raw = request.META.get('REMOTE_ADDR', '')
        ident = salted_hmac('reset-ip', raw).hexdigest()
        return 'reset:ip:' + ident


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RecoveryIPThrottle]

    def post(self, request):
        try:
            raw = request.data.get('email', '')
            email = serializers.EmailField(max_length=254).run_validation(raw.strip() if isinstance(raw, str) else raw).lower()
        except serializers.ValidationError:
            return Response({'email': 'Ingresa un correo válido.'}, status=400)
        password_recovery.request_reset(email)
        return Response(RESET_RESPONSE, headers={'Cache-Control': 'no-store'})


class ResetLinkSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)


def reset_user(data, lock=False):
    fields = ResetLinkSerializer(data=data)
    if not fields.is_valid():
        return None
    try:
        uid = force_str(urlsafe_base64_decode(fields.validated_data['uid']))
        query = Credenciales.objects.select_for_update() if lock else Credenciales.objects
        user = query.get(pk=uid)
        if password_recovery.eligible(user) and password_recovery.tokens.check_token(user, fields.validated_data['token']):
            return user
    except (TypeError, ValueError, OverflowError, UnicodeError, Credenciales.DoesNotExist):
        pass
    return None


class ValidatePasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        valid = reset_user(request.data) is not None
        return Response({'valid': True} if valid else {'error': 'El enlace no es válido o ha expirado.'},
                        status=200 if valid else 400, headers={'Cache-Control': 'no-store'})


class ConfirmPasswordResetView(ValidatePasswordResetView):
    def post(self, request):
        with transaction.atomic():
            user = reset_user(request.data, lock=True)
            if not user:
                return Response({'error': 'El enlace no es válido o ha expirado.'}, status=400)
            serializer = NewPasswordSerializer(data=request.data, context={'user': user})
            serializer.is_valid(raise_exception=True)
            user.set_password(serializer.validated_data['new_password'])
            user.password_version += 1
            user.password_reset_version += 1
            user.save(update_fields=['password', 'password_version', 'password_reset_version'])
            Token.objects.filter(user=user).delete()
        logger.info('password_reset password_changed user=%s sessions_revoked=true', user.pk)
        return Response({'message': 'Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.'},
                        headers={'Cache-Control': 'no-store'})
