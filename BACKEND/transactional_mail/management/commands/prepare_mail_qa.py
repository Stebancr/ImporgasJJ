"""Creates explicitly labeled, stable dev fixtures; never sends directly."""
from datetime import time
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from transactional_mail.models import Delivery
from transactional_mail.documents import ensure_document
from transactional_mail.service import context_for


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--recipient',required=True)
        parser.add_argument('--enqueue',action='store_true')

    def handle(self,*args,**options):
        recipient=options['recipient']
        if not settings.DEBUG or recipient not in settings.TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS:
            raise CommandError('Requires development and an explicitly allowed recipient.')
        from ecommerce.models import Order, OrderItem, Product, Category, Brand
        from AppVisits.models import ClienteVisita,VisitaTecnica,ReporteVisita
        from AppVisits.views import _persist_visit_pdf
        with transaction.atomic():
            category,_=Category.objects.get_or_create(name='QA correo transaccional',defaults={'is_active':False})
            brand,_=Brand.objects.get_or_create(name='QA correo transaccional',defaults={'is_active':False})
            product,_=Product.objects.get_or_create(slug='qa-brevo-no-comercial',defaults={'name':'Producto sintético QA — no es una compra real','category':category,'brand':brand,'price':100000,'is_available':False})
            order,_=Order.objects.get_or_create(order_number='QA-MAIL-20261019',defaults=dict(customer_name='Cliente de prueba — José & María',
                customer_email=recipient,shipping_address='Dirección sintética de prueba',city='Cali',department='Valle del Cauca',
                subtotal=100000,shipping_cost=10000,discounts=0,taxes=0,total=110000,paid_total=110000,status='paid',
                payment_method='wompi',wompi_status='APPROVED',notes='QA sintético autorizado. Sin cobro, inventario ni despacho real.'))
            OrderItem.objects.get_or_create(order=order,product=product,defaults={'quantity':1,'unit_price':100000})
            visit=VisitaTecnica.objects.filter(descripcion='Prueba QA autorizada',cliente__correo=recipient).order_by('pk').first()
            if not visit:
                customer=ClienteVisita.objects.create(nombre='Cliente de prueba — José & María',correo=recipient,direccion='Dirección sintética de prueba')
                visit=VisitaTecnica.objects.create(numero_tarea='QA-MAIL-20261019',cliente=customer,tipo_tarea='mantenimiento',tipo_tarea_etiqueta='Prueba de correo — sin intervención real',fecha=timezone.localdate(),hora=time(10),descripcion='Prueba QA autorizada',valor_visita=85000)
                ReporteVisita.objects.create(visita=visit,persona_atiende='Cliente QA',equipo='estufa',ubicacion_equipo='cocina',motivo_servicio='Validación de correos',solucion_realizada='Este es un informe sintético para validar el correo y la descarga del PDF. No corresponde a un servicio realizado.',valor_servicio=85000)
        visit=_persist_visit_pdf(visit.pk)
        for kind,source in [('order',order),('visit',visit)]:
            delivery,_=Delivery.objects.get_or_create(kind=kind,object_id=source.pk,defaults={'recipient':recipient})
            ensure_document(delivery,source)
            context=context_for(delivery,source)
            import base64
            from transactional_mail.branding import LOGO_PATH
            context['email_logo_src']='data:image/png;base64,'+base64.b64encode(LOGO_PATH.read_bytes()).decode()
            # Previews contain no signed tokens; actual delivery constructs fresh links.
            context['document_url']='https://example.invalid/documento-de-prueba'
            context['order_url']='https://example.invalid/pedido-de-prueba' if kind=='order' else ''
            output=Path('/tmp/mail-qa');output.mkdir(exist_ok=True)
            (output/f'{kind}.html').write_text(render_to_string('transactional_mail/message.html',context))
            file=delivery.document if kind=='order' else source.pdf_final
            with file.open('rb') as stream:(output/f'{kind}.pdf').write_bytes(stream.read())
            self.stdout.write(f'{kind}: event={delivery.pk} state={delivery.state} document=ready')
            if options['enqueue'] and delivery.state=='pending':
                from transactional_mail.tasks import deliver
                deliver.apply_async(args=[str(delivery.pk)],queue='mail-qa',retry=False)
                self.stdout.write(kind+': queued on isolated mail-qa queue')
