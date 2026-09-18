"""Customer account actions backed by Django password validation and reset tokens."""
import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import Credenciales

logger = logging.getLogger(__name__)
RESET_RESPONSE = {'message': 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.'}


class NewPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Las contraseñas no coinciden.'})
        try:
            validate_password(attrs['new_password'], user=self.context.get('user'))
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


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset_request'

    def post(self, request):
        email = request.data.get('email', '')
        if not isinstance(email, str) or not email.strip():
            return Response({'email': 'Ingresa un correo válido.'}, status=400)
        try:
            email = serializers.EmailField(max_length=254).run_validation(email.strip()).lower()
        except serializers.ValidationError:
            return Response({'email': 'Ingresa un correo válido.'}, status=400)
        user = (Credenciales.objects.select_related('usuario_rel')
                .filter(Q(usuario_rel__correo__iexact=email) | Q(usuario__iexact=email),
                        tipo_usuario=0, estado=1).first())
        if user and user.usuario_rel and user.usuario_rel.correo:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            url = request.build_absolute_uri(f'/restablecer-contrasena/{uid}/{token}')
            try:
                send_mail(
                    'Restablece tu contraseña de ImporGas JJ',
                    f'Solicitaste restablecer tu contraseña. Usa este enlace durante una hora:\n\n{url}\n\nSi no fuiste tú, ignora este correo.',
                    settings.DEFAULT_FROM_EMAIL, [user.usuario_rel.correo], fail_silently=False,
                    connection=get_connection(timeout=min(settings.EMAIL_TIMEOUT, 10)),
                )
            except Exception:
                logger.exception('No se pudo enviar el correo de recuperación al usuario %s', user.pk)
        return Response(RESET_RESPONSE)


class ConfirmPasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        try:
            uid = force_str(urlsafe_base64_decode(request.data.get('uid', '')))
            user = Credenciales.objects.get(pk=uid, tipo_usuario=0, estado=1)
        except (TypeError, ValueError, OverflowError, Credenciales.DoesNotExist):
            return Response({'error': 'El enlace no es válido o ha expirado.'}, status=400)
        with transaction.atomic():
            user = Credenciales.objects.select_for_update().get(pk=user.pk)
            if not default_token_generator.check_token(user, request.data.get('token', '')):
                return Response({'error': 'El enlace no es válido o ha expirado.'}, status=400)
            serializer = NewPasswordSerializer(data=request.data, context={'user': user})
            serializer.is_valid(raise_exception=True)
            user.set_password(serializer.validated_data['new_password'])
            user.password_version += 1
            user.save(update_fields=['password', 'password_version'])
            Token.objects.filter(user=user).delete()
        return Response({'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'})
