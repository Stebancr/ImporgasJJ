from .sync_version import serialize_visit_mutation
import io
import os
import base64
import re
import json
import ipaddress
import hashlib
import unicodedata
from datetime import datetime, date, timedelta
from decimal import Decimal
from xml.sax.saxutils import escape
from urllib.parse import urlencode, urlparse

from django.http import HttpResponse, FileResponse
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import serializers

from .models import VisitaTecnica, ReporteVisita, EvidenciaFotografica, ClienteVisita, TipoVisita, CambioCostoVisita
from .serializers import (
    VisitaListSerializer, VisitaDetailSerializer,
    VisitaCreateSerializer, VisitaUpdateSerializer,
    ReporteSerializer, ReporteCreateSerializer,
    EvidenciaSerializer, EvidenciaResponseSerializer, TecnicoSerializer, ClienteVisitaSerializer, TipoVisitaSerializer,
)
from .permissions import IsAdminOrReadOwn, IsAdminUser
from .notifications import notify_technician_visit_assigned
from usuarios.models import Credenciales

logger = logging.getLogger(__name__)


def _filter_visitas_by_user(qs, user):
    """Filtra visitas: técnicos solo ven sus propias visitas, admins ven todas."""
    tipo = getattr(user, 'tipo_usuario', 0)
    if tipo < 1 or not user.is_active:
        return qs.none()
    if tipo == 1:  # Técnico (tipo_usuario = 1)
        qs = qs.filter(tecnico=user)
    return qs


def _set_visit_cost(visita, value, actor, motivo=''):
    if visita.valor_visita == value:
        return False
    motivo = str(motivo or '').strip()
    if visita.costo_inicial is not None and value != visita.costo_inicial and not motivo:
        raise serializers.ValidationError({'motivo_cambio_costo': 'Indica el motivo del cambio respecto al costo inicial.'})
    previous = visita.valor_visita
    visita.valor_visita = value
    visita.save(update_fields=['valor_visita', 'fecha_actualizacion'])
    ReporteVisita.objects.filter(visita=visita).update(valor_servicio=value)
    CambioCostoVisita.objects.create(
        visita=visita, usuario=actor, valor_anterior=previous, valor_nuevo=value, motivo=motivo,
    )
    return True


def _schedule_visit_assignment_notification(visita_id):
    """Envía FCM solo después de que la asignación quedó confirmada en BD."""
    def send_notification():
        visita = VisitaTecnica.objects.select_related('cliente', 'tecnico').get(pk=visita_id)
        notify_technician_visit_assigned(visita)

    transaction.on_commit(send_notification)


def _enviar_correo_visita_completada(visita):
    """Envía una sola vez el reporte final usando la configuración SMTP existente."""
    if visita.correo_completada_en:
        return False


    destinatario = (visita.cliente.correo or '').strip()
    if not destinatario:
        visita.correo_completada_error = 'El cliente no tiene correo configurado.'
        visita.save(update_fields=['correo_completada_error', 'fecha_actualizacion'])
        return False
    try:
        if not visita.pdf_final or visita.pdf_estado != 'generado':
            raise ValueError('El PDF definitivo todavía no está disponible.')
        with visita.pdf_final.open('rb') as saved_pdf:
            pdf = saved_pdf.read()
        if len(pdf) != visita.pdf_bytes or hashlib.sha256(pdf).hexdigest() != visita.pdf_sha256:
            raise ValueError('El PDF definitivo no superó la validación de integridad.')
        message = EmailMessage(
            subject=f'Visita técnica #{visita.numero_tarea} completada',
            body=(
                f'Hola {visita.cliente.nombre},\n\n'
                f'La visita técnica #{visita.numero_tarea} fue completada. '
                'Adjuntamos el informe técnico en formato PDF.\n\n'
                'Atentamente,\nIMPORGAS JJ'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        message.attach(f'reporte_{visita.numero_tarea}.pdf', pdf, 'application/pdf')
        message.send(fail_silently=False)
        visita.correo_completada_en = timezone.now()
        visita.correo_completada_error = ''
        visita.save(update_fields=['correo_completada_en', 'correo_completada_error', 'fecha_actualizacion'])
        return True
    except Exception as exc:
        logger.exception('No fue posible enviar el reporte de la visita %s', visita.pk)
        visita.correo_completada_error = str(exc)[:1000]
        visita.save(update_fields=['correo_completada_error', 'fecha_actualizacion'])
        return False


def _normalized_colombian_phone(value):
    digits = re.sub(r'\D', '', str(value or ''))
    if len(digits) == 10 and digits.startswith('3'):
        return '57' + digits
    if len(digits) == 12 and digits.startswith('573'):
        return digits
    return ''


def _valid_public_https_base(value):
    parsed = urlparse(value)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not host or '.' not in host or host.endswith(('.local', '.internal')):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def _valid_pdf_link_base(value):
    if _valid_public_https_base(value):
        return True
    parsed = urlparse(value)
    return (settings.DEBUG and parsed.scheme == 'http'
            and parsed.hostname == 'localhost' and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.path in ('', '/'))


def _pdf_filename(visit):
    number = re.sub(r'[^A-Za-z0-9-]', '', str(visit.numero_tarea or visit.pk)) or str(visit.pk)
    if number.isdecimal():
        number = f'{int(number):06d}'
    name = unicodedata.normalize('NFKD', visit.cliente.nombre or '')
    name = name.encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^A-Za-z0-9]+', '-', name).strip('-')[:60].strip('-') or 'Cliente'
    return f'VISITA-{number}-{name}.pdf'


def _public_pdf_url(visit):
    base = settings.FRONTEND_PUBLIC_URL.rstrip('/')
    if (visit.estado != VisitaTecnica.ESTADO_FINALIZADA or not visit.pdf_final
            or visit.pdf_estado in ('error', 'fallido', 'procesando')
            or (visit.pdf_source_hash and visit.pdf_source_hash != _pdf_source_hash(visit))
            or not _valid_pdf_link_base(base)):
        return None
    token = signing.dumps({
        'visit_id': visit.pk, 'version': visit.pdf_link_version,
    }, salt='visita-pdf-publico')
    return f'{base}/api{reverse("visitas-pdf-publico", args=[visit.pk])}?{urlencode({"token": token})}'


def _pdf_source_hash(visit):
    report = visit.reporte
    payload = {
        'visit': [visit.pk, visit.numero_tarea, visit.estado, visit.fecha, visit.hora,
                  visit.tipo_tarea, visit.tipo_tarea_etiqueta, visit.descripcion,
                  visit.valor_visita, visit.tecnico_id, visit.creado_por_id],
        'client': [visit.cliente.nombre, visit.cliente.identificacion, visit.cliente.telefono,
                   visit.cliente.correo, visit.cliente.direccion],
        'report': [report.pk, report.actualizado_en, report.firma_cliente.name,
                   report.firma_base64],
        # Las fotos temporales conservan su identidad después de vaciar el
        # campo de archivo; así el PDF definitivo sigue vigente tras limpiarlas.
        'photos': [(photo.pk, 'temporal' if photo.es_temporal else photo.imagen.name,
                    photo.subida_en) for photo in visit.evidencias.all()],
    }
    return hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()


def _persist_visit_pdf(visit_id, created_files=None):
    """Confirma la finalización sólo después de guardar y validar el PDF."""
    from pypdf import PdfReader
    with transaction.atomic():
        visit = VisitaTecnica.objects.select_for_update().get(pk=visit_id)
        if not hasattr(visit, 'reporte'):
            raise ValueError('La visita no tiene reporte.')
        visit.estado = VisitaTecnica.ESTADO_FINALIZADA
        source_hash = _pdf_source_hash(visit)
        if (visit.pdf_source_hash == source_hash and visit.pdf_final
                and visit.pdf_final.storage.exists(visit.pdf_final.name)):
            with visit.pdf_final.storage.open(visit.pdf_final.name, 'rb') as existing_pdf:
                stored_pdf = existing_pdf.read()
            if (hashlib.sha256(stored_pdf).hexdigest() != visit.pdf_sha256
                    or len(stored_pdf) != visit.pdf_bytes
                    or not PdfReader(io.BytesIO(stored_pdf)).pages):
                raise ValueError('El PDF definitivo guardado no superó la validación de integridad.')
            if VisitaTecnica.objects.filter(pk=visit.pk).exclude(estado=VisitaTecnica.ESTADO_FINALIZADA).exists():
                visit.pdf_estado = 'generado'
                visit.save(update_fields=['estado', 'pdf_estado', 'fecha_actualizacion'])
            transaction.on_commit(lambda: _purge_temporary_images(visit_id), robust=True)
            return visit
        if visit.evidencias.filter(es_temporal=True, imagen='').exists():
            raise ValueError('No se puede regenerar un informe cuyas imágenes temporales ya se eliminaron.')
        pdf = _generar_pdf(visit)
        if not pdf.startswith(b'%PDF-') or not PdfReader(io.BytesIO(pdf)).pages:
            raise ValueError('El PDF generado no es válido.')
        digest = hashlib.sha256(pdf).hexdigest()
        name = f'visitas_pdf/{visit.pk}/{digest[:16]}/{_pdf_filename(visit)}'
        storage = visit.pdf_final.storage
        saved_new = False
        if storage.exists(name):
            with storage.open(name, 'rb') as existing:
                if hashlib.sha256(existing.read()).hexdigest() != digest:
                    raise ValueError('Existe un archivo PDF distinto con el mismo nombre.')
        else:
            stored = storage.save(name, ContentFile(pdf))
            if stored != name:
                storage.delete(stored)
                raise ValueError('No se pudo reservar el nombre del PDF.')
            saved_new = True
            if created_files is not None:
                created_files.append((storage, name))
        with storage.open(name, 'rb') as saved_pdf:
            persisted_bytes = saved_pdf.read()
        if hashlib.sha256(persisted_bytes).hexdigest() != digest or not PdfReader(io.BytesIO(persisted_bytes)).pages:
            if saved_new:
                storage.delete(name)
            raise ValueError('El PDF guardado no superó la validación de integridad.')
        visit.pdf_final.name = name
        visit.pdf_sha256 = digest
        visit.pdf_source_hash = source_hash
        visit.pdf_bytes = len(pdf)
        visit.pdf_generado_en = timezone.now()
        visit.pdf_estado = 'generado'
        visit.pdf_error = ''
        try:
            visit.save(update_fields=['estado', 'fecha_actualizacion', 'pdf_final', 'pdf_sha256', 'pdf_source_hash',
                                      'pdf_bytes', 'pdf_generado_en', 'pdf_estado', 'pdf_error'])
        except Exception:
            if saved_new:
                storage.delete(name)
            raise
        transaction.on_commit(lambda: _purge_temporary_images(visit_id), robust=True)
    return visit


def _purge_temporary_images(visit_id):
    """Desvincula sólo archivos nuevos tras confirmar el PDF; nunca toca fotos históricas."""
    evidence_ids = list(EvidenciaFotografica.objects.filter(
        visita_id=visit_id, es_temporal=True, eliminada_en__isnull=True,
    ).exclude(imagen='').values_list('pk', flat=True))
    for evidence_id in evidence_ids:
        with transaction.atomic():
            evidence = EvidenciaFotografica.objects.select_for_update().select_related('visita').get(pk=evidence_id)
            visit = evidence.visita
            if (visit.estado != VisitaTecnica.ESTADO_FINALIZADA or not visit.pdf_final
                    or visit.pdf_estado != 'generado' or not visit.pdf_final.storage.exists(visit.pdf_final.name)):
                return
            storage, name = evidence.imagen.storage, evidence.imagen.name
            if not name:
                continue
            evidence.imagen = ''
            evidence.eliminada_en = timezone.now()
            evidence.archivada_en = evidence.eliminada_en
            evidence.save(update_fields=['imagen', 'eliminada_en', 'archivada_en'])
        try:
            storage.delete(name)
        except Exception:
            logger.exception('No se pudo eliminar un archivo temporal de la visita %s', visit_id)


def _save_pdf_and_notify(visita_id):
    """Finalizar tras el PDF; avisar sólo en chat reactivo verificado."""
    from crmChat.models import ChatSession, ChatMessage, ChannelIntegration
    from crmChat.apps.meta.services import dispatch_outbound_message

    visit = VisitaTecnica.objects.select_related('cliente', 'reporte', 'creado_por').get(pk=visita_id)
    if not hasattr(visit, 'reporte'):
        return
    try:
        visit = _persist_visit_pdf(visita_id)
    except Exception:
        logger.exception('No fue posible guardar PDF de visita %s', visita_id)
        visit.pdf_estado = 'fallido'
        visit.pdf_error = 'No se pudo generar o guardar el PDF. Reintenta desde el CRM.'
        visit.whatsapp_notificacion_estado = 'error'
        visit.whatsapp_notificacion_error = 'No se pudo generar el PDF.'
        visit.save(update_fields=['pdf_estado', 'pdf_error', 'whatsapp_notificacion_estado', 'whatsapp_notificacion_error'])
        return

    _enviar_correo_visita_completada(visit)

    phone = _normalized_colombian_phone(visit.cliente.telefono)
    if not phone:
        reason = 'Número del cliente no verificable para WhatsApp Web.'
    else:
        sessions = ChatSession.objects.select_related('integration', 'contact').filter(
            channel=ChannelIntegration.CHANNEL_WHATSAPP_WEB,
            status__in=['bot', 'waiting', 'active'],
            integration__active=True,
            integration__connection_status='connected',
            last_customer_message_at__gte=timezone.now() - timedelta(hours=24),
        ).order_by('-last_customer_message_at')
        session = next((item for item in sessions if
            item.external_thread_id == f'{phone}@s.whatsapp.net' and
            item.contact and _normalized_colombian_phone(item.contact.phone) == phone and
            item.messages.filter(sender_type='user', direction='inbound', external_message_id__isnull=False).exists()
        ), None)
        reason = '' if session else 'Sin conversación reciente de WhatsApp Web con número verificado.'
    public_base = settings.FRONTEND_PUBLIC_URL.rstrip('/')
    if not reason and not _valid_public_https_base(public_base):
        reason = 'La URL pública HTTPS no está configurada.'
    if reason:
        visit.whatsapp_notificacion_estado = 'manual'
        visit.whatsapp_notificacion_error = reason
        visit.save(update_fields=['whatsapp_notificacion_estado', 'whatsapp_notificacion_error'])
        return

    link = _public_pdf_url(visit)
    text = f'La visita técnica #{visit.numero_tarea} ha finalizado. Descargue el informe: {link}'
    message, created = ChatMessage.objects.get_or_create(
        client_message_id=f'visit-pdf-{visit.pk}',
        defaults={
            'session': session, 'text': text, 'sender_type': 'agent',
            'direction': 'outbound', 'status': 'queued',
            'metadata': {'origin': 'visit_completion', 'visit_id': visit.pk},
        },
    )
    if not created:
        return
    try:
        dispatch_outbound_message(message)
        visit.whatsapp_notificacion_estado = 'enviada'
        visit.whatsapp_notificacion_error = ''
    except Exception as exc:
        logger.warning('No se pudo entregar PDF de visita %s mediante WhatsApp Web: %s', visit.pk, type(exc).__name__)
        visit.whatsapp_notificacion_estado = 'error'
        visit.whatsapp_notificacion_error = str(exc)[:300]
    visit.save(update_fields=['whatsapp_notificacion_estado', 'whatsapp_notificacion_error'])


def _refresh_saved_pdf(visita_id):
    visit = VisitaTecnica.objects.select_related('cliente', 'reporte', 'creado_por').get(pk=visita_id)
    if visit.estado != VisitaTecnica.ESTADO_FINALIZADA or not hasattr(visit, 'reporte'):
        return
    try:
        _persist_visit_pdf(visita_id)
    except Exception:
        logger.exception('No fue posible actualizar PDF de visita %s', visita_id)
        VisitaTecnica.objects.filter(pk=visita_id).update(
            pdf_estado='error', pdf_error='No se pudo actualizar el PDF. Reintenta desde el CRM.',
        )
# ─── Technicians list ──────────────────────────────────────────────────────────

class TecnicosView(APIView):
    """Lista de usuarios con tipo_usuario == 0 (técnicos/colaboradores)."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        tecnicos = Credenciales.objects.filter(
            tipo_usuario=1, estado=1
        ).select_related('usuario_rel').order_by('usuario')
        data = TecnicoSerializer(tecnicos, many=True).data
        return Response(data)


class TiposVisitaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'tipo_usuario', 0) < 1:
            return Response({'detail': 'No permitido.'}, status=403)
        qs = TipoVisita.objects.all() if request.user.tipo_usuario >= 2 else TipoVisita.objects.filter(activo=True)
        return Response(TipoVisitaSerializer(qs, many=True).data)

    def post(self, request):
        if getattr(request.user, 'tipo_usuario', 0) < 2:
            return Response({'detail': 'Solo administradores.'}, status=403)
        serializer = TipoVisitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(TipoVisitaSerializer(serializer.save()).data, status=201)


class TipoVisitaDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        try:
            item = TipoVisita.objects.get(pk=pk)
        except TipoVisita.DoesNotExist:
            return Response({'detail': 'Tipo no encontrado.'}, status=404)
        serializer = TipoVisitaSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(TipoVisitaSerializer(serializer.save()).data)


# ─── Visits list / create ──────────────────────────────────────────────────────

class VisitaListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        qs = VisitaTecnica.objects.select_related(
            'cliente', 'tecnico', 'tecnico__usuario_rel', 'creado_por', 'creado_por__usuario_rel'
        ).prefetch_related('evidencias')

        qs = _filter_visitas_by_user(qs, request.user)

        # Filters
        estado = request.query_params.get('estado')
        if estado and estado != 'all':
            qs = qs.filter(estado=estado)

        tecnico_id = request.query_params.get('tecnico_id')
        if tecnico_id:
            qs = qs.filter(tecnico_id=tecnico_id)

        fecha = request.query_params.get('fecha')
        if fecha:
            qs = qs.filter(fecha=fecha)

        mes = request.query_params.get('mes')  # format: YYYY-MM
        if mes:
            try:
                y, m = mes.split('-')
                qs = qs.filter(fecha__year=int(y), fecha__month=int(m))
            except Exception:
                pass

        search = request.query_params.get('search', '').strip()
        search_field = request.query_params.get('search_field', 'all')
        if search_field not in ('all', 'document', 'phone'):
            return Response({'search_field': 'Filtro de búsqueda inválido.'}, status=400)
        if search_field != 'all' and search and (not search.isascii() or not search.isdecimal() or len(search) > 15):
            return Response({'search': 'Usa hasta 15 dígitos para buscar documento o teléfono.'}, status=400)
        if search:
            if search_field == 'document':
                qs = qs.filter(cliente__identificacion__icontains=search)
            elif search_field == 'phone':
                qs = qs.filter(cliente__telefono__icontains=search)
            else:
                qs = qs.filter(
                    Q(cliente__nombre__icontains=search) |
                    Q(cliente__identificacion__icontains=search) |
                    Q(cliente__telefono__icontains=search) |
                    Q(cliente__direccion__icontains=search) |
                    Q(numero_tarea__icontains=search)
                )

        serializer = VisitaListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        tipo = getattr(request.user, 'tipo_usuario', 0)
        if tipo < 2:
            return Response({'error': 'Solo administradores pueden crear visitas.'}, status=403)

        complete_now = str(request.data.get('completar_ahora', '')).lower() in ('true', '1')
        if request.data.get('completar_ahora') not in (None, '', False, True, 'true', 'false', '1', '0'):
            return Response({'completar_ahora': 'Valor inválido.'}, status=400)
        photos = request.FILES.getlist('fotos')
        if photos and not complete_now:
            return Response({'fotos': 'Las imágenes corresponden al flujo de completar ahora.'}, status=400)
        if len(photos) > 20:
            return Response({'fotos': 'Máximo 20 fotografías.'}, status=400)
        for photo in photos:
            evidence = EvidenciaSerializer(data={'imagen': photo})
            evidence.is_valid(raise_exception=True)
            photo.seek(0)
        signature = request.FILES.get('firma_cliente')
        if signature and not complete_now:
            return Response({'firma_cliente': 'La firma sólo corresponde a una visita completada.'}, status=400)
        if signature:
            if signature.size > 1024 * 1024:
                return Response({'firma_cliente': 'La firma no puede superar 1 MB.'}, status=400)
            serializers.ImageField().run_validation(signature)
            signature.seek(0)
        report_data = {}
        report_serializer = None
        if complete_now:
            try:
                report_data = json.loads(request.data.get('reporte', '{}'))
            except (TypeError, ValueError):
                return Response({'reporte': 'JSON inválido.'}, status=400)
            if not isinstance(report_data, dict):
                return Response({'reporte': 'Debe ser un objeto.'}, status=400)
            for field in ('persona_atiende', 'motivo_servicio', 'solucion_realizada'):
                if not str(report_data.get(field, '')).strip():
                    return Response({'reporte': {field: 'Este campo es obligatorio.'}}, status=400)
            for selector, extra in (('equipo', 'equipo_otro'), ('ubicacion_equipo', 'ubicacion_otro')):
                if report_data.get(selector) == 'otro' and not str(report_data.get(extra, '')).strip():
                    return Response({'reporte': {extra: 'Especifica el valor de otro.'}}, status=400)
            raw_cost = request.data.get('valor_visita')
            report_data['valor_servicio'] = None if raw_cost in ('', None) else raw_cost
            report_serializer = ReporteCreateSerializer(data=report_data)
            report_serializer.is_valid(raise_exception=True)
        serializer = VisitaCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            with transaction.atomic():
                visita = serializer.save()
                for index, photo in enumerate(photos):
                    EvidenciaFotografica.objects.create(visita=visita, imagen=photo, orden=index, es_temporal=True)
                if visita.valor_visita is not None:
                    CambioCostoVisita.objects.create(
                        visita=visita, usuario=request.user, valor_anterior=None, valor_nuevo=visita.valor_visita,
                    )
                if report_serializer:
                    report = report_serializer.save(visita=visita)
                    if signature:
                        report.firma_cliente = signature
                        report.save(update_fields=['firma_cliente'])
                    visita.pdf_estado = 'procesando'
                    visita.save(update_fields=['pdf_estado'])
                    try:
                        visita = _persist_visit_pdf(visita.pk)
                    except Exception:
                        logger.exception('No fue posible completar PDF de visita %s', visita.pk)
                        visita.pdf_estado = 'fallido'
                        visita.pdf_error = 'No se pudo generar o guardar el PDF. Reintenta desde el CRM.'
                        visita.save(update_fields=['pdf_estado', 'pdf_error'])
                    else:
                        transaction.on_commit(lambda visit_id=visita.pk: _save_pdf_and_notify(visit_id), robust=True)
                if visita.tecnico_id and not complete_now:
                    _schedule_visit_assignment_notification(visita.pk)
            return Response(VisitaDetailSerializer(visita).data, status=201)
        return Response(serializer.errors, status=400)


# ─── Visit detail / update / delete ───────────────────────────────────────────

class VisitaDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOwn]

    def _get_visita(self, pk, user):
        try:
            qs = VisitaTecnica.objects.select_related(
                'cliente', 'tecnico', 'tecnico__usuario_rel', 'creado_por'
            ).prefetch_related('evidencias')
            qs = _filter_visitas_by_user(qs, user)
            v = qs.get(pk=pk)
        except VisitaTecnica.DoesNotExist:
            return None, Response({'error': 'Visita no encontrada.'}, status=404)
        return v, None

    def get(self, request, pk):
        self._request = request
        v, err = self._get_visita(pk, request.user)
        if err:
            return err
        return Response(VisitaDetailSerializer(v).data)

    @serialize_visit_mutation
    def patch(self, request, pk):
        self._request = request
        tipo = getattr(request.user, 'tipo_usuario', 0)
        if tipo < 2:
            return Response({'error': 'No permitido.'}, status=403)
        v, err = self._get_visita(pk, request.user)
        if err:
            return err
        if v.estado == VisitaTecnica.ESTADO_FINALIZADA:
            return Response(
                {'detail': 'No se puede modificar una visita que ya está finalizada.'},
                status=400,
            )
        previous_technician_id = v.tecnico_id
        previous_cost = v.valor_visita
        motivo = request.data.get('motivo_cambio_costo', '')
        serializer = VisitaUpdateSerializer(v, data=request.data, partial=True)
        if serializer.is_valid():
            visita = serializer.save()
            if visita.valor_visita != previous_cost:
                if visita.costo_inicial is not None and visita.valor_visita != visita.costo_inicial and not str(motivo).strip():
                    raise serializers.ValidationError({'motivo_cambio_costo': 'Indica el motivo del cambio.'})
                CambioCostoVisita.objects.create(
                    visita=visita, usuario=request.user,
                    valor_anterior=previous_cost, valor_nuevo=visita.valor_visita, motivo=str(motivo).strip(),
                )
                ReporteVisita.objects.filter(visita=visita).update(valor_servicio=visita.valor_visita)
            if visita.tecnico_id and visita.tecnico_id != previous_technician_id:
                _schedule_visit_assignment_notification(visita.pk)
            return Response(VisitaDetailSerializer(v).data)
        return Response(serializer.errors, status=400)


    @serialize_visit_mutation
    def delete(self, request, pk):
        self._request = request
        tipo = getattr(request.user, 'tipo_usuario', 0)
        if tipo < 2:
            return Response({'error': 'No permitido.'}, status=403)
        v, err = self._get_visita(pk, request.user)
        if err:
            return err
        v.delete()
        return Response(status=204)


class CostoVisitaView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if getattr(request.user, 'tipo_usuario', 0) < 1:
            return Response({'detail': 'No permitido.'}, status=403)
        field = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, min_value=Decimal('0'))
        if 'valor_visita' not in request.data:
            return Response({'valor_visita': 'Este campo es obligatorio.'}, status=400)
        try:
            raw_value = request.data['valor_visita']
            value = None if raw_value == '' else field.run_validation(raw_value)
        except serializers.ValidationError as exc:
            return Response({'valor_visita': exc.detail}, status=400)
        with transaction.atomic():
            qs = _filter_visitas_by_user(VisitaTecnica.objects.select_for_update(), request.user)
            try:
                visita = qs.get(pk=pk)
            except VisitaTecnica.DoesNotExist:
                return Response({'detail': 'Visita no encontrada o no asignada.'}, status=404)
            if visita.estado in (VisitaTecnica.ESTADO_FINALIZADA, VisitaTecnica.ESTADO_CANCELADA) and request.user.tipo_usuario < 2:
                return Response({'detail': 'Solo un administrador puede ajustar el costo de una visita cerrada.'}, status=403)
            if (visita.estado == VisitaTecnica.ESTADO_FINALIZADA
                    and visita.evidencias.filter(es_temporal=True, eliminada_en__isnull=False).exists()):
                return Response({'detail': 'El PDF definitivo ya contiene las evidencias y el costo. No se puede modificar el costo después de eliminar las imágenes temporales.'}, status=409)
            changed = _set_visit_cost(visita, value, request.user, request.data.get('motivo_cambio_costo', ''))
            if changed and visita.estado == VisitaTecnica.ESTADO_FINALIZADA:
                transaction.on_commit(lambda visit_id=visita.pk: _refresh_saved_pdf(visit_id), robust=True)
        return Response(VisitaDetailSerializer(VisitaTecnica.objects.select_related('cliente', 'tecnico', 'creado_por').get(pk=pk)).data)


class IndicacionesVisitaView(APIView):
    permission_classes = [IsAuthenticated]

    @serialize_visit_mutation
    def patch(self, request, pk):
        if 'indicaciones_llegada' not in request.data:
            return Response({'indicaciones_llegada': 'Este campo es obligatorio.'}, status=400)
        value = request.data['indicaciones_llegada']
        if not isinstance(value, str) or len(value) > 2000:
            return Response({'indicaciones_llegada': 'Usa hasta 2000 caracteres.'}, status=400)
        visit = _filter_visitas_by_user(VisitaTecnica.objects.select_related('cliente'), request.user).filter(pk=pk).first()
        if not visit:
            return Response({'detail': 'Visita no encontrada o no asignada.'}, status=404)
        if visit.estado not in (VisitaTecnica.ESTADO_PENDIENTE, VisitaTecnica.ESTADO_EN_PROCESO):
            return Response({'detail': 'La visita ya no admite cambios.'}, status=409)
        visit.cliente.indicaciones_llegada = value.strip()
        visit.cliente.save(update_fields=['indicaciones_llegada'])
        return Response(VisitaDetailSerializer(visit).data)


def _safe_excel_text(value):
    text = str(value or '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


class ExportarVisitasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'tipo_usuario', 0) < 1:
            return Response({'detail': 'No permitido.'}, status=403)
        try:
            start = date.fromisoformat(request.query_params['fecha_desde'])
            end = date.fromisoformat(request.query_params['fecha_hasta'])
        except (KeyError, ValueError):
            return Response({'detail': 'Indica fechas válidas en formato AAAA-MM-DD.'}, status=400)
        if start > end:
            return Response({'detail': 'La fecha inicial debe ser anterior o igual a la final.'}, status=400)
        qs = _filter_visitas_by_user(
            VisitaTecnica.objects.select_related(
                'cliente', 'tecnico__usuario_rel', 'creado_por__usuario_rel', 'reporte',
            ).prefetch_related('evidencias').filter(fecha__range=(start, end)), request.user,
        )
        tecnico_id = request.query_params.get('tecnico_id')
        if tecnico_id and tecnico_id != 'all':
            if not tecnico_id.isdecimal():
                return Response({'tecnico_id': 'Técnico inválido.'}, status=400)
            qs = qs.filter(tecnico_id=int(tecnico_id))
        tipo = request.query_params.get('tipo_tarea')
        if tipo and tipo != 'all':
            qs = qs.filter(tipo_tarea=tipo)
        state = request.query_params.get('estado', 'all')
        if state not in ('all', 'pendiente', 'en_proceso', 'finalizada', 'cancelada'):
            return Response({'estado': 'Estado inválido.'}, status=400)
        if state != 'all':
            qs = qs.filter(estado=state)
        from collections import defaultdict
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.worksheet.table import Table as ExcelTable, TableStyleInfo
        from openpyxl.utils import get_column_letter
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Visitas'
        sheet.sheet_view.showGridLines = False
        headers = ['Número de visita', 'Fecha', 'Creada por', 'Técnico', 'Cliente',
                   'Teléfono', 'Tipo de servicio', 'Costo inicial', 'Costo final',
                   'Estado', 'PDF']
        sheet.append(headers)
        navy = '173A57'
        gold = 'E9AF43'
        pale = 'EAF2F7'
        for cell in sheet[1]:
            cell.fill = PatternFill('solid', fgColor=navy)
            cell.font = Font(name='Aptos', size=11, bold=True, color='FFFFFF')
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            cell.border = Border(bottom=Side(style='medium', color=gold))
        sheet.row_dimensions[1].height = 30
        width_caps = [24, 16, 36, 36, 40, 22, 44, 20, 20, 20, 19]
        width_minimums = [18, 15, 20, 20, 20, 17, 24, 17, 17, 16, 16]
        observed_widths = [len(header) for header in headers]
        grouped_tech = defaultdict(lambda: [0, Decimal('0')])
        grouped_type = defaultdict(lambda: [0, Decimal('0')])
        grouped_state = defaultdict(int)
        count = 0
        total_cost = Decimal('0')
        for visit in qs.order_by('fecha', 'id').iterator(chunk_size=100):
            creator = visit.creado_por.usuario_rel.nombre_completo if visit.creado_por and visit.creado_por.usuario_rel else (visit.creado_por.usuario if visit.creado_por else '')
            technician = visit.tecnico.usuario_rel.nombre_completo if visit.tecnico and visit.tecnico.usuario_rel else (visit.tecnico.usuario if visit.tecnico else '')
            type_name = visit.get_tipo_tarea_display()
            cost = visit.valor_visita if visit.valor_visita is not None else Decimal('0')
            count += 1
            total_cost += cost
            grouped_tech[technician or 'Sin técnico'][0] += 1
            grouped_tech[technician or 'Sin técnico'][1] += cost
            grouped_type[type_name][0] += 1
            grouped_type[type_name][1] += cost
            grouped_state[visit.get_estado_display()] += 1
            link = _public_pdf_url(visit) if visit.estado == VisitaTecnica.ESTADO_FINALIZADA else None
            sheet.append([
                _safe_excel_text(visit.numero_tarea), visit.fecha,
                _safe_excel_text(creator), _safe_excel_text(technician),
                _safe_excel_text(visit.cliente.nombre), _safe_excel_text(visit.cliente.telefono),
                _safe_excel_text(type_name), visit.costo_inicial,
                visit.valor_visita, visit.get_estado_display(),
                'Ver PDF' if link else 'No disponible',
            ])
            row = sheet.max_row
            for column, cell in enumerate(sheet[row], start=1):
                observed_widths[column - 1] = max(observed_widths[column - 1],
                                                  10 if column == 2 else len(str(cell.value or '')))
                cell.font = Font(name='Aptos', size=10, color='173A57')
                cell.alignment = Alignment(vertical='center', wrap_text=column in (3, 4, 5, 7))
                if row % 2 == 0:
                    cell.fill = PatternFill('solid', fgColor=pale)
            sheet.cell(row, 2).number_format = 'dd/mm/yyyy'
            for column in (8, 9):
                sheet.cell(row, column).number_format = '"$" #,##0.00'
                sheet.cell(row, column).alignment = Alignment(horizontal='right', vertical='center')
            if link:
                pdf_cell = sheet.cell(row, 11)
                pdf_cell.hyperlink = link
                pdf_cell.font = Font(name='Aptos', size=10, color='1463A5', underline='single')
            sheet.row_dimensions[row].height = 22
        sheet.freeze_panes = 'A2'
        for index, (observed, minimum, cap) in enumerate(
                zip(observed_widths, width_minimums, width_caps), start=1):
            sheet.column_dimensions[get_column_letter(index)].width = min(cap, max(minimum, observed + 2))
        table = ExcelTable(displayName='VisitasTecnicas', ref=f'A1:K{max(sheet.max_row, 2)}') if count else None
        if table:
            table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showFirstColumn=False,
                                                  showLastColumn=False, showRowStripes=True,
                                                  showColumnStripes=False)
            sheet.add_table(table)
        else:
            sheet.auto_filter.ref = 'A1:K1'

        summary = workbook.create_sheet('Resumen')
        summary.sheet_view.showGridLines = False
        summary.append(['IMPORGAS JJ · Resumen de visitas'])
        summary['A1'].font = Font(name='Aptos Display', bold=True, size=16, color='FFFFFF')
        summary['A1'].fill = PatternFill('solid', fgColor=navy)
        summary.merge_cells('A1:D1')
        summary.append(['Generado', timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')])
        summary.append(['Desde', start, 'Hasta', end])
        summary['B3'].number_format = 'dd/mm/yyyy'
        summary['D3'].number_format = 'dd/mm/yyyy'
        if tecnico_id and tecnico_id != 'all':
            selected_technician = Credenciales.objects.filter(pk=int(tecnico_id)).select_related('usuario_rel').first()
            technician_filter = (selected_technician.usuario_rel.nombre_completo
                                 if selected_technician and selected_technician.usuario_rel
                                 else (selected_technician.usuario if selected_technician else tecnico_id))
        else:
            technician_filter = 'Todos'
        selected_type = TipoVisita.objects.filter(codigo=tipo).first() if tipo and tipo != 'all' else None
        type_filter = selected_type.nombre if selected_type else (tipo if tipo and tipo != 'all' else 'Todos')
        state_filter = dict(VisitaTecnica.ESTADO_CHOICES).get(state, 'Todos')
        summary.append(['Técnico', _safe_excel_text(technician_filter), 'Servicio', _safe_excel_text(type_filter)])
        summary.append(['Estado', state_filter, 'Visitas', count])
        summary.append(['Costo final total', total_cost])
        summary['B6'].number_format = '"$" #,##0.00'
        summary.append([])
        for title, groups in (('Por técnico', grouped_tech), ('Por servicio', grouped_type)):
            summary.append([title, 'Visitas', 'Costo final total'])
            header_row = summary.max_row
            for cell in summary[header_row][:3]:
                cell.fill = PatternFill('solid', fgColor=navy)
                cell.font = Font(bold=True, color='FFFFFF')
            for name, values in sorted(groups.items()):
                summary.append([_safe_excel_text(name), values[0], values[1]])
                summary.cell(summary.max_row, 3).number_format = '"$" #,##0.00'
            summary.append([])
        summary.append(['Por estado', 'Visitas'])
        for cell in summary[summary.max_row][:2]:
            cell.fill = PatternFill('solid', fgColor=navy)
            cell.font = Font(bold=True, color='FFFFFF')
        for name, amount in sorted(grouped_state.items()):
            summary.append([_safe_excel_text(name), amount])
        for column, width in {'A': 39, 'B': 22, 'C': 25, 'D': 18}.items():
            summary.column_dimensions[column].width = width
        summary.freeze_panes = 'A2'
        output = io.BytesIO()
        workbook.save(output)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="visitas.xlsx"'
        return response

# ─── Start visit ──────────────────────────────────────────────────────────────

class IniciarVisitaView(APIView):
    permission_classes = [IsAuthenticated]

    @serialize_visit_mutation
    def post(self, request, pk):
        try:
            qs = VisitaTecnica.objects.all()
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
        except VisitaTecnica.DoesNotExist:
            return Response({'error': 'Visita no encontrada.'}, status=404)

        if v.estado != VisitaTecnica.ESTADO_PENDIENTE:
            return Response({'error': f'Solo se puede iniciar una visita pendiente (estado actual: {v.get_estado_display()}).'}, status=400)

        v.estado = VisitaTecnica.ESTADO_EN_PROCESO
        v.save(update_fields=['estado', 'fecha_actualizacion'])

        # Auto-record start of displacement
        reporte, _ = ReporteVisita.objects.get_or_create(
            visita=v,
            defaults={
                'persona_atiende': '',
                'equipo': 'estufa',
                'ubicacion_equipo': 'cocina',
                'motivo_servicio': '',
                'solucion_realizada': '',
            }
        )
        if not reporte.inicio_desplazamiento:
            reporte.inicio_desplazamiento = timezone.now()
            reporte.save(update_fields=['inicio_desplazamiento'])

        return Response(VisitaDetailSerializer(v).data)


# ─── Submit report (finalize visit) ───────────────────────────────────────────

class FinalizarVisitaView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @transaction.atomic
    @serialize_visit_mutation
    def post(self, request, pk):
        try:
            qs = VisitaTecnica.objects.select_for_update().select_related('cliente')
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
        except VisitaTecnica.DoesNotExist:
            return Response({'error': 'Visita no encontrada.'}, status=404)

        if v.estado not in (VisitaTecnica.ESTADO_PENDIENTE, VisitaTecnica.ESTADO_EN_PROCESO):
            return Response({'error': 'La visita ya fue finalizada o cancelada.'}, status=400)

        reporte_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        motivo_cambio_costo = reporte_data.pop('motivo_cambio_costo', '')
        if isinstance(motivo_cambio_costo, list):
            motivo_cambio_costo = motivo_cambio_costo[0]
        firma = reporte_data.pop('firma_cliente', None)
        if isinstance(firma, list):
            firma = firma[0]

        # Handle base64 signature
        firma_b64 = reporte_data.pop('firma_base64', None)
        if isinstance(firma_b64, list):
            firma_b64 = firma_b64[0]
        if firma:
            serializers.ImageField().run_validation(firma)
            firma.seek(0)
        signature_file = None
        signature_ext = 'png'
        if firma_b64:
            try:
                signature_ext = 'jpg' if str(firma_b64).startswith('data:image/jpeg;') else 'png'
                raw = base64.b64decode(str(firma_b64).split(';base64,')[-1], validate=True)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Firma demasiado grande')
                signature_file = ContentFile(raw, name=f'firma.{signature_ext}')
                serializers.ImageField().run_validation(signature_file)
                signature_file.seek(0)
            except Exception:
                return Response({'firma_base64': 'La firma debe ser una imagen válida de máximo 1 MB.'}, status=400)

        reporte = ReporteVisita.objects.filter(visita=v).first()
        if reporte is None:
            reporte = ReporteVisita(
                visita=v, persona_atiende='', equipo='estufa',
                ubicacion_equipo='cocina', motivo_servicio='', solucion_realizada='',
            )

        if reporte_data.get('valor_servicio') in ('', None):
            reporte_data['valor_servicio'] = v.valor_visita
        serializer = ReporteCreateSerializer(reporte, data=reporte_data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        candidate = {
            field: serializer.validated_data.get(field, getattr(reporte, field))
            for field in ('persona_atiende', 'motivo_servicio', 'solucion_realizada',
                          'equipo', 'equipo_otro', 'ubicacion_equipo', 'ubicacion_otro')
        }
        for field in ('persona_atiende', 'motivo_servicio', 'solucion_realizada'):
            if not str(candidate[field]).strip():
                return Response({field: 'Este campo es obligatorio.'}, status=400)
        for selector, extra in (('equipo', 'equipo_otro'), ('ubicacion_equipo', 'ubicacion_otro')):
            if candidate[selector] == 'otro' and not str(candidate[extra]).strip():
                return Response({extra: 'Especifica el valor de otro.'}, status=400)
        reporte = serializer.save()
        if 'valor_servicio' in serializer.validated_data:
            _set_visit_cost(v, reporte.valor_servicio, request.user, motivo_cambio_costo)
        else:
            reporte.valor_servicio = v.valor_visita
            reporte.save(update_fields=['valor_servicio'])

        # Save signature
        if firma:
            reporte.firma_cliente = firma
            reporte.save(update_fields=['firma_cliente'])

        if firma_b64:
            reporte.firma_base64 = firma_b64
            reporte.firma_cliente.save(
                f'firma_{v.numero_tarea}.{signature_ext}', signature_file, save=False,
            )
            reporte.save(update_fields=['firma_base64', 'firma_cliente'])

        v.pdf_estado = 'procesando'
        v.save(update_fields=['pdf_estado'])
        try:
            v = _persist_visit_pdf(v.pk)
        except Exception:
            logger.exception('No fue posible completar PDF de visita %s', v.pk)
            v.pdf_estado = 'fallido'
            v.pdf_error = 'No se pudo generar o guardar el PDF. Reintenta desde el CRM.'
            v.save(update_fields=['pdf_estado', 'pdf_error'])
        else:
            transaction.on_commit(lambda visit_id=v.pk: _save_pdf_and_notify(visit_id), robust=True)

        correo_enviado = False

        response_data = VisitaDetailSerializer(
            VisitaTecnica.objects.select_related('cliente', 'tecnico').prefetch_related('evidencias').get(pk=pk)
        ).data
        response_data['correo_enviado'] = correo_enviado
        return Response(response_data)


# ─── Photos ───────────────────────────────────────────────────────────────────

class FotosView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @serialize_visit_mutation
    def post(self, request, pk):
        try:
            qs = VisitaTecnica.objects.all()
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
        except VisitaTecnica.DoesNotExist:
            return Response({'error': 'Visita no encontrada.'}, status=404)
        if v.estado in (VisitaTecnica.ESTADO_FINALIZADA, VisitaTecnica.ESTADO_CANCELADA):
            return Response({'detail': 'Las evidencias de una visita cerrada no se pueden modificar.'}, status=409)

        fotos = request.FILES.getlist('fotos')
        if not fotos:
            return Response({'error': 'No se enviaron imágenes.'}, status=400)

        current_count = v.evidencias.count()
        if current_count + len(fotos) > 20:
            return Response({'error': f'Máximo 20 fotografías por visita (ya tiene {current_count}).'}, status=400)

        for foto in fotos:
            validator = EvidenciaSerializer(data={'imagen': foto})
            validator.is_valid(raise_exception=True)
            foto.seek(0)
        evidencias = []
        for i, foto in enumerate(fotos):
            e = EvidenciaFotografica.objects.create(
                visita=v,
                imagen=foto,
                orden=current_count + i,
                es_temporal=True,
            )
            evidencias.append(e)

        return Response(EvidenciaResponseSerializer(evidencias, many=True).data, status=201)

    @serialize_visit_mutation
    def delete(self, request, pk, foto_id):
        try:
            qs = VisitaTecnica.objects.all()
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
            e = EvidenciaFotografica.objects.get(pk=foto_id, visita=v)
        except (VisitaTecnica.DoesNotExist, EvidenciaFotografica.DoesNotExist):
            return Response({'error': 'No encontrado.'}, status=404)
        if v.estado in (VisitaTecnica.ESTADO_FINALIZADA, VisitaTecnica.ESTADO_CANCELADA):
            return Response({'detail': 'Las evidencias de una visita cerrada no se pueden modificar.'}, status=409)

        e.delete()
        return Response(status=204)


class FotoPublicaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk, foto_id):
        try:
            payload = signing.loads(request.query_params.get('token', ''),
                                    salt='visita-foto-publica', max_age=24 * 3600)
        except signing.BadSignature:
            return Response({'detail': 'Enlace inválido o vencido.'}, status=403)
        evidence = EvidenciaFotografica.objects.select_related('visita').filter(pk=foto_id, visita_id=pk).first()
        if (not evidence or not evidence.imagen or payload.get('visit_id') != pk or payload.get('photo_id') != foto_id
                or payload.get('version') != evidence.visita.pdf_link_version):
            return Response({'detail': 'Imagen no disponible.'}, status=403)
        extension = evidence.imagen.name.rsplit('.', 1)[-1].lower()
        content_type = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                        'webp': 'image/webp'}.get(extension, 'application/octet-stream')
        response = FileResponse(evidence.imagen.open('rb'), content_type=content_type)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class FirmaPublicaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        try:
            payload = signing.loads(request.query_params.get('token', ''),
                                    salt='visita-firma-publica', max_age=24 * 3600)
        except signing.BadSignature:
            return Response({'detail': 'Enlace inválido o vencido.'}, status=403)
        visit = VisitaTecnica.objects.filter(pk=pk).first()
        if (not visit or payload.get('visit_id') != pk
                or payload.get('version') != visit.pdf_link_version
                or not hasattr(visit, 'reporte') or not visit.reporte.firma_cliente):
            return Response({'detail': 'Firma no disponible.'}, status=403)
        filename = visit.reporte.firma_cliente.name.lower()
        content_type = 'image/jpeg' if filename.endswith(('.jpg', '.jpeg')) else 'image/png'
        response = FileResponse(visit.reporte.firma_cliente.open('rb'), content_type=content_type)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


# ─── Calendar ─────────────────────────────────────────────────────────────────

class CalendarioView(APIView):
    """Devuelve visitas agrupadas por fecha para un mes dado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mes = request.query_params.get('mes')  # YYYY-MM

        qs = VisitaTecnica.objects.select_related('cliente', 'tecnico__usuario_rel')
        qs = _filter_visitas_by_user(qs, request.user)

        if mes:
            try:
                y, m = mes.split('-')
                qs = qs.filter(fecha__year=int(y), fecha__month=int(m))
            except Exception:
                pass

        # Group by date
        result = {}
        for v in qs:
            key = str(v.fecha)
            if key not in result:
                result[key] = []
            result[key].append({
                'id': v.id,
                'numero_tarea': v.numero_tarea,
                'cliente_nombre': v.cliente.nombre,
                'hora': str(v.hora),
                'valor_visita': (
                    int(v.valor_visita)
                    if v.valor_visita is not None and v.valor_visita == v.valor_visita.to_integral_value()
                    else (float(v.valor_visita) if v.valor_visita is not None else None)
                ),
                'estado': v.estado,
                'tipo_tarea': v.get_tipo_tarea_display(),
                'tecnico_nombre': (
                    v.tecnico.usuario_rel.nombre_completo
                    if v.tecnico and v.tecnico.usuario_rel
                    else (v.tecnico.usuario if v.tecnico else None)
                ),
            })

        return Response(result)


# ─── PDF generation ────────────────────────────────────────────────────────────

class PDFReporteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            qs = VisitaTecnica.objects.select_related(
                'cliente', 'tecnico__usuario_rel', 'reporte'
            ).prefetch_related('evidencias')
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
        except VisitaTecnica.DoesNotExist:
            return Response({'error': 'Visita no encontrada.'}, status=404)

        if (v.estado == VisitaTecnica.ESTADO_FINALIZADA and not v.pdf_final
                and not v.pdf_estado and hasattr(v, 'reporte')):
            try:
                # Compatibilidad con informes históricos. No envía notificaciones.
                v = _persist_visit_pdf(v.pk)
            except Exception:
                logger.exception('No fue posible archivar el PDF histórico de visita %s', v.pk)
                return Response({'detail': 'No se pudo generar el informe histórico. Se conservaron sus archivos.'}, status=409)
        if v.estado != VisitaTecnica.ESTADO_FINALIZADA or not v.pdf_final or v.pdf_estado in ('error', 'fallido', 'procesando') or (
                v.pdf_source_hash and v.pdf_source_hash != _pdf_source_hash(v)):
            return Response({'detail': 'El PDF definitivo no está disponible. Reintenta su generación.'}, status=409)
        response = FileResponse(v.pdf_final.open('rb'), content_type='application/pdf',
                                filename=_pdf_filename(v),
                                as_attachment=request.query_params.get('download') == '1')
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class PDFPublicoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        try:
            payload = signing.loads(
                request.query_params.get('token', ''),
                salt='visita-pdf-publico', max_age=7 * 24 * 3600,
            )
        except signing.BadSignature:
            return Response({'detail': 'Enlace inválido o vencido.'}, status=403)
        visit = VisitaTecnica.objects.filter(pk=pk, estado=VisitaTecnica.ESTADO_FINALIZADA).first()
        if (not visit or payload.get('visit_id') != pk
                or payload.get('version', 1) != visit.pdf_link_version):
            return Response({'detail': 'Enlace inválido.'}, status=403)
        if not visit.pdf_final or visit.pdf_estado in ('error', 'fallido', 'procesando') or (
                visit.pdf_source_hash and visit.pdf_source_hash != _pdf_source_hash(visit)):
            return Response({'detail': 'Informe no disponible.'}, status=404)
        logger.info('Acceso autorizado al PDF público de visita %s', visit.pk)
        response = FileResponse(
            visit.pdf_final.open('rb'), as_attachment=request.query_params.get('download') == '1',
            filename=_pdf_filename(visit), content_type='application/pdf',
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class RevocarEnlacesView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if getattr(request.user, 'tipo_usuario', 0) < 2:
            return Response({'detail': 'Solo administradores pueden revocar enlaces.'}, status=403)
        visit = VisitaTecnica.objects.select_for_update().filter(pk=pk).first()
        if not visit:
            return Response({'detail': 'Visita no encontrada.'}, status=404)
        visit.pdf_link_version += 1
        visit.save(update_fields=['pdf_link_version'])
        return Response({'detail': 'Enlaces anteriores revocados.'})


class ReintentarPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if getattr(request.user, 'tipo_usuario', 0) < 2:
            return Response({'detail': 'Solo administradores pueden reintentar el PDF.'}, status=403)
        visit = VisitaTecnica.objects.filter(pk=pk, pdf_estado__in=('error', 'fallido')).first()
        if not visit or not hasattr(visit, 'reporte'):
            return Response({'detail': 'No hay una generación fallida para reintentar.'}, status=404)
        try:
            visit = _persist_visit_pdf(pk)
        except Exception:
            logger.exception('No fue posible regenerar PDF de visita %s', pk)
            VisitaTecnica.objects.filter(pk=pk).update(pdf_estado='fallido', pdf_error='No se pudo generar o guardar el PDF.')
            return Response({'detail': 'No se pudo generar el PDF. Las imágenes se conservaron.'}, status=500)
        transaction.on_commit(lambda visit_id=pk: _save_pdf_and_notify(visit_id), robust=True)
        return Response({'pdf_disponible': True, 'pdf_sha256': visit.pdf_sha256})


def _generar_pdf(visita: VisitaTecnica) -> bytes:
    """Genera el PDF del informe técnico usando reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, Image as RLImage, HRFlowable, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from io import BytesIO
    from PIL import Image as PILImage
    from django.conf import settings

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    bold = ParagraphStyle('bold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontName='Helvetica', fontSize=8)
    title_style = ParagraphStyle('title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER)
    small = ParagraphStyle('small', parent=styles['Normal'], fontName='Helvetica', fontSize=7)
    italic_small = ParagraphStyle('italic_small', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, alignment=TA_JUSTIFY)

    r = visita.reporte
    c = visita.cliente
    tecnico_nombre = (
        visita.tecnico.usuario_rel.nombre_completo
        if visita.tecnico and visita.tecnico.usuario_rel
        else (visita.tecnico.usuario if visita.tecnico else 'No asignado')
    )
    creator_name = (
        visita.creado_por.usuario_rel.nombre_completo
        if visita.creado_por and visita.creado_por.usuario_rel
        else (visita.creado_por.usuario if visita.creado_por else 'No registrado')
    )

    story = []
    w = A4[0] - 3 * cm  # usable width

    # Copia versionada del PNG oficial; la generación no depende del frontend
    # en ejecución ni de descargas externas.
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo_imporgas.png')
    with open(logo_path, 'rb') as logo_file:
        logo_buffer = BytesIO(logo_file.read())
    with PILImage.open(logo_buffer) as logo_source:
        logo_ratio = logo_source.height / logo_source.width
    logo_buffer.seek(0)
    logo_height = 2.75 * cm
    logo = RLImage(logo_buffer, width=logo_height / logo_ratio, height=logo_height)

    # ── Header ──
    header_data = [[
        logo,
        Paragraph('<b>Informes de tareas</b><br/>'
                  '<b>DEPARTAMENTO DE SERVICIO TÉCNICO</b><br/>'
                  '<b>IMPORGAS JJ</b><br/>'
                  'Teléfono: 3165266734 / 3176467820<br/>'
                  'Número de identificación empresarial:<br/>'
                  'Email: servicioimporgas@gmail.com<br/>'
                  'Dirección: Sede Norte / Sede Sur', normal),
    ]]
    header_table = Table(header_data, colWidths=[3.5 * cm, w - 3.5 * cm])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))

    # ── Client + Task number ──
    client_header = [[
        Paragraph(f'<b>{escape(c.nombre.upper())}</b>', bold),
        Paragraph(f'<b>Tarea {escape(str(visita.numero_tarea))}</b>', bold),
    ]]
    ct = Table(client_header, colWidths=[w * 0.7, w * 0.3])
    ct.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.2 * cm))

    # ── Client info ──
    story.append(Paragraph('<b>Informaciones del cliente</b>', bold))
    ci_data = [
        [Paragraph('<b>Identificación Personal/Empresarial</b>', small), Paragraph(escape(c.identificacion or ''), normal)],
        [Paragraph('<b>Teléfono</b>', small), Paragraph(escape(c.telefono or ''), normal)],
        [Paragraph('<b>Email</b>', small), Paragraph(escape(c.correo or ''), normal)],
    ]
    ci_table = Table(ci_data, colWidths=[w * 0.3, w * 0.7])
    ci_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#DCE6F1')),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(ci_table)
    story.append(Spacer(1, 0.2 * cm))

    # ── Activity info ──
    story.append(Paragraph('<b>Informaciones de las actividades</b>', bold))
    fecha_str = visita.fecha.strftime('%d/%m/%Y') if visita.fecha else ''
    hora_str = str(visita.hora)[:5] if visita.hora else ''

    act_data = [
        ['Para', tecnico_nombre, 'Tipo de tarea', visita.get_tipo_tarea_display()],
        ['Fecha', fecha_str, 'Estado', visita.get_estado_display()],
        ['Dirección', Paragraph(escape(c.direccion), normal), '', ''],
        ['Descripción de la tarea', Paragraph(escape(visita.descripcion or ''), normal), '', ''],
        ['Reporte de ejecución', Paragraph(escape(r.solucion_realizada if r else ''), normal), '', ''],
        ['Creada por', Paragraph(escape(creator_name), normal), '', ''],
    ]
    act_table = Table(act_data, colWidths=[w * 0.18, w * 0.32, w * 0.18, w * 0.32])
    act_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#DCE6F1')),
        ('BACKGROUND', (2, 0), (-2, 1), colors.HexColor('#DCE6F1')),
        ('SPAN', (1, 2), (3, 2)),
        ('SPAN', (1, 3), (3, 3)),
        ('SPAN', (1, 4), (3, 4)),
        ('SPAN', (1, 5), (3, 5)),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(act_table)
    story.append(Spacer(1, 0.3 * cm))

    # ── Form header ──
    fh = Table(
        [[Paragraph('<b>Formulario: FORMULARIO GENERAL VISITAS</b>', bold)]],
        colWidths=[w]
    )
    fh.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(fh)
    story.append(Spacer(1, 0.2 * cm))

    if r:
        # ── Technician form fields ──
        equipo_val = r.equipo_otro if r.equipo == 'otro' else r.get_equipo_display()
        ubicacion_val = r.ubicacion_otro if r.ubicacion_equipo == 'otro' else r.get_ubicacion_equipo_display()

        form_data = [
            [Paragraph('<b>Nombre de la persona que atiende</b>', small),
             Paragraph('<b>Equipos a Asistir</b>', small)],
            [Paragraph(escape(r.persona_atiende or ''), normal), Paragraph(escape(equipo_val or ''), normal)],
            [Paragraph('<b>Ubicacion de Equipo</b>', small),
             Paragraph('<b>Motivo del servicio</b>', small)],
            [Paragraph(escape(ubicacion_val or ''), normal), Paragraph(escape(r.motivo_servicio or ''), normal)],
        ]
        form_table = Table(form_data, colWidths=[w * 0.5, w * 0.5])
        form_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#DCE6F1')),
            ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#DCE6F1')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(form_table)
        story.append(Spacer(1, 0.2 * cm))

        # ── Solution / Observations / Recommendations ──
        sol_data = [
            [Paragraph('<b>Solucion y Observaciones</b>', small),
             Paragraph('<b>Recomendaciones</b>', small)],
            [Paragraph(escape(r.solucion_realizada or ''), normal),
             Paragraph(escape(r.recomendaciones or ''), normal)],
            [Paragraph('<b>Cancela la visita al tecnico</b>', small),
             Paragraph('<b>Valor del servicio</b>', small)],
            [Paragraph(r.get_metodo_pago_display() if r.metodo_pago else '', normal),
             Paragraph(f'{visita.valor_visita:,.0f}' if visita.valor_visita is not None else '', normal)],
        ]
        sol_table = Table(sol_data, colWidths=[w * 0.5, w * 0.5])
        sol_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#DCE6F1')),
            ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#DCE6F1')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(sol_table)
        story.append(Spacer(1, 0.3 * cm))

        # ── Legal conditions ──
        condiciones = (
            "<b><i>CONDICIONES DE LA PRESTACIÓN DEL SERVICIO:</i></b><br/>"
            "<i>Este documento representa constancia de notificación personal al cliente referente a:<br/>"
            "* Recibir a satisfacción el trabajo realizado por el personal técnico de IMPORGAS JJ.<br/>"
            "* Aceptar las condiciones de la prestación del servicio.<br/>"
            "Así mismo se informa que:<br/>"
            "* SERVICIO TÉCNICO IMPORGAS JJ no se hace responsable de trabajos adicionales que no estén facturados.<br/>"
            "Las visitas técnicas no tienen garantía.</i>"
        )
        story.append(Paragraph(condiciones, italic_small))
        story.append(Spacer(1, 0.2 * cm))

        garantias = (
            "<b><i>GARANTIA Y RECOMENDACIONES:</i></b><br/>"
            "<i>Se recomienda hacer mantenimiento preventivo cada 1 año a los equipos para alargar la vida útil de los equipos.<br/>"
            "Garantía de 3 meses a repuestos cambiados.<br/>"
            "Los componentes electrónicos no tienen garantía.<br/>"
            "Las visitas técnicas no tienen garantía y tienen plazo de 8 días para poder ser descontadas</i>"
        )
        story.append(Paragraph(garantias, italic_small))
        story.append(Spacer(1, 0.3 * cm))

        # ── Photos ──
        evidencias = list(visita.evidencias.exclude(imagen='')[:20])
        if evidencias:
            foto_header = Table([[Paragraph('<b>Fotos</b>', bold)]], colWidths=[w])
            foto_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#DCE6F1')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            cols = min(3, len(evidencias))
            img_w = (w - 0.4 * cm) / cols
            img_h = min(5.5 * cm, img_w * 0.75)
            row = []
            foto_rows = []
            for i, ev in enumerate(evidencias):
                # Una imagen ilegible invalida el PDF; nunca se omite en silencio.
                with ev.imagen.open('rb') as source:
                    with PILImage.open(source) as picture:
                        picture.load()
                        picture.thumbnail((1600, 1600))
                        if picture.mode not in ('RGB', 'RGBA'):
                            picture = picture.convert('RGB')
                        image_data = BytesIO()
                        picture.save(image_data, format='PNG')
                        original_width, original_height = picture.size
                image_data.seek(0)
                scale = min(img_w / original_width, img_h / original_height)
                img = RLImage(image_data, width=original_width * scale,
                              height=original_height * scale)
                row.append(img)
                if len(row) == cols:
                    foto_rows.append(row)
                    row = []
            if row:
                while len(row) < cols:
                    row.append('')
                foto_rows.append(row)

            if foto_rows:
                photo_style = TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ])
                first_photo_row = Table(foto_rows[:1], colWidths=[img_w] * cols)
                first_photo_row.setStyle(photo_style)
                story.append(Spacer(1, 0.2 * cm))
                story.append(KeepTogether([foto_header, Spacer(1, 0.2 * cm), first_photo_row]))
                if len(foto_rows) > 1:
                    remaining_photos = Table(foto_rows[1:], colWidths=[img_w] * cols)
                    remaining_photos.setStyle(photo_style)
                    story.append(remaining_photos)

        # Firma al final, unida a su línea en el mismo bloque.
        signature_image = None
        try:
            if r.firma_cliente:
                source = r.firma_cliente.path
            elif r.firma_base64:
                raw = r.firma_base64.split(';base64,')[-1]
                source = BytesIO(base64.b64decode(raw, validate=True))
            else:
                source = None
            if source:
                with PILImage.open(source) as signature_source:
                    ratio = signature_source.width / signature_source.height
                if hasattr(source, 'seek'):
                    source.seek(0)
                signature_width = min(5 * cm, 2.2 * cm * ratio)
                signature_image = RLImage(source, width=signature_width, height=signature_width / ratio)
        except Exception:
            logger.warning('Firma no legible para visita %s', visita.pk)
        story.append(Spacer(1, 0.35 * cm))
        if signature_image:
            signature_table = Table([
                [signature_image],
                [HRFlowable(width=5 * cm, thickness=0.7, color=colors.black, hAlign='LEFT')],
                [Paragraph('Firma cliente', small)],
            ], colWidths=[5.4 * cm], hAlign='LEFT')
            signature_table.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(KeepTogether([signature_table]))
        else:
            story.append(Paragraph('Visita finalizada sin firma del cliente', bold))
    doc.build(story)
    return buffer.getvalue()
