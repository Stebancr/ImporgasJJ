from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from usuarios.models import AuthSession, PersistentTokenVersion
from .session_security import current_version


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.auth, 'get'):
            AuthSession.objects.filter(pk=request.auth.get('session_id'), user=request.user).update(revoked_at=timezone.now())
        elif isinstance(request.auth, Token):
            metadata = PersistentTokenVersion.objects.filter(token=request.auth).first()
            if metadata:
                AuthSession.objects.filter(pk=metadata.session_id).update(revoked_at=timezone.now())
            request.auth.delete()
        if hasattr(request, 'session'):
            from django.contrib.auth import logout
            logout(request)
        return Response(status=204)


class PersonalTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, Token):
            return Response({'code': 'INTERACTIVE_LOGIN_REQUIRED'}, status=403)
        with transaction.atomic():
            # Serialize rotations for this account. Never resurrect an old token.
            type(request.user).objects.select_for_update().get(pk=request.user.pk)
            old = PersistentTokenVersion.objects.filter(token__user=request.user).first()
            if old:
                AuthSession.objects.filter(pk=old.session_id).update(revoked_at=timezone.now())
            Token.objects.filter(user=request.user).delete()
            token = Token.objects.create(user=request.user)
            session = AuthSession.objects.create(user=request.user, global_auth_version=current_version(),
                password_version=request.user.password_version, expires_at=timezone.now()+timedelta(days=30), credential_type='drf')
            PersistentTokenVersion.objects.create(token=token, global_auth_version=session.global_auth_version,
                password_version=request.user.password_version, session=session)
        return Response({'token': token.key}, headers={'Cache-Control': 'no-store'})
