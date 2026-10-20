from django.conf import settings
from rest_framework import serializers
from .models import ProductShippingProfile, Shipment
from ecommerce.pricing import totals


PROFILE_FIELDS = ['requires_shipping', 'weight_kg', 'height_cm', 'width_cm', 'length_cm',
                  'packages_per_unit', 'declared_value', 'declared_value_from_price', 'packaging_code', 'fragile']


class ProductShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductShippingProfile
        fields = PROFILE_FIELDS


def quote_data(quote):
    return {'id': str(quote.pk), **calculation_data(quote.snapshot, quote.tcc_rate, quote.surcharge, quote.total,
            quote.created_at, quote.expires_at), 'approximate': False}


def calculation_data(snapshot, rate, surcharge, shipping, created_at, expires_at):
    breakdown = totals(snapshot['subtotal'], shipping)
    return {'carrier': 'TCC', 'tcc_rate': str(rate), 'surcharge': str(surcharge), 'total': str(shipping),
            'subtotal': str(breakdown['subtotal']), 'discounts': str(breakdown['discounts']), 'taxes': str(breakdown['taxes']),
            'order_total': str(breakdown['total']), 'expires_at': expires_at, 'quoted_at': created_at,
            'estimated_delivery': None, 'carrier_quote_id': None,
            'destination': {key: snapshot['address'][key] for key in ('city', 'department')},
            'package_count': len(snapshot['packages']), 'real_kg': snapshot['real_kg'],
            'volumetric_kg': snapshot['volumetric_kg'], 'billable_kg': snapshot['billable_kg']}


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
