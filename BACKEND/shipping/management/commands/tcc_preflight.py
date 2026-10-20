"""Read-only configuration/product audit. Never prints tokens or customer data."""
import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from ecommerce.models import Product, ProductImage, OrderItem
from shipping.rollout import missing_fields
from shipping.catalog import city


class Command(BaseCommand):
    help = 'Auditar TCC y productos sin modificar registros ni llamar al proveedor.'

    def add_arguments(self, parser):
        parser.add_argument('--production', action='store_true')
        parser.add_argument('--strict', action='store_true')

    def handle(self, *args, **options):
        missing = []
        required = {'TCC_PRODUCTION_API_TOKEN':settings.TCC_PRODUCTION_API_TOKEN,
                    'TCC_PQT_ACCOUNT':settings.TCC_PQT_ACCOUNT, 'TCC_MSJ_ACCOUNT':settings.TCC_MSJ_ACCOUNT,
                    'TCC_ORIGIN_CITY_CODE':settings.TCC_ORIGIN_CITY_CODE}
        required.update({'TCC_SENDER_'+field.upper():value for field,value in settings.TCC_SENDER.items()})
        missing.extend(key for key,value in required.items() if not str(value or '').strip())
        invalid = []
        if options['production']:
            # Account defaults in source/examples are not proof of production authorization.
            explicit = ['TCC_PRODUCTION_BASE_URL','TCC_API_ENVIRONMENT','TCC_PQT_ACCOUNT','TCC_MSJ_ACCOUNT']
            missing.extend(key for key in explicit if not os.environ.get(key) and key not in missing)
            if settings.TCC_API_ENVIRONMENT != 'production': invalid.append('TCC_API_ENVIRONMENT')
            if settings.TCC_PRODUCTION_BASE_URL.rstrip('/') != 'https://somos.tcc.com.co': invalid.append('TCC_PRODUCTION_BASE_URL')
            if not settings.TCC_PRODUCTION_APPROVED: invalid.append('TCC_PRODUCTION_APPROVED')
            if settings.TCC_PRODUCTION_API_TOKEN and settings.TCC_API_TOKEN == settings.TCC_PRODUCTION_API_TOKEN: invalid.append('TCC_PRODUCTION_API_TOKEN_equals_development')
        if not city(settings.TCC_ORIGIN_CITY_CODE): invalid.append('TCC_ORIGIN_CITY_CODE')
        if settings.TCC_SENDER.get('document_type') not in ('NIT','CC'): invalid.append('TCC_SENDER_DOCUMENT_TYPE')
        products = list(Product.objects.select_related('shipping_profile'))
        fields = ('weight_kg','height_cm','width_cm','length_cm','packages_per_unit','declared_value','packaging_code')
        deficits = {field:sum(field in missing_fields(getattr(p,'shipping_profile',None)) for p in products) for field in fields}
        result = {'products':len(products), 'active':sum(p.is_available for p in products),
            'inactive':sum(not p.is_available for p in products),
            'with_images':ProductImage.objects.values('product_id').distinct().count(),
            'used_in_orders':OrderItem.objects.values('product_id').distinct().count(),
            'logistical_status':{state:sum(p.shipping_status==state for p in products) for state in ('ready','incomplete','not_required')},
            'missing_logistics':deficits, 'missing_variables':missing, 'invalid_variables':invalid,
            'quote_enabled':settings.TCC_SHIPPING_ENABLED, 'admin_only':settings.TCC_ADMIN_ONLY,
            'dispatch_enabled':settings.TCC_DISPATCH_ENABLED,
            'requires_shipping_confirmation':settings.TCC_REQUIRE_CONFIRMED_SHIPPING,
            'timeouts_seconds':{'connect':5,'quote':12,'dispatch':45}, 'automatic_quote_retries':0}
        self.stdout.write(json.dumps(result, sort_keys=True))
        if options['strict'] and (missing or invalid):
            raise CommandError('Configuración TCC incompleta; revisa los nombres de variables indicados, sin publicar sus valores.')
