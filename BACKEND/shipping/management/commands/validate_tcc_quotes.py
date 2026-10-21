"""Read-only, sandbox-only national rate matrix; never dispatches or writes DB."""
import json
from unittest.mock import patch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from shipping.catalog import city
from shipping.services import quotation_payload
from shipping.tcc import TCCClient, TCCError, QUOTE_PATH
import requests


class Command(BaseCommand):
    help = 'Validate sandbox quotes from Cali with synthetic parcels; no database writes.'

    def add_arguments(self, parser):
        parser.add_argument('--sandbox-quote-only', action='store_true')

    def handle(self, *args, **options):
        if not options['sandbox_quote_only'] or settings.TCC_API_ENVIRONMENT not in ('sandbox', 'development'):
            raise CommandError('Requires explicit sandbox/development quotation-only mode.')
        if settings.TCC_ORIGIN_CITY_CODE != '76001000':
            raise CommandError('The official origin must be Cali (76001000).')
        rows = []
        post = requests.post
        for code in ('11001000', '05001000', '08001000', '68001000', '66001000', '76520000'):
            destination = city(code)
            if not destination:
                raise CommandError('Destination absent from the supplied geographic catalogue: '+code)
            for weight in ('2', '6'):
                business = 'MSJ' if weight == '2' else 'PQT'
                account = settings.TCC_MSJ_ACCOUNT if business == 'MSJ' else settings.TCC_PQT_ACCOUNT
                snapshot = {'origin': {'city_code': settings.TCC_ORIGIN_CITY_CODE},
                    'address': {'tcc_city_code': code}, 'account_type': business, 'account': account,
                    'packages': [{'declared_value': '125000', 'weight_kg': weight, 'volumetric_kg': '0.40',
                                  'height_cm': '10', 'width_cm': '10', 'length_cm': '10'}]}
                row = {'origin': '76001000', 'destination': code, 'city': destination['city'],
                    'weight_kg': weight, 'volumetric_kg': '0.40', 'dimensions_cm': [10, 10, 10],
                    'packages': 1, 'declared_value': '125000', 'account_type': business, 'account': account,
                    'business_code': 2 if business == 'MSJ' else 1, 'http_status': None,
                    'coverage': 'unconfirmed', 'rate_COP': None, 'estimated_delivery': None}
                def observed(url, **kwargs):
                    if not url.startswith('https://testsomos.tcc.com.co/') or not url.endswith(QUOTE_PATH):
                        raise CommandError('Blocked non-sandbox or non-quotation request.')
                    response = post(url, **kwargs)
                    row['http_status'] = response.status_code
                    return response
                try:
                    with patch('shipping.tcc.requests.post', side_effect=observed):
                        row.update(rate_COP=str(TCCClient().quote(quotation_payload(snapshot))), coverage='quoted')
                except TCCError as exc:
                    row['error_code'] = exc.code
                rows.append(row)
                self.stdout.write(json.dumps(row, ensure_ascii=False))
        self.stdout.write(json.dumps({'environment': settings.TCC_API_ENVIRONMENT, 'endpoint_path': QUOTE_PATH,
                                     'method': 'POST', 'results': len(rows), 'dispatches': 0}))
