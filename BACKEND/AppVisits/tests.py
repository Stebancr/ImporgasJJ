import base64
from datetime import date, time, timedelta
from decimal import Decimal
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
        self.technician = Credenciales.objects.create(
            usuario='visit-technician', estado=1, tipo_usuario=1,
        )
        self.client.force_authenticate(self.admin)
        customer = ClienteVisita.objects.create(
            nombre='Cliente PDF', identificacion='123', telefono='3000000000',
            correo='cliente@example.com', direccion='Calle de prueba',
        )
        self.visit = VisitaTecnica.objects.create(
            cliente=customer, tipo_tarea='mantenimiento', fecha=date.today(),
            hora=time(10, 0), descripcion='Prueba de visita', creado_por=self.admin,
        )

    def valid_create_payload(self):
        return {
            'cliente_nombre': 'Cliente con valor',
            'cliente_identificacion': '1234567890',
            'cliente_telefono': '3001234567',
            'cliente_correo': 'cliente@example.com',
            'cliente_direccion': 'Calle 10 # 20-30',
            'tipo_tarea': 'revision_periodica',
            'fecha': date.today().isoformat(),
            'hora': '08:30:00',
            'valor_visita': 150000,
            'tecnico_id': self.technician.pk,
        }

    def test_task_number_is_deterministic(self):
        self.assertEqual(self.visit.numero_tarea, str(999 + self.visit.id))
        second = VisitaTecnica.objects.create(
            cliente=self.visit.cliente, tipo_tarea='revision', fecha=date.today(), hora=time(11, 0)
        )
        self.assertEqual(second.numero_tarea, str(999 + second.id))

    def test_search_document_phone_and_service_choice(self):
        for field, term in (('document', '123'), ('phone', '3000000000')):
            result = self.client.get(reverse('visitas-list-create'), {'search': term, 'search_field': field})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(any(row['id'] == self.visit.pk for row in result.data))
        self.assertEqual(self.client.get(reverse('visitas-list-create'), {
            'search': 'abc', 'search_field': 'document',
        }).status_code, 400)
        payload = self.valid_create_payload()
        payload['tipo_tarea'] = 'not-an-option'
        self.assertEqual(self.client.post(reverse('visitas-list-create'), payload, format='json').status_code, 400)
        payload['tipo_tarea'] = 'revision_periodica'
        created = self.client.post(reverse('visitas-list-create'), payload, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['tipo_tarea_display'], 'REVISION PERIODICA')
        detail = self.client.get(reverse('visitas-detail', args=[created.data['id']]))
        self.assertEqual(detail.data['tipo_tarea'], 'revision_periodica')

    def test_visit_value_is_created_and_returned_as_json_number(self):
        payload = self.valid_create_payload()
        created = self.client.post(reverse('visitas-list-create'), payload, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['valor_visita'], 150000)
        self.assertIsInstance(created.data['valor_visita'], int)
        self.assertIsInstance(created.json()['valor_visita'], int)

        visit = VisitaTecnica.objects.get(pk=created.data['id'])
        self.assertEqual(visit.valor_visita, Decimal('150000.00'))
        detail = self.client.get(reverse('visitas-detail', args=[visit.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['valor_visita'], 150000)
        listed = self.client.get(reverse('visitas-list-create'))
        item = next(row for row in listed.data if row['id'] == visit.pk)
        self.assertEqual(item['valor_visita'], 150000)
        calendar = self.client.get(
            reverse('visitas-calendario'),
            {'mes': date.today().strftime('%Y-%m')},
        )
        calendar_item = next(
            row for rows in calendar.data.values() for row in rows if row['id'] == visit.pk
        )
        self.assertEqual(calendar_item['valor_visita'], 150000)

    def test_existing_visit_without_value_remains_compatible_and_negative_is_rejected(self):
        detail = self.client.get(reverse('visitas-detail', args=[self.visit.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data['valor_visita'])

        invalid = self.client.patch(
            reverse('visitas-detail', args=[self.visit.pk]),
            {'valor_visita': -1},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)
        self.visit.refresh_from_db()
        self.assertIsNone(self.visit.valor_visita)

    def test_create_requires_every_field_except_description_and_observations(self):
        response = self.client.post(reverse('visitas-list-create'), {}, format='json')
        self.assertEqual(response.status_code, 400)
        required = {
            'cliente_nombre', 'cliente_identificacion', 'cliente_telefono',
            'cliente_correo', 'cliente_direccion', 'tipo_tarea', 'fecha',
            'hora', 'valor_visita', 'tecnico_id',
        }
        self.assertTrue(required.issubset(response.data.keys()))
        self.assertNotIn('descripcion', response.data)
        self.assertNotIn('observaciones_iniciales', response.data)
        self.assertEqual(str(response.data['tecnico_id'][0]), 'Debe seleccionar un técnico.')

    def test_create_rejects_invalid_identity_phone_email_past_date_and_technician(self):
        cases = [
            ('cliente_identificacion', '123ABC', 'La cédula solo puede contener números.'),
            ('cliente_telefono', '300-123-4567', 'El número de celular solo puede contener números.'),
            ('cliente_correo', 'usuario@dominio', 'Ingrese un correo electrónico válido.'),
            ('fecha', (date.today() - timedelta(days=1)).isoformat(), 'La fecha de la visita no puede ser anterior al día actual.'),
            ('tecnico_id', self.admin.pk, 'Debe seleccionar un técnico válido y activo.'),
        ]
        for field, value, expected in cases:
            with self.subTest(field=field):
                payload = self.valid_create_payload()
                payload[field] = value
                response = self.client.post(reverse('visitas-list-create'), payload, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(str(response.data[field][0]), expected)

    def test_finalized_visit_cannot_be_patched_but_pending_visit_can(self):
        url = reverse('visitas-detail', args=[self.visit.pk])
        editable = self.client.patch(url, {'descripcion': 'Todavía editable'}, format='json')
        self.assertEqual(editable.status_code, 200)

        self.visit.refresh_from_db()
        self.visit.estado = VisitaTecnica.ESTADO_EN_PROCESO
        self.visit.save(update_fields=['estado', 'fecha_actualizacion'])
        in_progress = self.client.patch(url, {'descripcion': 'En proceso editable'}, format='json')
        self.assertEqual(in_progress.status_code, 200)

        self.visit.refresh_from_db()
        self.visit.estado = VisitaTecnica.ESTADO_FINALIZADA
        self.visit.save(update_fields=['estado', 'fecha_actualizacion'])
        blocked = self.client.patch(url, {'descripcion': 'Cambio no permitido'}, format='json')
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(blocked.data['detail'], 'No se puede modificar una visita que ya está finalizada.')
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.descripcion, 'En proceso editable')

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
            fecha=date.today(), hora=time(9, 0), valor_visita=Decimal('150000.00'),
        )
        send_push.return_value = {'sent': 1, 'failed': 0, 'deactivated': 0}

        result = notify_technician_visit_assigned(visit)

        self.assertEqual(result['sent'], 1)
        notification = Notification.objects.get(user=technician)
        self.assertIn(visit.numero_tarea, notification.message)
        send_push.assert_called_once()
        self.assertEqual(send_push.call_args.args[3]['valor_visita'], '150000.00')
