import base64
from datetime import date, time
from io import BytesIO
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from pypdf import PdfReader
from rest_framework.test import APITestCase

from usuarios.models import Credenciales, Usuario
from .models import ClienteVisita, VisitaTecnica
from .notifications import notify_technician_visit_assigned
from ecommerce.models import Notification


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class VisitCompletionTests(APITestCase):
    def setUp(self):
        profile = Usuario.objects.create(cedula='visit-admin', nombre_completo='Admin Visitas', correo='admin@example.com')
        self.admin = Credenciales.objects.create(usuario='visit-admin', usuario_rel=profile, estado=1, tipo_usuario=4)
        self.admin.set_password('safe-test-password')
        self.admin.save(update_fields=['password'])
        self.client.force_authenticate(self.admin)
        customer = ClienteVisita.objects.create(
            nombre='Cliente PDF', identificacion='123', telefono='3000000000',
            correo='cliente@example.com', direccion='Calle de prueba',
        )
        self.visit = VisitaTecnica.objects.create(
            cliente=customer, tipo_tarea='mantenimiento', fecha=date.today(),
            hora=time(10, 0), descripcion='Prueba de visita', creado_por=self.admin,
        )

    def test_task_number_is_deterministic(self):
        self.assertEqual(self.visit.numero_tarea, str(999 + self.visit.id))
        second = VisitaTecnica.objects.create(
            cliente=self.visit.cliente, tipo_tarea='revision', fecha=date.today(), hora=time(11, 0)
        )
        self.assertEqual(second.numero_tarea, str(999 + second.id))

    def test_completion_sends_one_email_with_pdf_and_signature_line_label(self):
        signature_png = base64.b64encode(base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        )).decode()
        payload = {
            'persona_atiende': 'Cliente PDF', 'equipo': 'estufa',
            'ubicacion_equipo': 'cocina', 'motivo_servicio': 'Mantenimiento',
            'solucion_realizada': 'Trabajo completado',
            'firma_base64': f'data:image/png;base64,{signature_png}',
        }
        url = reverse('visitas-finalizar', args=[self.visit.id])
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['correo_enviado'])
        self.visit.refresh_from_db()
        self.assertIsNotNone(self.visit.correo_completada_en)
        self.assertEqual(len(mail.outbox), 1)
        attachment = mail.outbox[0].attachments[0]
        self.assertEqual(attachment.mimetype, 'application/pdf')
        text = ''.join(page.extract_text() or '' for page in PdfReader(BytesIO(attachment.content)).pages)
        self.assertIn(f'Tarea {self.visit.numero_tarea}', text)
        self.assertIn('Firma cliente', text)

        repeated = self.client.post(url, payload, format='json')
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(len(mail.outbox), 1)


class VisitAssignmentNotificationTests(APITestCase):
    @patch('AppVisits.notifications.send_push_to_user')
    def test_assigned_technician_receives_persisted_and_fcm_notification(self, send_push):
        technician = Credenciales.objects.create(usuario='tech-push', estado=1, tipo_usuario=1)
        customer = ClienteVisita.objects.create(nombre='Cliente Push', direccion='Dirección')
        visit = VisitaTecnica.objects.create(
            cliente=customer, tecnico=technician, tipo_tarea='revision',
            fecha=date.today(), hora=time(9, 0),
        )
        send_push.return_value = {'sent': 1, 'failed': 0, 'deactivated': 0}

        result = notify_technician_visit_assigned(visit)

        self.assertEqual(result['sent'], 1)
        notification = Notification.objects.get(user=technician)
        self.assertIn(visit.numero_tarea, notification.message)
        send_push.assert_called_once()
