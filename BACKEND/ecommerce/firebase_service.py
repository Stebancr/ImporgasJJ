import logging
import os
from threading import Lock

from django.conf import settings

from .models import FCMDeviceToken


logger = logging.getLogger(__name__)
_firebase_lock = Lock()


def _firebase_app():
    """Inicializa Firebase Admin una sola vez, exclusivamente desde backend."""
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return firebase_admin.get_app()

    with _firebase_lock:
        if firebase_admin._apps:
            return firebase_admin.get_app()

        credentials_file = getattr(settings, 'FIREBASE_CREDENTIALS_FILE', '')
        if credentials_file:
            credential = credentials.Certificate(credentials_file)
        else:
            project_id = getattr(settings, 'FIREBASE_PROJECT_ID', '')
            client_email = getattr(settings, 'FIREBASE_CLIENT_EMAIL', '')
            private_key = getattr(settings, 'FIREBASE_PRIVATE_KEY', '')
            if not all((project_id, client_email, private_key)):
                raise RuntimeError('Firebase Admin no está configurado.')
            credential = credentials.Certificate({
                'type': 'service_account',
                'project_id': project_id,
                'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
                'private_key': private_key.replace('\\n', '\n'),
                'client_email': client_email,
                'client_id': os.getenv('FIREBASE_CLIENT_ID', ''),
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_CERT_URL', ''),
            })
        return firebase_admin.initialize_app(credential)


def send_push_to_user(user, title, body, data=None):
    """Envía a todos los dispositivos activos y desactiva tokens rechazados por FCM."""
    from firebase_admin import messaging

    app = _firebase_app()
    result = {'sent': 0, 'failed': 0, 'deactivated': 0}
    safe_data = {str(key): str(value) for key, value in (data or {}).items()}
    invalid_errors = (messaging.UnregisteredError, messaging.SenderIdMismatchError)

    for device in FCMDeviceToken.objects.filter(user=user, is_active=True).iterator():
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=safe_data,
            token=device.token,
        )
        try:
            messaging.send(message, app=app)
            result['sent'] += 1
            if device.last_error:
                device.last_error = ''
                device.save(update_fields=['last_error', 'updated_at'])
        except invalid_errors as exc:
            device.is_active = False
            device.last_error = exc.__class__.__name__
            device.save(update_fields=['is_active', 'last_error', 'updated_at'])
            result['failed'] += 1
            result['deactivated'] += 1
        except Exception as exc:
            logger.warning('Error temporal enviando notificación FCM al token %s: %s', device.pk, exc.__class__.__name__)
            device.last_error = exc.__class__.__name__[:255]
            device.save(update_fields=['last_error', 'updated_at'])
            result['failed'] += 1
    return result
