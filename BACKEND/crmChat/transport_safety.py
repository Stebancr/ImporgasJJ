"""Single safety boundary for provider IO; simulation never contacts a provider."""
from django.conf import settings


def assert_provider_io_allowed():
    if getattr(settings, 'CRM_TEST_MODE', False) or not getattr(settings, 'CRM_EXTERNAL_SEND_ENABLED', True):
        from crmChat.apps.meta.services import MetaAPIError
        raise MetaAPIError('CRM_EXTERNAL_IO_DISABLED: conexión externa bloqueada por configuración.')


def simulated_message_id(message):
    # Stable across retries; namespaced so it cannot be mistaken for a provider ID.
    return f'crm-simulated:{message.session.channel}:{message.pk}'
