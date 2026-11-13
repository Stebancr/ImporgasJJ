"""Run mocked CRM contracts with fail-closed network access, including threads.

Only the isolated Compose database/Redis and loopback are reachable. Adapter
contract tests may opt into mocked transports; real sockets remain forbidden.
"""
import socket
from unittest.mock import patch

from django.test.runner import DiscoverRunner
from django.test import override_settings


class AuditRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        allowed = {'127.0.0.1', '::1'}
        for host in ('database', 'redis'):
            allowed.update(row[4][0] for row in socket.getaddrinfo(host, None))

        def checked(sock, address, original):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in allowed:
                raise AssertionError('CRM_AUDIT_EXTERNAL_NETWORK_BLOCKED')
            return original(sock, address)

        with override_settings(CRM_EXTERNAL_SEND_ENABLED=True, CRM_TEST_MODE=False,
                               CRM_ASYNC_OUTBOUND_ENABLED=False,
                               TEST_RUNNER='crmChat.audit_runner.AuditRunner'), \
                patch.object(socket.socket, 'connect', lambda s, a: checked(s, a, original_connect)), \
                patch.object(socket.socket, 'connect_ex', lambda s, a: checked(s, a, original_connect_ex)):
            return super().run_tests(*args, **kwargs)
