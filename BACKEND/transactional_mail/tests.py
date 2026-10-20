import io
import tempfile
import smtplib
import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import urlsplit
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from pypdf import PdfReader
from ecommerce.models import Order, OrderItem, Product, Category, Brand
from AppVisits.models import VisitaTecnica, ClienteVisita, ReporteVisita
from AppVisits.views import _persist_visit_pdf
from usuarios.models import Credenciales
from .models import Delivery
from .service import queue, send
from .documents import document_link
from .configuration import public_url, validate_smtp


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',TRANSACTIONAL_EMAIL_ENABLED=True,
    DEBUG=True,FRONTEND_PUBLIC_URL='http://localhost',PUBLIC_API_URL='http://localhost/api',
    TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS=['qa@example.invalid'])
class TransactionalTests(APITestCase):
    def setUp(self):
        self.media=tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        setting=override_settings(MEDIA_ROOT=self.media.name);setting.enable();self.addCleanup(setting.disable)
        self.owner=Credenciales.objects.create(usuario='mail-owner',estado=1,tipo_usuario=0)
        self.other=Credenciales.objects.create(usuario='mail-other',estado=1,tipo_usuario=0)
        self.order=Order.objects.create(user=self.owner,customer_name='<script>José & María</script>',customer_email='qa@example.invalid',
            shipping_address='Dirección sintética',city='Cali',department='Valle del Cauca',subtotal=100000,shipping_cost=10000,
            discounts=5000,taxes=2000,total=107000,paid_total=107000,wompi_status='APPROVED',payment_method='wompi',status='paid')
        product=Product.objects.create(name='Calentador <QA>',price=100000,category=Category.objects.create(name='QA'),brand=Brand.objects.create(name='QA'))
        OrderItem.objects.create(order=self.order,product=product,quantity=1,unit_price=100000)
        customer=ClienteVisita.objects.create(nombre='José & María',correo='qa@example.invalid',direccion='QA')
        self.visit=VisitaTecnica.objects.create(cliente=customer,tipo_tarea='mantenimiento',fecha=date.today(),hora=time(10),descripcion='QA')
        ReporteVisita.objects.create(visita=self.visit,persona_atiende='QA',equipo='estufa',ubicacion_equipo='cocina',
            motivo_servicio='QA',solucion_realizada='Mantenimiento de prueba, sin intervención real.')

    def registration(self,kind,source):
        with patch('transactional_mail.tasks.deliver.apply_async'):
            with self.captureOnCommitCallbacks(execute=True):
                queue(kind,source.pk)
        return Delivery.objects.get(kind=kind,object_id=source.pk)

    def test_approved_order_document_and_duplicate(self):
        delivery=self.registration('order',self.order)
        self.assertTrue(send(delivery.pk));self.assertFalse(send(delivery.pk))
        self.assertFalse(queue('order',self.order.pk))
        self.assertEqual(len(mail.outbox),1)
        message=mail.outbox[0]
        self.assertEqual(message.reply_to,['ventas@imporgasjj.com'])
        self.assertIn('$ 107.000,00 COP',message.body)
        self.assertIn('Envío registrado anteriormente: $ 10.000,00 COP',message.body)
        self.assertIn('&lt;script&gt;',message.alternatives[0].content)
        self.assertNotIn('<script>',message.alternatives[0].content)
        delivery.refresh_from_db()
        with delivery.document.open('rb') as file:
            text=''.join(page.extract_text() for page in PdfReader(file).pages)
        self.assertIn('No es una factura electrónica',text)
        self.assertIn('107.000,00',text)
        url=urlsplit(document_link(delivery))
        response=self.client.get(url.path.removeprefix('/api')+'?'+url.query)
        self.assertEqual(response.status_code,200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertEqual(self.client.get('/media/'+delivery.document.name).status_code,404)

    def test_new_order_receipt_and_email_do_not_offer_free_delivery(self):
        self.order.shipping_cost=None
        self.order.total=97000;self.order.paid_total=97000
        self.order.save()
        delivery=self.registration('order',self.order)
        self.assertTrue(send(delivery.pk))
        message=mail.outbox[0]
        self.assertIn('El valor del envío no está incluido en esta compra.',message.body)
        self.assertNotIn('Envío: $',message.body)
        self.assertNotIn('gratis',message.body.lower())
        delivery.refresh_from_db()
        with delivery.document.open('rb') as document:
            text='\n'.join(page.extract_text() for page in PdfReader(document).pages)
        self.assertIn('El valor del envío no está incluido',text)
        self.assertNotIn('Envío: $',text)
        self.assertNotIn('gratis',text.lower())

    def test_pending_and_rejected_do_not_queue(self):
        for state in ('PENDING','DECLINED','ERROR'):
            self.order.wompi_status=state;self.order.save()
            self.assertFalse(queue('order',self.order.pk))
        self.assertFalse(Delivery.objects.exists())

    def test_document_token_expiry_tamper_and_owner(self):
        delivery=self.registration('order',self.order);send(delivery.pk)
        url=urlsplit(document_link(delivery));path=url.path.removeprefix('/api')
        self.assertEqual(self.client.get(path+'?'+url.query+'x').status_code,403)
        self.assertEqual(self.client.get(path.replace(str(delivery.pk),str(uuid.uuid4()))+'?'+url.query).status_code,403)
        with patch('django.core.signing.time.time',return_value=timezone.now().timestamp()+8*86400):
            self.assertEqual(self.client.get(path+'?'+url.query).status_code,403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(path+'renew/').status_code,403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(path+'renew/').status_code,200)
        self.order.wompi_status='DECLINED';self.order.save()
        self.assertEqual(self.client.post(path+'renew/').status_code,409)
        self.assertEqual(self.client.get(path+'?'+url.query).status_code,404)

    def test_visit_waits_for_pdf_and_sends_once(self):
        delivery=self.registration('visit',self.visit)
        self.assertFalse(send(delivery.pk));self.assertEqual(len(mail.outbox),0)
        _persist_visit_pdf(self.visit.pk)
        Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        self.assertTrue(send(delivery.pk));self.assertFalse(send(delivery.pk))
        url=urlsplit(document_link(delivery))
        path=url.path.removeprefix('/api')+'?'+url.query+'&download=1'
        response=self.client.get(path);self.assertEqual(response.status_code,200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))
        self.assertIn('attachment',response['Content-Disposition'])
        self.visit.refresh_from_db();self.visit.pdf_link_version+=1;self.visit.save()
        self.assertEqual(self.client.get(path).status_code,403)

    def test_smtp_rejection_sanitized_retry_and_uncertainty(self):
        delivery=self.registration('order',self.order)
        with patch('transactional_mail.service.EmailMultiAlternatives.send',side_effect=smtplib.SMTPAuthenticationError(535,b'SECRET_DO_NOT_LOG')):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db();self.assertEqual(delivery.last_error,'smtp_authentication_failed_535')
        self.order.refresh_from_db();self.assertEqual(self.order.status,'paid')
        Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        with patch('transactional_mail.service.EmailMultiAlternatives.send',side_effect=TimeoutError('secret')):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db();self.assertEqual(delivery.state,'uncertain')
        self.assertFalse(send(delivery.pk))

    def test_urls_and_smtp_config(self):
        self.assertEqual(public_url('/mail/documents/',api=True),'http://localhost/api/mail/documents/')
        with override_settings(DEBUG=False,FRONTEND_PUBLIC_URL='https://www.imporgasjj.com/',PUBLIC_API_URL='https://www.imporgasjj.com/api/'):
            self.assertEqual(public_url('/x',api=True),'https://www.imporgasjj.com/api/x')
        with override_settings(DEBUG=False,FRONTEND_PUBLIC_URL='http://localhost'):
            with self.assertRaises(ImproperlyConfigured):public_url('x')
        for host in ('https://localhost','https://backend.internal','https://127.0.0.1'):
            with override_settings(DEBUG=False,FRONTEND_PUBLIC_URL=host):
                with self.assertRaises(ImproperlyConfigured):public_url('x')
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='smtp-relay.brevo.com',EMAIL_HOST_USER='',EMAIL_HOST_PASSWORD=''):
            with self.assertRaises(ImproperlyConfigured):validate_smtp()

    def test_queue_failure_preserves_pending_event(self):
        with patch('transactional_mail.tasks.deliver.apply_async',side_effect=RuntimeError('secret')):
            with self.captureOnCommitCallbacks(execute=True):queue('order',self.order.pk)
        self.assertEqual(Delivery.objects.get().state,'pending')

    def test_development_blocks_unapproved_recipient(self):
        self.order.customer_email='not-authorized@example.invalid';self.order.save()
        delivery=self.registration('order',self.order)
        self.assertFalse(send(delivery.pk));self.assertEqual(len(mail.outbox),0)

    def test_admin_audit_retry_budget_and_immutable_terminal_states(self):
        delivery=self.registration('order',self.order)
        base='/mail/deliveries/'
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(base).status_code,403)
        self.assertEqual(self.client.post(base+str(delivery.pk)+'/retry/').status_code,403)
        self.owner.tipo_usuario=1;self.owner.save()
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(base).status_code,200)
        Delivery.objects.filter(pk=delivery.pk).update(state='failed',attempts=3)
        with patch('transactional_mail.tasks.deliver.apply_async',side_effect=RuntimeError('SECRET')):
            self.assertEqual(self.client.post(base+str(delivery.pk)+'/retry/').status_code,202)
        delivery.refresh_from_db()
        self.assertEqual((delivery.state,delivery.attempts,delivery.max_attempts),('pending',3,6))
        for state in ('sent','sending','uncertain','cancelled'):
            Delivery.objects.filter(pk=delivery.pk).update(state=state)
            self.assertEqual(self.client.post(base+str(delivery.pk)+'/retry/').status_code,409)
            with patch('transactional_mail.tasks.deliver.apply_async') as enqueue:
                with self.captureOnCommitCallbacks(execute=True):
                    self.assertFalse(queue('order',self.order.pk))
                enqueue.assert_not_called()
            self.assertFalse(send(delivery.pk))

    def test_disabled_delivery_and_exhausted_budget_preserve_source(self):
        delivery=self.registration('order',self.order)
        with override_settings(TRANSACTIONAL_EMAIL_ENABLED=False):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db();self.assertEqual(delivery.attempts,0)
        Delivery.objects.filter(pk=delivery.pk).update(attempts=3)
        self.assertFalse(send(delivery.pk));self.assertEqual(len(mail.outbox),0)
        self.order.refresh_from_db();self.assertEqual(self.order.status,'paid')
