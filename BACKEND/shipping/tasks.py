from datetime import timedelta
import logging
from celery import shared_task
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
from ecommerce.models import WompiPaymentIntent
from .models import Shipment, ShipmentEvent
from .services import dispatch_payload, enqueue_shipment
from .tcc import TCCClient, TCCError

logger = logging.getLogger(__name__)


def event(shipment, key, description):
    ShipmentEvent.objects.get_or_create(shipment=shipment, event_key=key,
        defaults={'state': shipment.state, 'description': description})


@shared_task
def create_shipment(shipment_id):
    if not settings.TCC_SHIPPING_ENABLED or not settings.TCC_DISPATCH_ENABLED:
        return {'skipped': 'dispatch_disabled'}
    with transaction.atomic():
        shipment = Shipment.objects.select_for_update(of=('self',)).select_related('order', 'quote').filter(pk=shipment_id).first()
        if not shipment:
            return {'skipped': 'not_found'}
        if shipment.state not in (Shipment.State.PENDING, Shipment.State.ERROR) or shipment.waybill:
            return {'skipped': 'already_claimed_or_final'}
        order = shipment.order
        if order.payment_method == 'wompi':
            confirmed = WompiPaymentIntent.objects.filter(order=order, wompi_status='APPROVED', processed_at__isnull=False,
                                                        total=order.total, shipping_cost=shipment.quote.total).exists()
        else:
            confirmed = order.status == 'paid'
        if not confirmed or order.status == 'cancelled':
            return {'skipped': 'payment_not_confirmed'}
        if shipment.quote.environment != settings.TCC_API_ENVIRONMENT:
            return {'skipped': 'environment_mismatch'}
        shipment.state, shipment.started_at = Shipment.State.CREATING, timezone.now()
        shipment.attempts += 1
        shipment.next_attempt_at = None
        shipment.request_summary = {'order_number': order.order_number, 'packages': len(shipment.quote.snapshot['packages']),
            'origin_code': shipment.quote.snapshot['origin'].get('city_code'),
            'destination_code': shipment.quote.snapshot['address']['tcc_city_code'],
            'environment': shipment.quote.environment, 'account_type': shipment.quote.account_type,
            'local_idempotency_key': str(shipment.idempotency_key)}
        shipment.save()
        event(shipment, f'attempt-{shipment.attempts}', 'Solicitud de creación de despacho iniciada.')
    try:
        if not shipment.quote.snapshot['packages']:
            raise TCCError('La orden no requiere transporte.', code='no_packages')
        result = TCCClient().dispatch(dispatch_payload(shipment))
    except TCCError as exc:
        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
            shipment.state = Shipment.State.UNCERTAIN if exc.uncertain else Shipment.State.ERROR
            shipment.last_error = str(exc)[:300]
            shipment.response_summary = {'code': exc.code}
            if exc.retryable and not exc.uncertain and shipment.attempts < 3:
                shipment.next_attempt_at = timezone.now() + timedelta(minutes=2 ** shipment.attempts)
            shipment.save()
            event(shipment, f'error-{shipment.attempts}', shipment.last_error)
        logger.warning('TCC dispatch failed shipment_id=%s code=%s uncertain=%s', shipment_id, exc.code, exc.uncertain)
        return {'state': shipment.state}
    except Exception as exc:
        # The request may have reached TCC. Never blindly send a second one.
        Shipment.objects.filter(pk=shipment_id).update(state=Shipment.State.UNCERTAIN,
            last_error='La operación terminó sin confirmación. Verifica con TCC antes de reintentar.')
        logger.warning('TCC dispatch uncertain shipment_id=%s reason=%s', shipment_id, type(exc).__name__)
        return {'state': Shipment.State.UNCERTAIN}
    with transaction.atomic():
        shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
        try:
            with transaction.atomic():
                shipment.waybill = result['waybill']
                shipment.pickup_number = result['pickup_number']
                shipment.document_urls = result['documents']
                shipment.state, shipment.last_error = Shipment.State.CREATED, ''
                shipment.last_sync_at = timezone.now()
                shipment.response_summary = {'code': '0', 'waybill': shipment.waybill}
                shipment.save()
        except IntegrityError:
            shipment.refresh_from_db()
            shipment.state = Shipment.State.UNCERTAIN
            shipment.last_error = 'TCC devolvió una guía ya asociada. Requiere verificación manual.'
            shipment.save()
        event(shipment, 'dispatch-confirmed' if shipment.state == Shipment.State.CREATED else 'duplicate-provider-guide',
              'TCC confirmó la creación del despacho.' if shipment.state == Shipment.State.CREATED else shipment.last_error)
    return {'state': shipment.state}


@shared_task
def recover_pending_shipments():
    if not settings.TCC_SHIPPING_ENABLED or not settings.TCC_DISPATCH_ENABLED:
        return {'skipped': 'disabled'}
    now = timezone.now()
    # A worker may die after transmitting a request. Reconcile manually; don't
    # turn expiration of a local lease into a second charge/waybill at TCC.
    for row in Shipment.objects.filter(state='creating', started_at__lt=now-timedelta(minutes=3))[:50]:
        updated = Shipment.objects.filter(pk=row.pk, state='creating').update(state='uncertain',
            last_error='El proceso terminó sin confirmación. Verifica la remesa con TCC.')
        if updated:
            row.state = 'uncertain'
            event(row, 'worker-interrupted', 'Creación sin confirmación; no se repetirá automáticamente.')
    ids = list(Shipment.objects.filter(state__in=['pending', 'error'], next_attempt_at__lte=now).order_by('next_attempt_at').values_list('pk', flat=True)[:50])
    for pk in ids:
        enqueue_shipment(pk)
    return {'queued': len(ids)}
