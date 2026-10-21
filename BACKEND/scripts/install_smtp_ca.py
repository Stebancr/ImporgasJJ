"""Validate an explicitly authorized, fingerprint-pinned development CA before installation.

No download/discovery, no TLS verification overrides, no private keys accepted.
"""
import argparse
import datetime
import hashlib
import re
import ssl
import subprocess
from pathlib import Path


def validate_certificate(path, expected):
    expected = expected.replace(':', '').strip().upper()
    if not re.fullmatch(r'[0-9A-F]{64}', expected):
        raise ValueError('Provide the independently verified SHA-256 fingerprint.')
    raw = Path(path).read_text(encoding='ascii').strip()
    if not re.fullmatch(r'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----', raw):
        raise ValueError('Exactly one public PEM certificate is required; keys and bundles are rejected.')
    actual = hashlib.sha256(ssl.PEM_cert_to_DER_cert(raw)).hexdigest().upper()
    if actual != expected:
        raise ValueError('CA fingerprint mismatch; refusing installation.')
    def openssl(*args):
        result = subprocess.run(['openssl', 'x509', '-noout', *args], input=raw, text=True, capture_output=True, check=True)
        return result.stdout
    constraints = openssl('-ext', 'basicConstraints,keyUsage')
    if 'CA:TRUE' not in constraints:
        raise ValueError('Certificate is not a CA.')
    if 'X509v3 Key Usage' in constraints and 'Certificate Sign' not in constraints:
        raise ValueError('Certificate does not permit certificate signing.')
    dates = dict(line.split('=', 1) for line in openssl('-dates').splitlines())
    now = datetime.datetime.now(datetime.timezone.utc)
    for label, lower in [('notBefore', True), ('notAfter', False)]:
        stamp = datetime.datetime.strptime(dates[label], '%b %d %H:%M:%S %Y GMT').replace(tzinfo=datetime.timezone.utc)
        if (lower and now < stamp) or (not lower and now > stamp):
            raise ValueError('CA is outside its validity period.')
    result = subprocess.run(['openssl', 'verify', '-check_ss_sig', '-CAfile', str(path), str(path)], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('CA self-signature/chain verification failed.')
    return raw + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--certificate', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--install', action='store_true')
    options = parser.parse_args()
    try:
        pem = validate_certificate(options.certificate, options.sha256)
        if options.install:
            Path('/usr/local/share/ca-certificates/smtp-local-root.crt').write_text(pem, encoding='ascii')
        print('Authorized CA fingerprint, validity, constraints and signature verified.')
    except (ValueError, OSError, subprocess.SubprocessError):
        parser.exit(1, 'CA validation failed; refusing installation.\n')


if __name__ == '__main__':
    main()
