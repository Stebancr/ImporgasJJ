import io
import os
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase
from pypdf import PdfReader
from AppVisits.views import _generar_pdf
from . import tests as fixtures
from .models import Delivery
from .service import send, queue
from .configuration import sender_for


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', TRANSACTIONAL_EMAIL_ENABLED=True,
    SERVER_EMAIL_APLICACION='technical@example.invalid', DEBUG=True, FRONTEND_PUBLIC_URL='http://localhost',
    PUBLIC_API_URL='http://localhost/api', TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS=['qa@example.invalid'])
class TechnicalEmailReadinessTests(APITestCase):
    setUp = fixtures.TransactionalTests.setUp
    registration = fixtures.TransactionalTests.registration

    def test_confirmation_has_technical_from_text_html_no_pdf_and_one_logical_event(self):
        delivery=self.registration('visit_confirmation',self.visit)
        self.assertTrue(send(delivery.pk))
        self.assertFalse(send(delivery.pk))
        self.assertFalse(queue('visit_confirmation',self.visit.pk))
        message=mail.outbox[-1]
        parsed=BytesParser(policy=policy.default).parsebytes(message.message().as_bytes())
        self.assertEqual(parsed['From'].addresses[0].display_name,'ImporGas JJ Servicio Técnico')
        self.assertEqual(parsed['From'].addresses[0].addr_spec,'technical@example.invalid')
        self.assertEqual(message.to,['qa@example.invalid'])
        self.assertEqual(message.cc,[]); self.assertEqual(message.bcc,[])
        self.assertIn('programada',message.subject)
        self.assertIn('José & María',message.body)
        self.assertIn('text/html',[part.get_content_type() for part in message.message().walk()])
        self.assertNotIn('token=',message.body)
        self.assertEqual(Delivery.objects.filter(kind='visit_confirmation',object_id=self.visit.pk).count(),1)
        self.visit.refresh_from_db()
        self.assertIsNone(self.visit.correo_completada_en)

    def test_failed_confirmation_keeps_visit_and_can_retry_without_duplicate(self):
        delivery=self.registration('visit_confirmation',self.visit)
        with override_settings(SERVER_EMAIL_APLICACION=''):
            self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.state,'failed')
        self.assertIn('SERVER_EMAIL_APLICACION',delivery.last_error)
        self.assertTrue(type(self.visit).objects.filter(pk=self.visit.pk).exists())
        Delivery.objects.filter(pk=delivery.pk).update(next_attempt_at=None)
        self.assertTrue(send(delivery.pk))
        self.assertEqual(Delivery.objects.filter(kind='visit_confirmation').count(),1)

    def test_cancelled_visit_confirmation_is_not_delivered(self):
        delivery=self.registration('visit_confirmation',self.visit)
        type(self.visit).objects.filter(pk=self.visit.pk).update(estado='cancelada')
        self.assertFalse(send(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.state,'cancelled')
        self.assertEqual(len(mail.outbox),0)

    def test_visit_pdf_only_changes_configured_contact_and_preserves_layout(self):
        with patch('transactional_mail.configuration.visit_contact_address',return_value='old@example.invalid'):
            before=_generar_pdf(self.visit)
        after=_generar_pdf(self.visit)
        a,b=PdfReader(io.BytesIO(before)),PdfReader(io.BytesIO(after))
        self.assertEqual(len(a.pages),len(b.pages))
        self.assertEqual([list(p.mediabox) for p in a.pages],[list(p.mediabox) for p in b.pages])
        old=' '.join(p.extract_text() for p in a.pages)
        new=' '.join(p.extract_text() for p in b.pages)
        self.assertIn('technical@example.invalid',new)
        self.assertNotIn('servicioimporgas@gmail.com',new)
        self.assertEqual(old.replace('old@example.invalid','technical@example.invalid'),new)
        if os.environ.get('READINESS_PDF_EVIDENCE')=='1':
            from pathlib import Path
            Path('/tmp/readiness-pdf-before.pdf').write_bytes(before)
            Path('/tmp/readiness-pdf-after.pdf').write_bytes(after)

    def test_other_sender_settings_remain_independent(self):
        with override_settings(DEFAULT_FROM_EMAIL='Sales <sales@example.invalid>', SERVER_EMAIL='server@example.invalid'):
            self.assertEqual(sender_for('order'),'Sales <sales@example.invalid>')
            self.assertIn('technical@example.invalid',sender_for('visit'))
            self.assertIn('technical@example.invalid',sender_for('visit_confirmation'))

    def test_creating_a_visit_registers_confirmation_after_commit(self):
        from datetime import timedelta
        from types import SimpleNamespace
        from django.utils import timezone
        from AppVisits.models import TipoVisita
        from AppVisits.serializers import VisitaCreateSerializer
        from usuarios.models import Credenciales
        kind=TipoVisita.objects.create(codigo='readiness-confirmation',nombre='Servicio QA',activo=True)
        technician=Credenciales.objects.create(usuario='readiness-technician',tipo_usuario=1,estado=1)
        serializer=VisitaCreateSerializer(data={
            'cliente_nombre':'Cliente sintético', 'cliente_telefono':'3000000000',
            'cliente_correo':'qa@example.invalid', 'cliente_direccion':'Dirección sintética',
            'tipo_tarea':kind.codigo, 'tecnico_id':technician.pk,
            'fecha':str(timezone.localdate()+timedelta(days=1)), 'hora':'10:00:00',
        },context={'request':SimpleNamespace(user=self.owner)})
        self.assertTrue(serializer.is_valid(),serializer.errors)
        with patch('transactional_mail.tasks.deliver.apply_async') as worker:
            with self.captureOnCommitCallbacks(execute=True):
                visit=serializer.save()
                worker.assert_not_called()
            worker.assert_called_once()
        event=Delivery.objects.get(kind='visit_confirmation',object_id=visit.pk)
        self.assertEqual(event.recipient,'qa@example.invalid')
        self.assertTrue(send(event.pk))
        self.assertIsNone(type(visit).objects.get(pk=visit.pk).correo_completada_en)
