"""Correos transaccionales de comercio enviados por el SMTP configurado."""
import logging

from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .models import Order


logger = logging.getLogger(__name__)


def send_order_payment_confirmation(order_id):
    """Envía una sola confirmación después de una aprobación Wompi verificada."""
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .prefetch_related('items__product')
            .get(pk=order_id)
        )
        if order.payment_confirmation_email_sent_at:
            return False
        if order.wompi_status != Order.WompiStatus.APPROVED:
            return False

        recipient = order.customer_email.strip()
        try:
            validate_email(recipient)
        except ValidationError:
            order.payment_confirmation_email_error = 'El pedido no tiene un correo de cliente válido.'
            order.save(update_fields=['payment_confirmation_email_error', 'updated_at'])
            return False

        item_lines = ''.join(
            f'<li>{item.product.name} × {item.quantity}: ${item.unit_price:,.0f}</li>'
            for item in order.items.all()
        ) or '<li>Consulta el detalle de tu pedido en la tienda.</li>'
        subject = f'Pago confirmado — pedido {order.order_number}'
        text_body = (
            f'Hola {order.customer_name},\n\n'
            f'Wompi confirmó correctamente el pago de tu pedido {order.order_number}.\n'
            f'Referencia de pago: {order.wompi_reference}.\n'
            f'Total pagado: ${order.total:,.0f} COP.\n\n'
            'Gracias por comprar en IMPORGAS JJ.'
        )
        html_body = (
            f'<p>Hola {order.customer_name},</p>'
            f'<p>Wompi confirmó correctamente el pago de tu pedido '
            f'<strong>{order.order_number}</strong>.</p>'
            f'<p>Referencia: <strong>{order.wompi_reference}</strong><br>'
            f'Total pagado: <strong>${order.total:,.0f} COP</strong></p>'
            f'<p>Productos:</p><ul>{item_lines}</ul>'
            '<p>Gracias por comprar en IMPORGAS JJ.</p>'
        )
        try:
            message = EmailMultiAlternatives(subject, text_body, to=[recipient])
            message.attach_alternative(html_body, 'text/html')
            message.send(fail_silently=False)
        except Exception as exc:
            logger.exception('No fue posible enviar confirmación de pago para pedido %s', order.pk)
            order.payment_confirmation_email_error = exc.__class__.__name__[:1000]
            order.save(update_fields=['payment_confirmation_email_error', 'updated_at'])
            return False

        order.payment_confirmation_email_sent_at = timezone.now()
        order.payment_confirmation_email_error = ''
        order.save(update_fields=[
            'payment_confirmation_email_sent_at',
            'payment_confirmation_email_error',
            'updated_at',
        ])
        return True
