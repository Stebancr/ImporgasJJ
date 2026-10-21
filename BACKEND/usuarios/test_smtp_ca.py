"""Synthetic OpenSSL certificates only; never trusts a host/network certificate."""
import hashlib
import ssl
import subprocess
import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from scripts.install_smtp_ca import validate_certificate


class SMTPRootValidationTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'root.pem'
        self.key = Path(self.temp.name) / 'synthetic.key'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-noenc',
            '-keyout',str(self.key),'-out',str(self.root),'-days','1','-subj','/CN=Synthetic SMTP CA',
            '-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign'],
            check=True,capture_output=True)
        self.fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(self.root.read_text())).hexdigest().upper()

    def test_correct_independently_supplied_fingerprint_and_ca(self):
        self.assertIn('BEGIN CERTIFICATE', validate_certificate(self.root, self.fingerprint))

    def test_wrong_or_missing_fingerprint_rejected(self):
        for value in ['', 'invalid', '0'*64]:
            with self.assertRaises(ValueError):
                validate_certificate(self.root, value)

    def test_private_keys_and_multiple_certificates_rejected(self):
        mixed = Path(self.temp.name) / 'mixed.pem'
        for value in [self.root.read_text()+self.key.read_text(), self.root.read_text()*2, self.key.read_text()]:
            mixed.write_text(value)
            with self.assertRaises(ValueError):
                validate_certificate(mixed, self.fingerprint)

    def test_leaf_certificate_is_never_installed_as_root(self):
        leaf = Path(self.temp.name) / 'leaf.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-noenc',
            '-keyout',str(self.key),'-out',str(leaf),'-days','1','-subj','/CN=synthetic.invalid',
            '-addext','basicConstraints=critical,CA:FALSE'],check=True,capture_output=True)
        digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(leaf.read_text())).hexdigest().upper()
        with self.assertRaises(ValueError):
            validate_certificate(leaf, digest)
