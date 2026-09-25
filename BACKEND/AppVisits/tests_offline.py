import base64
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from datetime import date, time
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from pypdf import PdfReader
from usuarios.models import Credenciales
from .models import ClienteVisita, VisitaTecnica, EvidenciaFotografica, ReporteVisita, VisitSyncReceipt, CambioCostoVisita
from .sync_version import visit_sync_version

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


class OfflineSyncTests(APITestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp(prefix='visits-offline-test-')
        self.settings_override = override_settings(MEDIA_ROOT=self.media)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media)
        self.tech = Credenciales.objects.create(usuario='offline-tech', tipo_usuario=1, estado=1)
        self.other = Credenciales.objects.create(usuario='other-tech', tipo_usuario=1, estado=1)
        customer = ClienteVisita.objects.create(nombre='Cliente', direccion='Calle 1')
        self.visit = VisitaTecnica.objects.create(cliente=customer, tecnico=self.tech, tipo_tarea='revision', fecha=date.today(), hora=time(9))
        self.url = reverse('visitas-sincronizar', args=[self.visit.pk])
        self.version = visit_sync_version(self.visit)
        self.client.force_authenticate(self.tech)

    def payload(self):
        return {'persona_atiende': 'Cliente', 'equipo': 'otro', 'equipo_otro': 'Especial', 'ubicacion_equipo': 'otro', 'ubicacion_otro': 'Terraza', 'motivo_servicio': 'Revisión', 'solucion_realizada': 'Ajuste', 'observaciones': 'Nota', 'recomendaciones': 'Anual', 'valor_servicio': '', 'metodo_pago': 'efectivo', 'firma_base64': base64.b64encode(PNG).decode(), 'fotos': [SimpleUploadedFile('photo.png', PNG, content_type='image/png')]}

    def send(self, *, key='operation-00000001', version=None, payload=None):
        return self.client.post(self.url, self.payload() if payload is None else payload, format='multipart', HTTP_IDEMPOTENCY_KEY=key, HTTP_IF_MATCH=version or self.version)

    @patch('AppVisits.views._enviar_correo_visita_completada')
    def test_lost_response_replays_same_receipt_without_duplicate_rows_or_email(self, email):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.send()
        self.assertEqual(first.status_code, 200, first.data)
        second = self.send()
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data, first.data)
        self.assertEqual(second['Idempotency-Replayed'], 'true')
        self.assertEqual(EvidenciaFotografica.objects.count(), 1)
        self.assertEqual(ReporteVisita.objects.count(), 1)
        self.assertEqual(VisitSyncReceipt.objects.count(), 1)
        email.assert_called_once()
        report = ReporteVisita.objects.get()
        self.assertEqual(report.observaciones, 'Nota')
        self.assertEqual(report.equipo_otro, 'Especial')
        self.assertEqual(report.ubicacion_otro, 'Terraza')
        self.assertIsNone(report.valor_servicio)

    def test_reusing_key_with_changed_payload_is_rejected(self):
        self.assertEqual(self.send().status_code, 200)
        data = self.payload(); data['observaciones'] = 'Cambió'
        self.assertEqual(self.send(payload=data).status_code, 409)
        self.assertEqual(EvidenciaFotografica.objects.count(), 1)

    def test_stale_version_rejects_all_writes(self):
        self.visit.descripcion = 'Nueva orden'; self.visit.save()
        self.assertEqual(self.send().status_code, 412)
        self.assertFalse(ReporteVisita.objects.exists())
        self.assertFalse(EvidenciaFotografica.objects.exists())
        self.assertFalse(VisitSyncReceipt.objects.exists())

    def test_changed_arrival_directions_invalidate_old_offline_snapshot(self):
        self.visit.cliente.indicaciones_llegada = 'Acceso por portería norte'
        self.visit.cliente.save(update_fields=['indicaciones_llegada'])
        self.assertEqual(self.send().status_code, 412)
        self.assertFalse(EvidenciaFotografica.objects.exists())

    def test_reassignment_and_ecommerce_account_cannot_access_visit(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.send().status_code, 404)
        ecommerce = Credenciales.objects.create(usuario='shopper', tipo_usuario=0, estado=1)
        self.client.force_authenticate(ecommerce)
        self.assertEqual(self.send().status_code, 403)
        self.assertEqual(self.client.get(reverse('visitas-list-create')).data, [])

    def test_invalid_photo_or_signature_does_not_partially_complete(self):
        data = self.payload(); data['fotos'].append(SimpleUploadedFile('bad.png', b'invalid', content_type='image/png'))
        self.assertEqual(self.send(payload=data).status_code, 400)
        data = self.payload(); data['firma_base64'] = 'invalid'
        self.assertEqual(self.send(payload=data).status_code, 400)
        data = self.payload(); data['valor_servicio'] = '-1'
        self.assertEqual(self.send(payload=data).status_code, 400)
        self.assertFalse(EvidenciaFotografica.objects.exists())
        self.assertFalse(ReporteVisita.objects.exists())
        self.visit.refresh_from_db(); self.assertEqual(self.visit.estado, 'pendiente')

    def test_completion_without_signature_updates_cost_and_replay_does_not_duplicate_photo(self):
        data = self.payload()
        data['firma_base64'] = ''
        data['valor_servicio'] = '85000'
        with self.captureOnCommitCallbacks(execute=True):
            first = self.send(payload=data)
        self.assertEqual(first.status_code, 200, first.data)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.valor_visita, 85000)
        self.assertFalse(ReporteVisita.objects.get(visita=self.visit).firma_cliente)
        replay_data = self.payload()
        replay_data['firma_base64'] = ''
        replay_data['valor_servicio'] = '85000'
        replay = self.send(payload=replay_data)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertEqual(EvidenciaFotografica.objects.filter(visita=self.visit).count(), 1)

    def test_blank_completion_cost_keeps_existing_initial_value(self):
        self.visit.costo_inicial = Decimal('45000.00')
        self.visit.valor_visita = Decimal('45000.00')
        self.visit.save(update_fields=['costo_inicial', 'valor_visita'])
        self.version = visit_sync_version(self.visit)
        response = self.send()
        self.assertEqual(response.status_code, 200, response.data)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.costo_inicial, Decimal('45000.00'))
        self.assertEqual(self.visit.valor_visita, Decimal('45000.00'))
        self.assertEqual(ReporteVisita.objects.get(visita=self.visit).valor_servicio, Decimal('45000.00'))
        self.assertFalse(CambioCostoVisita.objects.filter(visita=self.visit).exists())

    @patch('AppVisits.views._enviar_correo_visita_completada')
    def test_final_cost_and_reason_are_atomic_audited_and_idempotent(self, email):
        self.visit.costo_inicial = Decimal('45000.00')
        self.visit.valor_visita = Decimal('45000.00')
        self.visit.save(update_fields=['costo_inicial', 'valor_visita'])
        self.version = visit_sync_version(self.visit)
        data = self.payload()
        data['valor_servicio'] = '70000'
        self.assertEqual(self.send(payload=data).status_code, 400)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.valor_visita, Decimal('45000.00'))
        self.assertFalse(EvidenciaFotografica.objects.exists())
        data = self.payload()
        data['valor_servicio'] = '70000'
        data['motivo_cambio_costo'] = 'Se agregó cambio de regulador'
        with self.captureOnCommitCallbacks(execute=True):
            response = self.send(payload=data)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['costo_inicial'], 45000)
        self.assertEqual(response.data['costo_final'], 70000)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.costo_inicial, Decimal('45000.00'))
        self.assertEqual(self.visit.valor_visita, Decimal('70000.00'))
        self.assertEqual(ReporteVisita.objects.get(visita=self.visit).valor_servicio, Decimal('70000.00'))
        change = CambioCostoVisita.objects.get(visita=self.visit)
        self.assertEqual(change.usuario_id, self.tech.pk)
        self.assertEqual(change.motivo, 'Se agregó cambio de regulador')
        self.assertIn('70,000', ''.join(page.extract_text() or '' for page in PdfReader(BytesIO(self.visit.pdf_final.read())).pages))
        replay_data = self.payload()
        replay_data['valor_servicio'] = '70000'
        replay_data['motivo_cambio_costo'] = 'Se agregó cambio de regulador'
        replay = self.send(payload=replay_data)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay['Idempotency-Replayed'], 'true')
        self.assertEqual(CambioCostoVisita.objects.filter(visita=self.visit).count(), 1)
        self.assertEqual(EvidenciaFotografica.objects.filter(visita=self.visit).count(), 1)
        self.assertEqual(self.client.patch(reverse('visitas-costo', args=[self.visit.pk]), {'valor_visita': 90000, 'motivo_cambio_costo': 'Más trabajo'}, format='json').status_code, 403)

    def test_receipt_write_failure_rolls_back_report_photos_and_status(self):
        with patch.object(VisitSyncReceipt.objects, 'create', side_effect=RuntimeError('simulated commit failure')):
            with self.assertRaises(RuntimeError):
                self.send()
        self.assertFalse(EvidenciaFotografica.objects.exists())
        self.assertFalse(ReporteVisita.objects.exists())
        self.visit.refresh_from_db(); self.assertEqual(self.visit.estado, 'pendiente')
        from pathlib import Path
        self.assertEqual([p for p in Path(self.media).rglob('*') if p.is_file()], [])

    def test_capability_and_version_advertised_without_changing_legacy_fields(self):
        response = self.client.get(reverse('visitas-detail', args=[self.visit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['offline_sync_supported'])
        self.assertEqual(response.data['sync_version'], self.version)
        self.assertEqual(response.data['cliente']['nombre'], 'Cliente')

    def test_missing_headers_and_new_operation_for_closed_visit_are_rejected(self):
        response = self.client.post(self.url, self.payload(), format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.send().status_code, 200)
        self.assertEqual(self.send(key='operation-00000002').status_code, 412)
