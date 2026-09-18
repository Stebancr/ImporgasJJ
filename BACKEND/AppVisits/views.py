from .sync_version import serialize_visit_mutation
import io
import os
import base64
from datetime import datetime, date

from django.http import HttpResponse, FileResponse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMessage
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import VisitaTecnica, ReporteVisita, EvidenciaFotografica, ClienteVisita
from .serializers import (
    VisitaListSerializer, VisitaDetailSerializer,
    VisitaCreateSerializer, VisitaUpdateSerializer,
    ReporteSerializer, ReporteCreateSerializer,
    EvidenciaSerializer, TecnicoSerializer, ClienteVisitaSerializer,
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
        pdf = _generar_pdf(visita)
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


# ─── Visits list / create ──────────────────────────────────────────────────────

class VisitaListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VisitaTecnica.objects.select_related(
            'cliente', 'tecnico', 'tecnico__usuario_rel'
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

        serializer = VisitaCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            visita = serializer.save()
            if visita.tecnico_id:
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
        serializer = VisitaUpdateSerializer(v, data=request.data, partial=True)
        if serializer.is_valid():
            visita = serializer.save()
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
        firma = reporte_data.pop('firma_cliente', None)
        if isinstance(firma, list):
            firma = firma[0]

        # Handle base64 signature
        firma_b64 = reporte_data.pop('firma_base64', None)
        if isinstance(firma_b64, list):
            firma_b64 = firma_b64[0]

        reporte, _ = ReporteVisita.objects.get_or_create(visita=v, defaults={
            'persona_atiende': '',
            'equipo': 'estufa',
            'ubicacion_equipo': 'cocina',
            'motivo_servicio': '',
            'solucion_realizada': '',
        })

        serializer = ReporteCreateSerializer(reporte, data=reporte_data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        reporte = serializer.save()

        # Save signature
        if firma:
            reporte.firma_cliente = firma
            reporte.save(update_fields=['firma_cliente'])

        if firma_b64:
            reporte.firma_base64 = firma_b64
            try:
                firma_str = firma_b64.strip()
                if ';base64,' in firma_str:
                    fmt, imgstr = firma_str.split(';base64,')
                    ext = fmt.split('/')[-1] if '/' in fmt else 'png'
                else:
                    imgstr = firma_str
                    ext = 'png'
                img_bytes = base64.b64decode(imgstr)
                from django.core.files.base import ContentFile
                reporte.firma_cliente.save(
                    f'firma_{v.numero_tarea}.{ext}',
                    ContentFile(img_bytes),
                    save=False,
                )
            except Exception:
                pass
            reporte.save(update_fields=['firma_base64', 'firma_cliente'])

        v.estado = VisitaTecnica.ESTADO_FINALIZADA
        v.save(update_fields=['estado', 'fecha_actualizacion'])

        correo_enviado = _enviar_correo_visita_completada(v)

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
            )
            evidencias.append(e)

        return Response(EvidenciaSerializer(evidencias, many=True).data, status=201)

    @serialize_visit_mutation
    def delete(self, request, pk, foto_id):
        try:
            qs = VisitaTecnica.objects.all()
            qs = _filter_visitas_by_user(qs, request.user)
            v = qs.get(pk=pk)
            e = EvidenciaFotografica.objects.get(pk=foto_id, visita=v)
        except (VisitaTecnica.DoesNotExist, EvidenciaFotografica.DoesNotExist):
            return Response({'error': 'No encontrado.'}, status=404)

        e.delete()
        return Response(status=204)


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

        if not hasattr(v, 'reporte'):
            return Response({'error': 'Esta visita no tiene reporte aún.'}, status=400)

        pdf_buffer = _generar_pdf(v)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_{v.numero_tarea}.pdf"'
        return response


def _generar_pdf(visita: VisitaTecnica) -> bytes:
    """Genera el PDF del informe técnico usando reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, Image as RLImage, HRFlowable
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

    story = []
    w = A4[0] - 3 * cm  # usable width

    # ── Header ──
    header_data = [[
        Paragraph('<b>Informes de tareas</b><br/>'
                  '<b>DEPARTAMENTO DE SERVICIO TECNICO IMPORGAS JJ</b><br/>'
                  'Teléfono: 3165266734 3176467820<br/>'
                  'Número de identificación empresarial:<br/>'
                  'Email: servicioimporgas@gmail.com<br/>'
                  'Dirección: Sede Norte / Sede Sur', normal),
    ]]
    header_table = Table(header_data, colWidths=[w])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))

    # ── Client + Task number ──
    client_header = [[
        Paragraph(f'<b>{c.nombre.upper()}</b>', bold),
        Paragraph(f'<b>Tarea {visita.numero_tarea}</b>', bold),
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
        [Paragraph('<b>Identificación Personal/Empresarial</b>', small), Paragraph(c.identificacion or '', normal)],
        [Paragraph('<b>Teléfono</b>', small), Paragraph(c.telefono or '', normal)],
        [Paragraph('<b>Email</b>', small), Paragraph(c.correo or '', normal)],
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
        ['Dirección', Paragraph(c.direccion, normal), '', ''],
        ['Descripción de la tarea', Paragraph(visita.descripcion or '', normal), '', ''],
        ['Reporte de ejecución', Paragraph(r.solucion_realizada if r else '', normal), '', ''],
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
            [Paragraph(r.persona_atiende or '', normal), Paragraph(equipo_val or '', normal)],
            [Paragraph('<b>Ubicacion de Equipo</b>', small),
             Paragraph('<b>Motivo del servicio</b>', small)],
            [Paragraph(ubicacion_val or '', normal), Paragraph(r.motivo_servicio or '', normal)],
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
            [Paragraph(r.solucion_realizada or '', normal),
             Paragraph(r.recomendaciones or '', normal)],
            [Paragraph('<b>Cancela la visita al tecnico</b>', small),
             Paragraph('<b>Valor del servicio</b>', small)],
            [Paragraph(r.get_metodo_pago_display() if r.metodo_pago else '', normal),
             Paragraph(f'{r.valor_servicio:,.0f}' if r.valor_servicio else '', normal)],
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

        # ── Signature ──
        firma_agregada = False
        if r.firma_base64:
            story.append(Paragraph('<b>Firma del cliente:</b>', bold))
            try:
                firma_str = r.firma_base64.strip()
                if ';base64,' in firma_str:
                    fmt, imgstr = firma_str.split(';base64,')
                else:
                    imgstr = firma_str
                img_bytes = base64.b64decode(imgstr)
                from io import BytesIO
                img_buffer = BytesIO(img_bytes)
                img_buffer.seek(0)
                firma_img = RLImage(img_buffer, width=5 * cm, height=3 * cm)
                story.append(firma_img)
                firma_agregada = True
            except Exception as e:
                if r.firma_cliente:
                    try:
                        firma_path = r.firma_cliente.path
                        firma_img = RLImage(firma_path, width=5 * cm, height=3 * cm)
                        story.append(firma_img)
                        firma_agregada = True
                    except Exception:
                        pass
        elif r.firma_cliente:
            story.append(Paragraph('<b>Firma del cliente:</b>', bold))
            try:
                firma_path = r.firma_cliente.path
                firma_img = RLImage(firma_path, width=5 * cm, height=3 * cm)
                story.append(firma_img)
                firma_agregada = True
            except Exception:
                pass

        if firma_agregada:
            story.append(HRFlowable(width=5 * cm, thickness=0.7, color=colors.black, spaceBefore=1, spaceAfter=2, hAlign='LEFT'))
            story.append(Paragraph('Firma cliente', small))

        # ── Photos ──
        evidencias = list(visita.evidencias.all()[:20])
        if evidencias:
            story.append(Spacer(1, 0.3 * cm))
            foto_header = Table([[Paragraph('<b>Fotos</b>', bold)]], colWidths=[w])
            foto_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#DCE6F1')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(foto_header)
            story.append(Spacer(1, 0.2 * cm))

            cols = 3
            img_w = (w - 0.4 * cm) / cols
            img_h = img_w * 0.75
            row = []
            foto_rows = []
            for i, ev in enumerate(evidencias):
                try:
                    img = RLImage(ev.imagen.path, width=img_w, height=img_h)
                    row.append(img)
                except Exception:
                    row.append('')
                if len(row) == cols:
                    foto_rows.append(row)
                    row = []
            if row:
                while len(row) < cols:
                    row.append('')
                foto_rows.append(row)

            if foto_rows:
                foto_table = Table(foto_rows, colWidths=[img_w] * cols)
                foto_table.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]))
                story.append(foto_table)

    doc.build(story)
    return buffer.getvalue()
