import logging
import smtplib
import socket
import ssl
from email.mime.image import MIMEImage
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Delivery
from .configuration import public_url, validate_smtp
from .documents import ensure_document, document_link, cop

logger = logging.getLogger(__name__)


def source_for(kind, pk):
    if kind == 'order':
        from ecommerce.models import Order
        return Order.objects.prefetch_related('items__product').get(pk=pk)
    from AppVisits.models import VisitaTecnica
    return VisitaTecnica.objects.select_related('cliente','tecnico','reporte').get(pk=pk)


def queue(kind, pk):
    source = source_for(kind, pk)
    if kind == 'order':
        if source.wompi_status != 'APPROVED' or source.payment_confirmation_email_sent_at:
            return False
        recipient = source.customer_email.strip()
    else:
        if source.correo_completada_en or not hasattr(source, 'reporte'):
            return False
        recipient = source.cliente.correo.strip()
    with transaction.atomic():
        delivery, created = Delivery.objects.get_or_create(kind=kind, object_id=pk, defaults={'recipient':recipient})
    if delivery.state in ('sent','sending','uncertain','cancelled'):
        return False
    def enqueue():
        from .tasks import deliver
        try:
            deliver.apply_async(args=[str(delivery.pk)], retry=False)
        except Exception:
            logger.warning('transactional_email queue_unavailable event=%s', delivery.pk)
    transaction.on_commit(enqueue)
    return created


def context_for(delivery, source):
    context = {'logo':'cid:imporgas-logo', 'document_url':document_link(delivery),
        'contact':settings.TRANSACTIONAL_REPLY_TO, 'phone':'3165266734 / 3176467820'}
    if delivery.kind == 'order':
        context.update(name=source.customer_name, title='Tu compra está confirmada', number=source.order_number,
            date=timezone.localtime(source.created_at,ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M'),
            document_label='Ver o descargar comprobante', summary='Wompi confirmó tu pago. Este comprobante es un resumen interno, no una factura electrónica.',
            rows=[{'name':i.product.name,'quantity':i.quantity,'price':cop(i.unit_price),'total':cop(i.quantity*i.unit_price)} for i in source.items.all()],
            details=[('Subtotal',cop(source.subtotal)),('Envío',cop(source.shipping_cost)),('Descuentos',cop(source.discounts)),
                ('Impuestos',cop(source.taxes)),('Total pagado',cop(source.paid_total if source.paid_total is not None else source.total)),
                ('Entrega',f'{source.shipping_address}, {source.city}, {source.department}'),('Pago','Wompi'),('Estado',source.get_status_display())],
            order_url=public_url(f'pedido/{source.tracking_code}'))
    else:
        tech = getattr(getattr(source.tecnico,'usuario_rel',None),'nombre_completo','')
        context.update(name=source.cliente.nombre, title='Tu servicio técnico ha sido finalizado',number=source.numero_tarea,
            date=source.fecha.strftime('%d/%m/%Y'), document_label='Ver informe de servicio técnico',
            summary=source.reporte.solucion_realizada[:500],
            details=[('Servicio',source.tipo_tarea_etiqueta or source.tipo_tarea),('Técnico',tech or 'Equipo de servicio técnico'),
                ('Valor final',cop(source.valor_visita) if source.valor_visita is not None else 'No registrado')])
    return context


def send(pk):
    with transaction.atomic():
        delivery=Delivery.objects.select_for_update().get(pk=pk)
        if delivery.state not in ('pending','failed') or delivery.attempts>=delivery.max_attempts:
            return False
        if delivery.next_attempt_at and delivery.next_attempt_at>timezone.now():
            return False
        if not settings.TRANSACTIONAL_EMAIL_ENABLED:
            return False
        delivery.state='sending';delivery.started_at=timezone.now();delivery.attempts+=1
        delivery.save(update_fields=['state','started_at','attempts'])
    stage='prepare'
    try:
        source=source_for(delivery.kind,delivery.object_id)
        if delivery.kind=='order' and source.wompi_status!='APPROVED':
            raise ValueError('payment_not_approved')
        validate_email(delivery.recipient)
        if settings.DEBUG and delivery.recipient.lower() not in [v.lower() for v in settings.TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS]:
            raise ValueError('recipient_not_authorized_in_dev')
        validate_smtp()
        ensure_document(delivery,source)
        context=context_for(delivery,source)
        message_id=f'<{delivery.pk}@imporgasjj.com>'
        delivery.message_id=message_id;delivery.save(update_fields=['message_id'])
        message=EmailMultiAlternatives(f'{context["title"]} — {context["number"]}',
            render_to_string('transactional_mail/message.txt',context),settings.DEFAULT_FROM_EMAIL,[delivery.recipient],
            reply_to=[settings.TRANSACTIONAL_REPLY_TO],headers={'Message-ID':message_id})
        message.attach_alternative(render_to_string('transactional_mail/message.html',context),'text/html')
        logo=Path(settings.BASE_DIR)/'AppVisits/assets/logo_imporgas.png'
        if logo.is_file():
            image=MIMEImage(logo.read_bytes(),_subtype='png')
            image.add_header('Content-ID','<imporgas-logo>')
            image.add_header('Content-Disposition','inline',filename='imporgas.png')
            message.attach(image)
        stage='smtp'
        if message.send(fail_silently=False)!=1:
            raise smtplib.SMTPException('not_accepted')
    except Exception as exc:
        # Never persist SMTP replies, recipient content, paths or credentials.
        ambiguous=stage=='smtp' and isinstance(exc,(socket.timeout,TimeoutError,smtplib.SMTPServerDisconnected))
        code = ('delivery_uncertain_manual_review' if ambiguous else
            'smtp_tls_certificate_invalid' if isinstance(exc,ssl.SSLCertVerificationError) else
            'smtp_authentication_failed' if isinstance(exc,smtplib.SMTPAuthenticationError) else
            'smtp_recipient_rejected' if isinstance(exc,smtplib.SMTPRecipientsRefused) else
            'smtp_sender_rejected' if isinstance(exc,smtplib.SMTPSenderRefused) else
            'smtp_configuration_invalid' if isinstance(exc,ImproperlyConfigured) else
            'recipient_invalid' if isinstance(exc,ValidationError) else
            'document_or_event_not_ready' if stage=='prepare' else 'smtp_temporarily_unavailable')
        if isinstance(exc,smtplib.SMTPResponseException):
            code += '_'+str(exc.smtp_code)
        logger.warning('transactional_email failure_class event=%s type=%s',pk,type(exc).__name__)
        Delivery.objects.filter(pk=pk).update(state='uncertain' if ambiguous else 'failed',last_error=code,
            next_attempt_at=timezone.now()+timedelta(minutes=5*delivery.attempts))
        try:
            if delivery.kind=='order':
                from ecommerce.models import Order
                Order.objects.filter(pk=delivery.object_id).update(payment_confirmation_email_error=code)
            else:
                from AppVisits.models import VisitaTecnica
                VisitaTecnica.objects.filter(pk=delivery.object_id).update(correo_completada_error=code)
        except Exception:
            pass
        logger.warning('transactional_email failed event=%s reason=%s',pk,code)
        return False
    Delivery.objects.filter(pk=pk).update(state='sent',sent_at=timezone.now(),last_error='',next_attempt_at=None)
    if delivery.kind=='order':
        type(source).objects.filter(pk=source.pk).update(payment_confirmation_email_sent_at=timezone.now(),payment_confirmation_email_error='')
    else:
        type(source).objects.filter(pk=source.pk).update(correo_completada_en=timezone.now(),correo_completada_error='')
    logger.info('transactional_email sent event=%s',pk)
    return True
