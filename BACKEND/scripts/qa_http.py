"""Fail-closed, local-only certificate probe for the isolated QA database."""
import os
from pathlib import Path
from urllib.parse import urlsplit
import requests


def configuration():
    if (os.environ.get('QA_READ_ONLY_PROBE') != '1'
            or os.environ.get('CRM_TEST_POSTGRES') != '1'
            or os.environ.get('DB_NAME') != 'crm_audit'
            or os.environ.get('DEBUG', '').lower() != 'true'):
        raise SystemExit('Sonda manual desactivada: requiere autorización explícita y entorno QA aislado.')
    base = os.environ.get('QA_BASE_URL', '').rstrip('/')
    url = urlsplit(base)
    if (url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', 'backend', 'general-e2e-backend'}
            or url.username or url.password or url.query or url.fragment or url.path not in ('', '/')):
        raise SystemExit('QA_BASE_URL debe apuntar exclusivamente al servicio local de pruebas.')
    token = os.environ.get('QA_BEARER_TOKEN', '').strip()
    if not token or '\r' in token or '\n' in token or len(token) > 8192:
        raise SystemExit('Configura un QA_BEARER_TOKEN válido de pruebas; valor omitido.')
    return base, token


def certificate_probe():
    base, token = configuration()
    identifier = os.environ.get('QA_TRAINING_ID', '')
    if not identifier.isdigit() or int(identifier) < 1:
        raise SystemExit('Configura QA_TRAINING_ID de una capacitación sintética.')
    try:
        response = requests.get(f'{base}/capacitaciones/certificado/{int(identifier)}/',
                                headers={'Authorization': 'Bearer ' + token}, timeout=15, allow_redirects=False)
    except requests.RequestException:
        raise SystemExit('No se pudo consultar el servicio QA; cabeceras y respuesta omitidas.') from None
    print('QA_CERTIFICATE_HTTP_STATUS', response.status_code)
    if response.status_code == 200:
        data = response.content
        if not data.startswith(b'%PDF') or len(data) > 20 * 1024 * 1024:
            raise SystemExit('El servicio QA no devolvió un PDF válido dentro del límite.')
        output = Path('/tmp/imporgas-legacy-qa')
        output.mkdir(exist_ok=True)
        (output / 'certificate.pdf').write_bytes(data)
        print('QA_CERTIFICATE_SAVED_IN_TEMP_DIRECTORY')
