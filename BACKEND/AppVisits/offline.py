"""Versioned, idempotent offline completion; legacy endpoints stay compatible."""
import base64
import hashlib
import json
import logging
import re

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VisitaTecnica, ReporteVisita, EvidenciaFotografica, VisitSyncReceipt
from .serializers import VisitaDetailSerializer, ReporteCreateSerializer, EvidenciaSerializer
from .sync_version import visit_sync_version

logger = logging.getLogger(__name__)


def request_digest(request):
    fields = {key: request.data.get(key) for key in request.data if key != 'fotos'}
    digest = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(',', ':')).encode())
    for photo in request.FILES.getlist('fotos'):
        digest.update(photo.name.encode())
        digest.update(str(photo.size).encode())
        for chunk in photo.chunks():
            digest.update(chunk)
        photo.seek(0)
    return digest.hexdigest()


class SincronizarVisitaView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        key = request.headers.get('Idempotency-Key', '')
        expected = request.headers.get('If-Match', '').strip('"')
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
            return Response({'detail': 'Se requiere una clave de operación válida.'}, status=400)
        if not expected:
            return Response({'detail': 'Se requiere la versión de la visita (If-Match).'}, status=428)
        if getattr(request.user, 'tipo_usuario', 0) < 1 or not request.user.is_active:
            return Response({'detail': 'No tiene permiso para gestionar visitas.'}, status=403)

        # Compute before holding database locks; the multipart parser spills large
        # uploads to temporary files and hashes them incrementally.
        digest = request_digest(request)
        created_files = []
        try:
            with transaction.atomic():
                qs = VisitaTecnica.objects.select_for_update()
                if request.user.tipo_usuario == 1:
                    qs = qs.filter(tecnico_id=request.user.pk)
                try:
                    visit = qs.get(pk=pk)
                except VisitaTecnica.DoesNotExist:
                    return Response({'detail': 'Visita no encontrada o reasignada.'}, status=404)

                receipt = VisitSyncReceipt.objects.filter(visita=visit, usuario=request.user, operation_key=key).first()
                if receipt:
                    if receipt.request_hash != digest:
                        return Response({'detail': 'La clave ya se usó con otros datos.'}, status=409)
                    return Response(receipt.response_data, headers={'Idempotency-Replayed': 'true'})

                current_version = visit_sync_version(visit)
                if expected != current_version:
                    return Response({'detail': 'La visita cambió. Revisa los datos actuales antes de sincronizar.', 'sync_version': current_version}, status=412)
                if visit.estado not in ('pendiente', 'en_proceso'):
                    return Response({'detail': 'La visita está cerrada o cancelada.'}, status=409)

                photos = request.FILES.getlist('fotos')
                if not photos or visit.evidencias.count() + len(photos) > 20:
                    return Response({'detail': 'Incluye al menos una foto y máximo 20 evidencias en total.'}, status=400)
                for photo in photos:
                    validator = EvidenciaSerializer(data={'imagen': photo})
                    validator.is_valid(raise_exception=True)
                    photo.seek(0)

                data = {key: request.data.get(key) for key in request.data if key not in ('fotos', 'firma_base64')}
                if data.get('valor_servicio') == '':
                    data['valor_servicio'] = None
                report = ReporteVisita.objects.filter(visita=visit).first()
                validator = ReporteCreateSerializer(report, data=data)
                validator.is_valid(raise_exception=True)
                for field in ('persona_atiende', 'motivo_servicio', 'solucion_realizada'):
                    if not str(data.get(field, '')).strip():
                        raise serializers.ValidationError({field: 'Este campo es obligatorio.'})
                for selector, extra in [('equipo', 'equipo_otro'), ('ubicacion_equipo', 'ubicacion_otro')]:
                    if data.get(selector) == 'otro' and not str(data.get(extra, '')).strip():
                        raise serializers.ValidationError({extra: 'Especifica el valor de otro.'})

                signature = request.data.get('firma_base64', '')
                try:
                    signature_bytes = base64.b64decode(signature.split(';base64,')[-1], validate=True)
                    if len(signature_bytes) > 1024 * 1024:
                        raise ValueError('Firma demasiado grande')
                    signature_file = ContentFile(signature_bytes, name='firma.png')
                    serializers.ImageField().run_validation(signature_file)
                    signature_file.seek(0)
                except Exception:
                    raise serializers.ValidationError({'firma_base64': 'Se requiere una firma PNG o JPEG válida, de máximo 1 MB.'})

                # All validation precedes writes. The receipt, evidence rows,
                # report and completion are committed as one transaction.
                count = visit.evidencias.count()
                for index, photo in enumerate(photos):
                    evidence = EvidenciaFotografica(visita=visit, orden=count + index)
                    evidence.imagen.save(photo.name, photo, save=False)
                    created_files.append((evidence.imagen.storage, evidence.imagen.name))
                    evidence.save()
                report = validator.save(visita=visit)
                report.firma_base64 = signature
                report.firma_cliente.save(f'firma_{visit.numero_tarea}_{key}.png', signature_file, save=False)
                created_files.append((report.firma_cliente.storage, report.firma_cliente.name))
                report.save()
                visit.estado = VisitaTecnica.ESTADO_FINALIZADA
                visit.save(update_fields=['estado', 'fecha_actualizacion'])
                visit = VisitaTecnica.objects.get(pk=visit.pk)
                response = dict(VisitaDetailSerializer(visit).data)
                response['operation_id'] = key
                response['correo_programado'] = True
                VisitSyncReceipt.objects.create(visita=visit, usuario=request.user, operation_key=key, request_hash=digest, response_data=response)

                def notify():
                    from .views import _enviar_correo_visita_completada
                    _enviar_correo_visita_completada(VisitaTecnica.objects.select_related('cliente').get(pk=pk))
                transaction.on_commit(notify, robust=True)
            return Response(response)
        except Exception:
            # Storage isn't transactional. Remove only files created by this
            # rolled-back request, never pre-existing report/evidence files.
            for storage, name in created_files:
                try:
                    storage.delete(name)
                except Exception:
                    logger.exception('No se pudo limpiar un archivo de sincronización revertida')
            raise
