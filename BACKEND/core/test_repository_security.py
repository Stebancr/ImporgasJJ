import contextlib
import io
import os
import re
import time
from pathlib import Path
from unittest.mock import patch
import jwt
from django.conf import settings
from django.test import SimpleTestCase


class LegacyProbeSafetyTests(SimpleTestCase):
    def test_manual_scripts_do_not_embed_jwt_credentials(self):
        root = Path(settings.BASE_DIR) / 'scripts'
        for relative in ('decode_jwt.py', 'decode_jwt copy.py', 'pruebas/probar_certificado.py',
                         'pruebas/test_certificado.py', 'pruebas/test_cargar_csv.py', 'test_perfil_capacitacion.py'):
            source = (root / relative).read_text(encoding='utf-8-sig')
            self.assertIsNone(re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', source), relative)

    @patch.dict(os.environ, {}, clear=True)
    @patch('scripts.qa_http.requests.get')
    def test_probe_fails_closed_without_explicit_isolated_environment(self, request):
        from scripts.qa_http import certificate_probe
        with self.assertRaises(SystemExit):
            certificate_probe()
        request.assert_not_called()

    @patch('scripts.qa_http.requests.get')
    def test_probe_rejects_production_or_remote_destinations(self, request):
        from scripts.qa_http import configuration
        env = {'QA_READ_ONLY_PROBE': '1', 'CRM_TEST_POSTGRES': '1', 'DB_NAME': 'crm_audit',
               'DEBUG': 'True', 'QA_BEARER_TOKEN': 'synthetic-test-value'}
        for target in ('https://www.imporgasjj.com', 'http://external.invalid', 'http://user:password@backend'):
            with patch.dict(os.environ, {**env, 'QA_BASE_URL': target}, clear=True), self.assertRaises(SystemExit):
                configuration()
        with patch.dict(os.environ, {**env, 'QA_BASE_URL': 'http://backend', 'DB_NAME': 'production'}, clear=True), self.assertRaises(SystemExit):
            configuration()
        request.assert_not_called()

    def test_token_metadata_does_not_log_token_or_private_identity(self):
        from scripts.jwt_metadata import main
        token = jwt.encode({'exp': int(time.time()) + 60, 'user_id': 'private-identity-marker', 'token_type': 'access'},
                           'qa-only-' * 8, algorithm='HS256')
        output = io.StringIO()
        with patch.dict(os.environ, {'QA_BEARER_TOKEN': token}), contextlib.redirect_stdout(output):
            main()
        self.assertNotIn(token, output.getvalue())
        self.assertNotIn('private-identity-marker', output.getvalue())
        self.assertIn('"signature_verified": false', output.getvalue())

    @patch.dict(os.environ, {}, clear=True)
    def test_metadata_requires_explicit_token(self):
        from scripts.jwt_metadata import main
        with self.assertRaises(SystemExit):
            main()
