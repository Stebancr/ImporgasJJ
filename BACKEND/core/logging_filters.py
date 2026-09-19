"""Filtros que impiden registrar secretos recibidos en query strings."""

import logging
import re


_WEBHOOK_TOKEN = re.compile(
    r'(?i)(hub(?:\.|_)verify_token=)[^&\s"?]+',
)


def redact_webhook_tokens(value):
    return _WEBHOOK_TOKEN.sub(r'\1[REDACTED]', str(value))


class RedactWebhookSecretsFilter(logging.Filter):
    """Sanitiza la línea ya formateada por Django/Daphne antes de emitirla."""

    def filter(self, record):
        message = record.getMessage()
        redacted = redact_webhook_tokens(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
