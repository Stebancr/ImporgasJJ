import io
import hashlib
from xml.sax.saxutils import escape
from django.core import signing
from django.core.files.base import ContentFile
from django.urls import reverse
from .configuration import public_url


def cop(value):
    return '$ ' + f'{value or 0:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') + ' COP'


def receipt(order):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    p = lambda value: Paragraph(escape(str(value)), styles['BodyText'])
    story = [Paragraph('IMPORGAS JJ', styles['Title']), Paragraph('Comprobante de compra', styles['Heading1']),
        p('Resumen interno del pedido. No es una factura electrónica.'), Spacer(1, 16),
        p(f'Pedido: {order.order_number}'), p(f'Cliente: {order.customer_name}'),
        p(f'Fecha: {order.created_at:%d/%m/%Y}'), p(f'Dirección: {order.shipping_address}, {order.city}'), Spacer(1, 16)]
    rows = [[p('Producto'), p('Cantidad'), p('Precio unitario'), p('Importe')]]
    rows += [[p(i.product.name), p(i.quantity), p(cop(i.unit_price)), p(cop(i.quantity*i.unit_price))] for i in order.items.all()]
    table = Table(rows, colWidths=[210, 55, 105, 110], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf7')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dde3ed'))]))
    story += [table, Spacer(1, 20)]
    for name, value in [('Subtotal',order.subtotal),('Envío',order.shipping_cost),('Descuentos',order.discounts),('Impuestos',order.taxes),('Total pagado',order.paid_total if order.paid_total is not None else order.total)]:
        story.append(p(f'{name}: {cop(value)}'))
    story += [Spacer(1,20), p('Pago confirmado por Wompi.'), p('Contacto: ventas@imporgasjj.com · 3165266734 / 3176467820')]
    SimpleDocTemplate(stream, rightMargin=50, leftMargin=50, title='Comprobante de compra', author='ImporGas JJ').build(story)
    return stream.getvalue()


def ensure_document(delivery, source):
    if delivery.kind == 'order':
        if not delivery.document or not delivery.document.storage.exists(delivery.document.name):
            delivery.document.save(f'{delivery.pk}.pdf', ContentFile(receipt(source)), save=True)
        return
    from AppVisits.views import _pdf_source_hash
    if (source.estado != source.ESTADO_FINALIZADA or source.pdf_estado != 'generado' or not source.pdf_final
            or (source.pdf_source_hash and source.pdf_source_hash != _pdf_source_hash(source))):
        raise ValueError('document_pending')
    with source.pdf_final.open('rb') as file:
        data = file.read()
    if len(data) != source.pdf_bytes or hashlib.sha256(data).hexdigest() != source.pdf_sha256:
        raise ValueError('document_invalid')


def document_link(delivery):
    payload={'delivery':str(delivery.pk)}
    if delivery.kind=='visit':
        from AppVisits.models import VisitaTecnica
        payload['version']=VisitaTecnica.objects.values_list('pdf_link_version',flat=True).get(pk=delivery.object_id)
    token = signing.dumps(payload, salt='transactional-document')
    return public_url(reverse('transactional-document', args=[delivery.pk]), api=True) + '?token=' + token
