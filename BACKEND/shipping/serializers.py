from decimal import Decimal
from django.conf import settings
from rest_framework import serializers
from .models import ProductShippingProfile, Shipment


PROFILE_FIELDS = ['requires_shipping', 'weight_kg', 'height_cm', 'width_cm', 'length_cm',
                  'packages_per_unit', 'declared_value', 'packaging_code', 'fragile']


class ProductShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductShippingProfile
        fields = PROFILE_FIELDS


def quote_data(quote):
    return {'id': str(quote.pk), 'carrier': 'TCC', 'tcc_rate': str(quote.tcc_rate),
            'surcharge': str(quote.surcharge), 'total': str(quote.total),
            'subtotal': quote.snapshot['subtotal'], 'order_total': str(quote.total + Decimal(quote.snapshot['subtotal'])),
            'expires_at': quote.expires_at, 'package_count': len(quote.snapshot['packages']),
            'real_kg': quote.snapshot['real_kg'], 'volumetric_kg': quote.snapshot['volumetric_kg'],
            'billable_kg': quote.snapshot['billable_kg']}


def shipment_data(order, admin=False):
    try:
        shipment = order.shipment
    except Shipment.DoesNotExist:
        return None
    result = {'id': shipment.pk, 'carrier': 'TCC', 'state': shipment.state, 'state_label': shipment.get_state_display(),
        'waybill': shipment.waybill, 'last_update': shipment.updated_at, 'last_sync_at': shipment.last_sync_at,
        'tracking_url': ('https://www.tcc.com.co/rastreo?tipo=RE&documento='+shipment.waybill) if shipment.waybill else '',
        'tracking_api_available': False,
        'history': [{'state': e.state, 'description': e.description, 'created_at': e.created_at}
                    for e in shipment.events.all()]}
    if order.status == 'cancelled' and shipment.state == 'awaiting_payment':
        result['state_label'] = 'Orden cancelada localmente; despacho no solicitado'
    if admin:
        quote = shipment.quote
        result.update({'account_type': quote.account_type, 'account': quote.snapshot['account'],
            'real_kg': quote.snapshot['real_kg'], 'volumetric_kg': quote.snapshot['volumetric_kg'],
            'billable_kg': quote.snapshot['billable_kg'], 'tcc_rate': str(quote.tcc_rate),
            'surcharge': str(quote.surcharge), 'charged': str(quote.total),
            'last_error': shipment.last_error, 'documents': shipment.document_urls,
            'retry_allowed': shipment.state == 'error' and settings.TCC_SHIPPING_ENABLED and settings.TCC_DISPATCH_ENABLED,
            'environment': quote.environment})
    return result
