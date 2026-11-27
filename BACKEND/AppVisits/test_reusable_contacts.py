from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from usuarios.models import Credenciales
from .models import ClienteVisita, VisitaTecnica


class ReusableVisitContactsTests(APITestCase):
    def setUp(self):
        self.admin = Credenciales.objects.create(usuario='visit-admin-qa', tipo_usuario=4, estado=1)
        self.tech = Credenciales.objects.create(usuario='visit-tech-qa', tipo_usuario=1, estado=1)
        self.client.force_authenticate(self.admin)
        self.create_url = reverse('visitas-list-create')
        self.payload = {
            'registrar_cliente': True, 'cliente_nombre': 'Cliente de prueba',
            'cliente_telefono': '3001234567', 'cliente_correo': ' CLIENTE@example.com ',
            'cliente_direccion': 'Calle original', 'cliente_indicaciones_llegada': 'Portería original',
            'tipo_tarea': 'revision_periodica', 'fecha': str(timezone.localdate() + timedelta(days=1)),
            'hora': '09:00', 'tecnico_id': self.tech.pk,
        }

    def post(self, **changes):
        return self.client.post(self.create_url, {**self.payload, **changes}, format='json')

    def create_profile(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        return ClienteVisita.fichas().get()

    def test_select_and_reuse_with_independent_snapshot_and_history(self):
        profile = self.create_profile()
        first = profile.historial_visitas.get()
        for term in ('cliente de', '+57 300-123-4567', 'CLIENTE@EXAMPLE'):
            search = self.client.post(reverse('visitas-clientes-buscar'), {'term': term}, format='json')
            self.assertEqual([row['id'] for row in search.data], [profile.pk])
            self.assertIn('no-store', search['Cache-Control'])
            self.assertNotIn('correo_clave', search.data[0])
        second = self.post(registrar_cliente=False, cliente_registrado_id=profile.pk,
                           cliente_direccion='Calle de la segunda visita')
        self.assertEqual(second.status_code, 201, second.data)
        result = self.client.patch(reverse('visitas-cliente', args=[profile.pk]),
                                   {'telefono': '3007654321', 'direccion': 'Dirección actualizada'}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(first.cliente.telefono, '3001234567')
        self.assertEqual(first.cliente.direccion, 'Calle original')
        self.assertEqual(second.data['cliente']['direccion'], 'Calle de la segunda visita')
        self.assertEqual(ClienteVisita.fichas().count(), 1)
        self.assertEqual(Credenciales.objects.count(), 2)
        history = self.client.get(reverse('visitas-cliente-historial', args=[profile.pk]))
        self.assertEqual({row['id'] for row in history.data['results']}, {first.pk, second.data['id']})

    def test_conflicts_require_explicit_selection(self):
        first = self.create_profile()
        second_response = self.post(cliente_telefono='3002222222', cliente_correo='otro@example.com')
        self.assertEqual(second_response.status_code, 201)
        second = ClienteVisita.fichas().exclude(pk=first.pk).get()
        for phone, email, expected in (
            ('573001234567', 'tercero@example.com', [first.pk]),
            ('3003333333', ' OTRO@EXAMPLE.COM ', [second.pk]),
            ('3001234567', 'otro@example.com', [first.pk, second.pk]),
        ):
            response = self.post(cliente_telefono=phone, cliente_correo=email)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(list(map(int, response.data['cliente_coincidencias'])), expected)
        self.assertEqual(VisitaTecnica.objects.count(), 2)
        self.assertEqual(ClienteVisita.fichas().count(), 2)

    def test_failure_rolls_back_contact_and_snapshot(self):
        with patch('AppVisits.serializers.VisitaTecnica.objects.create', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.post()
        self.assertFalse(ClienteVisita.objects.exists())
        self.assertFalse(VisitaTecnica.objects.exists())

    def test_legacy_visit_still_works_and_technician_cannot_access_contacts(self):
        profile = self.create_profile()
        old = self.post(registrar_cliente=False)
        self.assertEqual(old.status_code, 201)
        self.assertIsNone(VisitaTecnica.objects.get(pk=old.data['id']).cliente_registrado_id)
        self.client.force_authenticate(self.tech)
        self.assertEqual(self.client.get(reverse('visitas-detail', args=[old.data['id']])).status_code, 200)
        self.assertEqual(self.client.post(reverse('visitas-clientes-buscar'), {'term': 'cliente'}, format='json').status_code, 403)
        detail = reverse('visitas-cliente', args=[profile.pk])
        self.assertEqual(self.client.get(detail).status_code, 403)
        self.assertEqual(self.client.patch(detail, {'telefono': '3000000000'}, format='json').status_code, 403)
        self.assertEqual(self.client.get(reverse('visitas-cliente-historial', args=[profile.pk])).status_code, 403)
