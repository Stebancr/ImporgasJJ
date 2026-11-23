from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from .session_security import current_version, validate_django_session


@receiver(user_logged_in, dispatch_uid='stamp_auth_session_versions')
def stamp_session(sender, request, user, **kwargs):
    from usuarios.models import AuthSession
    request.session['global_auth_version'] = current_version()
    request.session['password_version'] = user.password_version
    request.session['credential_type'] = 'django_session'
    request.session['issued_at'] = int(timezone.now().timestamp())
    session = AuthSession.objects.create(user=user, global_auth_version=request.session['global_auth_version'],
        password_version=user.password_version, expires_at=request.session.get_expiry_date(), credential_type='django_session')
    request.session['auth_session_id'] = str(session.pk)


@receiver(user_logged_out, dispatch_uid='revoke_logged_out_session')
def revoke_session(sender, request, user, **kwargs):
    from usuarios.models import AuthSession
    if request and request.session.get('auth_session_id'):
        AuthSession.objects.filter(pk=request.session['auth_session_id']).update(revoked_at=timezone.now())


class VersionedSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                validate_django_session(request.user, request.session)
            except AuthenticationFailed:
                logout(request)
        return self.get_response(request)
