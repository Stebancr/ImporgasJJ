"""TCC REST contracts transcribed from the supplied manuals/plugin v2.5.1.

No tracking/cancellation/webhook contract or remote idempotency guarantee was
provided. Never invent them and never retry an uncertain dispatch automatically.
"""
import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
import requests
from django.conf import settings

logger = logging.getLogger(__name__)
QUOTE_PATH = '/api/clientes/tarifas/v5/consultarliquidacion'
DISPATCH_PATH = '/api/clientes/remesas/grabardespacho8'


class TCCError(Exception):
    def __init__(self, message, *, code='unavailable', retryable=False, uncertain=False):
        super().__init__(message)
        self.code, self.retryable, self.uncertain = code, retryable, uncertain


def safe_document_url(value):
    if not isinstance(value, str) or len(value) > 2000:
        return ''
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        return ''
    # No automatic fetching and no redirects to arbitrary or internal hosts.
    if (url.scheme == 'https' and url.hostname in {'somos.tcc.com.co', 'testsomos.tcc.com.co', 'www.tcc.com.co'}
            and port in (None, 443) and not url.username and not url.password and not url.fragment):
        return value
    return ''


class TCCClient:
    def __init__(self):
        env = settings.TCC_API_ENVIRONMENT
        if env == 'development':
            self.base, self.token = 'https://testsomos.tcc.com.co', settings.TCC_API_TOKEN
        elif env == 'production' and settings.TCC_PRODUCTION_APPROVED:
            self.base, self.token = 'https://somos.tcc.com.co', settings.TCC_PRODUCTION_API_TOKEN
        else:
            raise TCCError('El ambiente TCC no está autorizado.', code='configuration')
        self.token = self.token.strip()
        if not self.token:
            raise TCCError('Falta configurar la credencial TCC en el backend.', code='configuration')

    def _post(self, path, payload, dispatch=False):
        try:
            response = requests.post(self.base + path, json=payload, headers={
                'AccessToken': self.token, 'Content-Type': 'application/json',
            }, timeout=(5, 45 if dispatch else 12), allow_redirects=False)
        except requests.ConnectTimeout:
            raise TCCError('No fue posible conectar con TCC.', code='connect_timeout', retryable=True) from None
        except requests.RequestException as exc:
            logger.warning('TCC operation=%s failure=%s', 'dispatch' if dispatch else 'quote', type(exc).__name__)
            raise TCCError('TCC no confirmó la solicitud. Intenta cotizar nuevamente.' if not dispatch else
                           'TCC no confirmó la creación; verifica con TCC antes de reintentar.',
                           uncertain=dispatch, retryable=not dispatch) from None
        if response.status_code != 200:
            logger.warning('TCC operation=%s http_status=%s', 'dispatch' if dispatch else 'quote', response.status_code)
            raise TCCError('TCC no pudo procesar la solicitud.', code='http_' + str(response.status_code),
                           uncertain=dispatch and response.status_code >= 500,
                           retryable=response.status_code == 429 or (not dispatch and response.status_code >= 500))
        try:
            data = response.json()
        except (ValueError, TypeError):
            raise TCCError('TCC devolvió una respuesta no válida.', uncertain=dispatch) from None
        if not isinstance(data, dict):
            raise TCCError('TCC devolvió una respuesta no válida.', uncertain=dispatch)
        return data

    def quote(self, payload):
        data = self._post(QUOTE_PATH, payload)
        if str(data.get('codigoResultado')) != '0':
            # Provider messages can echo credentials/PII: retain only result code.
            provider_code = str(data.get('codigoResultado', ''))
            logger.warning('TCC quote rejected provider_code=%s', provider_code if provider_code.lstrip('-').isdigit() else 'unknown')
            if 'no existe tarifa para la ruta solicitada' in str(data.get('mensajeResultado', '')).lower():
                raise TCCError('TCC no tiene tarifa configurada para esta ruta y cuenta. Contacta al asesor.', code='route_not_configured')
            raise TCCError('TCC no pudo cotizar este envío. Revisa origen, destino y paquetes.', code='quote_rejected')
        try:
            amount = Decimal(str(data['total']['totaldespacho']))
            if not amount.is_finite() or amount < 0 or amount > Decimal('9999999999.99'):
                raise ValueError()
            return amount.quantize(Decimal('0.01'))
        except (KeyError, TypeError, InvalidOperation, ValueError):
            raise TCCError('La tarifa recibida de TCC no es válida.', code='invalid_rate') from None

    def dispatch(self, payload):
        if not settings.TCC_DISPATCH_ENABLED:
            raise TCCError('La creación de despachos TCC está deshabilitada.', code='dispatch_disabled')
        data = self._post(DISPATCH_PATH, payload, dispatch=True)
        rows = data.get('remesas')
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise TCCError('TCC no confirmó la remesa.', uncertain=True)
        if str(rows[0].get('codigoresultado')) != '0':
            raise TCCError('TCC rechazó la remesa. Revisa la configuración del envío.', code='dispatch_rejected')
        number = str(rows[0].get('numeroremesa') or '')
        if not number.isdigit() or len(number) > 100:
            raise TCCError('TCC no devolvió un número de remesa válido.', uncertain=True)
        return {'waybill': number, 'pickup_number': str(data.get('numerorecogida') or '')[:100],
                'documents': {key: url for key, field in [('label', 'urlrotulos'), ('relation', 'urlrelacionenvio'), ('waybill', 'urlremesa')]
                              if (url := safe_document_url(data.get(field, ''))) }}
