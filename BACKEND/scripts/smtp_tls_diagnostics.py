"""Read-only SMTP diagnostics. Never authenticates, sends mail or bypasses TLS."""
import datetime
import json
import os
import platform
import re
import smtplib
import socket
import ssl
import subprocess
import sys
from pathlib import Path


def command(args, data=None, timeout=20):
    result = subprocess.run(args, input=data, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def inspect():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from django.conf import settings
    host, port = settings.EMAIL_HOST, settings.EMAIL_PORT
    report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'os': platform.freedesktop_os_release().get('PRETTY_NAME'),
              'python': platform.python_version(), 'openssl': ssl.OPENSSL_VERSION,
              'smtp': {'host': host, 'port': port, 'tls': settings.EMAIL_USE_TLS,
                       'ssl': settings.EMAIL_USE_SSL, 'timeout': settings.EMAIL_TIMEOUT,
                       'EMAIL_HOST_USER_present': bool(settings.EMAIL_HOST_USER),
                       'EMAIL_HOST_PASSWORD_present': bool(settings.EMAIL_HOST_PASSWORD)},
              'environment_present': {key: bool(os.getenv(key)) for key in
                  ['HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy',
                   'SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE']},
              'ssl_paths': ssl.get_default_verify_paths()._asdict(),
              'ca_stats': ssl.create_default_context().cert_store_stats()}
    try:
        import certifi
        report['certifi_bundle'] = certifi.where()
    except ImportError:
        report['certifi_bundle'] = None
    try:
        report['dns'] = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
        with smtplib.SMTP(host, port, timeout=min(settings.EMAIL_TIMEOUT, 15)) as smtp:
            report['tcp_peer'] = smtp.sock.getpeername()[0]
            code, _ = smtp.ehlo('tls-diagnostic.invalid')
            report['smtp_ehlo_code'] = code
            report['starttls_advertised'] = smtp.has_extn('starttls')
            try:
                smtp.starttls(context=ssl.create_default_context())
                report['python_tls'] = {'verified': True, 'version': smtp.sock.version(), 'cipher': smtp.sock.cipher()}
            except ssl.SSLCertVerificationError as exc:
                report['python_tls'] = {'verified': False, 'verify_code': exc.verify_code, 'reason': exc.verify_message}
    except Exception as exc:
        report.setdefault('python_tls', {'verified': False, 'error_class': type(exc).__name__})
    try:
        code, out, err = command(['openssl','s_client','-starttls','smtp','-connect',f'{host}:{port}',
                                 '-servername',host,'-showcerts','-verify_return_error','-verify_hostname',host], data='')
        combined = out + '\n' + err
        report['openssl_exit_code'] = code
        report['openssl_verification'] = [line.strip() for line in combined.splitlines()
            if re.search(r'verify error:|Verification error:|Verify return code:|Verification:|Protocol *:|Cipher *:|New, TLS', line)]
        report['chain'] = []
        for pem in re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', out, re.S):
            _, metadata, _ = command(['openssl','x509','-noout','-subject','-issuer','-dates','-fingerprint','-sha256','-ext','subjectAltName'],pem)
            _, details, _ = command(['openssl','x509','-noout','-text'],pem)
            report['chain'].append({'metadata':metadata.strip().splitlines(),
                'algorithms':[line.strip() for line in details.splitlines() if 'Signature Algorithm:' in line or 'Public Key Algorithm:' in line or 'Public-Key:' in line][:3]})
        report['chain_length'] = len(report['chain'])
    except Exception as exc:
        report['openssl_error_class'] = type(exc).__name__
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return bool(report.get('python_tls', {}).get('verified') and report.get('openssl_exit_code') == 0)


if __name__ == '__main__':
    sys.exit(0 if inspect() else 1)
