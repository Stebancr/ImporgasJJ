"""Authoritative packaging, quotation and frozen order shipping snapshots."""
import hashlib
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from collections import Counter

from django.conf import settings
from django.db import transaction, connection
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ecommerce.models import Product, CartItem, UserAddress, Order, OrderItem
from .models import ProductShippingProfile, ShippingQuote, Shipment, ShipmentEvent
from .catalog import city
from .tcc import TCCClient, TCCError

logger = logging.getLogger(__name__)
CENT = Decimal('0.01')


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def origin():
    if not city(settings.TCC_ORIGIN_CITY_CODE):
        raise TCCError('Configura el código de origen TCC en el backend.', code='configuration')
    sender = dict(settings.TCC_SENDER)
    if sender.get('document_type') and sender['document_type'] not in ('CC', 'NIT'):
        raise TCCError('Configura el tipo de documento del remitente según el contrato TCC (CC o NIT).', code='configuration')
    # Quotation only requires the origin city; sender identity is required
    # before dispatch, not collected from the buyer at checkout.
    if settings.TCC_DISPATCH_ENABLED and any(not sender.get(field) for field in ('name', 'document_type', 'document', 'address', 'phone')):
        raise TCCError('Completa los datos del remitente TCC en el backend.', code='configuration')
    return {**sender, 'city_code': settings.TCC_ORIGIN_CITY_CODE}


def address_snapshot(user, data):
    if data.get('address_id'):
        address = UserAddress.objects.filter(pk=data['address_id'], user=user).first()
        if address is None:
            raise ValidationError({'address_id': 'Dirección no disponible para este usuario.'})
        result = {field: getattr(address, field) for field in
                  ('recipient_name', 'phone', 'address', 'city', 'department', 'postal_code', 'tcc_city_code',
                   'complement', 'neighborhood', 'delivery_instructions')}
    else:
        result = {field: str(data.get(source) or '').strip() for field, source in {
            'recipient_name': 'customer_name', 'phone': 'customer_phone', 'address': 'shipping_address',
            'city': 'city', 'department': 'department', 'postal_code': 'postal_code', 'tcc_city_code': 'tcc_city_code',
            'complement': 'complement', 'neighborhood': 'neighborhood', 'delivery_instructions': 'delivery_instructions',
        }.items()}
    result['email'] = str(data.get('customer_email') or '').strip()
    if any(not result[field] for field in ('recipient_name', 'phone', 'address', 'city', 'department', 'email', 'tcc_city_code')):
        raise ValidationError({'address': 'Completa destinatario, contacto, dirección y ciudad TCC.'})
    destination = city(result['tcc_city_code'])
    if not destination or result['city'] != destination['city'] or result['department'] != destination['department']:
        raise ValidationError({'tcc_city_code': 'Selecciona una ciudad del catálogo TCC que corresponda al departamento.'})
    return result


def shipping_snapshot(user, items, data):
    counts = Counter()
    for item in items:
        counts[item['product_id']] += item['quantity']
    cart = dict(CartItem.objects.filter(user=user).values_list('product_id', 'quantity'))
    if dict(counts) != cart or not counts:
        raise ValidationError({'items': 'El carrito cambió. Actualízalo antes de cotizar.'})
    products = {p.pk: p for p in Product.objects.filter(pk__in=counts, is_available=True).select_related('shipping_profile')}
    if len(products) != len(counts):
        raise ValidationError({'items': 'Uno de los productos no está disponible.'})
    packages, lines = [], []
    subtotal = Decimal('0')
    for pk, qty in sorted(counts.items()):
        product = products[pk]
        profile = getattr(product, 'shipping_profile', None)
        if profile is None:
            raise ValidationError({'items': f'El producto {pk} no tiene configuración de transporte. Contacta al asesor.'})
        subtotal += product.price * qty
        lines.append({'product_id': pk, 'quantity': qty, 'unit_price': str(product.price),
                      'shipping_revision': profile.updated_at.isoformat()})
        if not profile.requires_shipping:
            continue
        fields = ('weight_kg', 'height_cm', 'width_cm', 'length_cm', 'declared_value')
        if any(getattr(profile, field) is None or getattr(profile, field) <= 0 for field in fields):
            raise ValidationError({'items': f'Faltan peso, dimensiones o valor declarado del producto {pk}.'})
        count = qty * profile.packages_per_unit
        if count < 1 or len(packages) + count > 100:
            raise ValidationError({'items': 'El envío supera el límite operativo de 100 paquetes. Contacta al asesor.'})
        for _ in range(count):
            volumetric = money(profile.length_cm * profile.width_cm * profile.height_cm * Decimal('0.0004'))
            packages.append({**{field: str(getattr(profile, field)) for field in fields},
                'volumetric_kg': str(volumetric), 'product_id': pk, 'packaging_code': profile.packaging_code,
                'fragile': profile.fragile})
    real = sum((Decimal(p['weight_kg']) for p in packages), Decimal('0'))
    volume = sum((Decimal(p['volumetric_kg']) for p in packages), Decimal('0'))
    # Each unit stays a separate box. Never add lengths/widths/heights.
    business = 'PQT' if real > 5 or volume > 5 else 'MSJ'
    snapshot = {'items': lines, 'packages': packages, 'subtotal': str(money(subtotal)),
        'real_kg': str(real), 'volumetric_kg': str(volume), 'billable_kg': str(max(real, volume, Decimal('1')) if packages else Decimal('0')),
        'address': address_snapshot(user, data), 'origin': origin() if packages else {},
        'environment': settings.TCC_API_ENVIRONMENT, 'account_type': business,
        'account': settings.TCC_PQT_ACCOUNT if business == 'PQT' else settings.TCC_MSJ_ACCOUNT,
        'markup_percent': str(settings.TCC_SHIPPING_MARKUP_PERCENT), 'handling_fee': str(settings.TCC_SHIPPING_HANDLING_FEE)}
    return snapshot


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def quotation_payload(snapshot):
    return {'tipoenvio': '', 'idciudadorigen': snapshot['origin']['city_code'],
        'idciudaddestino': snapshot['address']['tcc_city_code'],
        'valormercancia': float(sum(Decimal(p['declared_value']) for p in snapshot['packages'])),
        'boomerang': 0, 'identificacion': '', 'cuenta': snapshot['account'],
        'fecharemesa': timezone.localdate().isoformat(), 'idunidadnegocio': 1 if snapshot['account_type'] == 'PQT' else 2,
        'unidades': [{'numerounidades': '1', 'pesoreal': float(p['weight_kg']),
            'pesovolumen': float(p['volumetric_kg']), 'alto': float(p['height_cm']),
            'largo': float(p['length_cm']), 'ancho': float(p['width_cm']), 'tipoempaque': ''} for p in snapshot['packages']]}


def fresh_rate(snapshot):
    if not snapshot['packages']:
        return Decimal('0'), Decimal('0'), Decimal('0')
    rate = TCCClient().quote(quotation_payload(snapshot))
    try:
        percent, fee = Decimal(snapshot['markup_percent']), Decimal(snapshot['handling_fee'])
        if not percent.is_finite() or not fee.is_finite() or percent < 0 or fee < 0 or percent > 1000:
            raise ValueError()
    except Exception:
        raise TCCError('La configuración de recargos no es válida.', code='configuration') from None
    surcharge = money(rate * percent / 100 + fee)
    return rate, surcharge, money(rate + surcharge)


def quote_shipping(user, items, data):
    snapshot = shipping_snapshot(user, items, data)
    key = fingerprint(snapshot)
    cached = ShippingQuote.objects.filter(user=user, fingerprint=key, reference='', expires_at__gt=timezone.now()).order_by('-created_at').first()
    if cached and not data.get('force', False):
        return cached
    rate, surcharge, total = fresh_rate(snapshot)
    return ShippingQuote.objects.create(user=user, fingerprint=key, snapshot=snapshot,
        environment=settings.TCC_API_ENVIRONMENT, account_type=snapshot['account_type'],
        tcc_rate=rate, surcharge=surcharge, total=total,
        expires_at=timezone.now()+timedelta(seconds=settings.TCC_QUOTE_TTL_SECONDS))


def validate_checkout_quote(user, quote_id, items, data):
    quote = ShippingQuote.objects.select_for_update().filter(pk=quote_id, user=user).first()
    if not quote or quote.expires_at <= timezone.now():
        raise ValidationError({'shipping_quote_id': 'La cotización expiró o no está disponible. Vuelve a cotizar.'})
    snapshot = shipping_snapshot(user, items, data)
    if quote.fingerprint != fingerprint(snapshot):
        raise ValidationError({'shipping_quote_id': 'Cambió el carrito, la dirección o el transporte. Vuelve a cotizar.'})
    reference = data.get('wompi_reference', '')
    if quote.reference and quote.reference != reference:
        raise ValidationError({'shipping_quote_id': 'La cotización ya está vinculada a otro pago.'})
    # A fresh provider request before payment; frontend cannot decide the amount.
    if fresh_rate(snapshot) != (quote.tcc_rate, quote.surcharge, quote.total):
        raise ValidationError({'shipping_quote_id': 'La tarifa TCC cambió. Actualiza la cotización antes de pagar.'})
    quote.reference = reference
    quote.save(update_fields=['reference'])
    return quote


def create_draft_order(intent, quote):
    """TCC-only unpaid local order. Inventory is untouched until Wompi approves."""
    if intent.order_id:
        return intent.order
    if connection.vendor == 'postgresql':
        # Serialize only number allocation for the new TCC drafts, not HTTP calls.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [384771029])
    data = intent.checkout_data
    order = Order.objects.create(user=intent.user, customer_name=data['customer_name'], customer_email=data['customer_email'],
        customer_phone=data['customer_phone'], shipping_address=data['shipping_address'], city=data['city'],
        department=data['department'], postal_code=data.get('postal_code', ''), notes=data.get('notes', ''),
        subtotal=intent.subtotal, shipping_cost=intent.shipping_cost, total=intent.total,
        payment_method='wompi', wompi_reference=intent.reference, status='pending', wompi_status='PENDING')
    for item in data['items']:
        OrderItem.objects.create(order=order, product_id=item['product_id'], quantity=item['quantity'], unit_price=item['unit_price'])
    intent.order = order
    intent.save(update_fields=['order'])
    if quote.snapshot['packages']:
        shipment = Shipment.objects.create(order=order, quote=quote)
        ShipmentEvent.objects.create(shipment=shipment, event_key='awaiting-payment', state=shipment.state,
                                    description='Orden registrada. El despacho espera confirmación oficial de pago.')
    return order


def mark_paid(order):
    shipment = Shipment.objects.select_for_update().filter(order=order).first()
    if shipment is None:
        return
    if order.status == Order.Status.CANCELLED:
        ShipmentEvent.objects.get_or_create(shipment=shipment, event_key='payment-after-local-cancellation', defaults={
            'state': shipment.state, 'description': 'Pago recibido para una orden cancelada localmente. Requiere revisión del asesor; no se solicitó despacho.'})
        return
    if shipment.state == Shipment.State.AWAITING_PAYMENT:
        shipment.state = Shipment.State.PENDING
        shipment.next_attempt_at = timezone.now()
        shipment.save(update_fields=['state', 'next_attempt_at', 'updated_at'])
        ShipmentEvent.objects.get_or_create(shipment=shipment, event_key='payment-approved', defaults={
            'state': shipment.state, 'description': 'Pago confirmado. Despacho pendiente de creación en TCC.'})
        transaction.on_commit(lambda: enqueue_shipment(shipment.pk))


def enqueue_shipment(shipment_id):
    try:
        from .tasks import create_shipment
        create_shipment.delay(shipment_id)
    except Exception as exc:
        logger.warning('TCC enqueue unavailable shipment_id=%s reason=%s', shipment_id, type(exc).__name__)
        # Durable pending row is recovered by Beat; a paid order is never lost.


def dispatch_payload(shipment):
    snap = shipment.quote.snapshot
    if any(not snap['origin'].get(field) for field in ('name', 'document_type', 'document', 'address', 'phone')):
        raise TCCError('Completa los datos del remitente TCC en el backend y genera una cotización nueva.', code='configuration')
    sender, recipient = snap['origin'], snap['address']
    units = [{'tipounidad': 'TIPO_UND_PAQ', 'tipoempaque': '', 'claseempaque': p['packaging_code'],
        'dicecontener': '', 'kilosreales': p['weight_kg'], 'largo': p['length_cm'], 'alto': p['height_cm'],
        'ancho': p['width_cm'], 'pesovolumen': p['volumetric_kg'], 'valormercancia': p['declared_value'],
        'codigodebarras': '', 'numerobolsa': '', 'referencias': '', 'unidadesinternas': '0'} for p in snap['packages']]
    return {'numerodespacho': '', 'fechadespacho': timezone.localdate().isoformat(),
        'unidadnegocio': 1 if snap['account_type'] == 'PQT' else 2, 'cuentaremitente': snap['account'],
        'sederemitente': '', 'primernombreremitente': sender['name'], 'segundonombreremitente': '',
        'primerapellidoremitente': '', 'segundoapellidoremitente': '', 'razonsocialremitente': sender.get('company', ''),
        'contactoremitente': '', 'tipoidentificacionremitente': sender['document_type'], 'identificacionremitente': sender['document'],
        'direccionremitente': sender['address'], 'ciudadorigen': sender['city_code'], 'telefonoremitente': sender['phone'],
        'emailremitente': sender.get('email', ''), 'destinatarios': [{
            'numerocontrol': '1', 'numeroremesa': '', 'numeroreferenciacliente': shipment.order.order_number,
            'tipoidentificaciondestinatario': '', 'identificaciondestinatario': '', 'sededestinatario': '',
            'primernombredestinatario': recipient['recipient_name'], 'segundonombredestinatario': '',
            'primerapellidodestinatario': '', 'segundoapellidodestinatario': '', 'razonsocialdestinatario': '',
            'contactodestinatario': '', 'direcciondestinatario': ', '.join(filter(None, [recipient['address'], recipient['complement'], recipient['neighborhood']])),
            'telefonodestinatario': recipient['phone'], 'ciudaddestino': recipient['tcc_city_code'], 'formapago': '',
            'llevabodega': '', 'recogebodega': '', 'centrocostos': '',
            'tiposervicio': 'TISE_NORMAL_PAQ' if snap['account_type'] == 'PQT' else 'TISE_NORMAL_MEN',
            'observaciones': recipient['delivery_instructions'], 'recaudoproducto': '', 'unidades': units}],
        'documentosreferencia': [{'tipodocumento': 'PE', 'numerodocumento': shipment.order.order_number,
                                 'fechadocumento': timezone.localdate().isoformat()}]}
