"""Retira únicamente archivos huérfanos de la carpeta temporal de visitas."""

import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from AppVisits.models import EvidenciaFotografica
from AppVisits.views import _purge_temporary_images
from AppVisits.models import VisitaTecnica


class Command(BaseCommand):
    help = 'Muestra o limpia fotos temporales huérfanas; nunca toca evidencias históricas.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Ejecuta la limpieza. Por defecto sólo muestra el total.')
        parser.add_argument('--days', type=int, default=30, help='Antigüedad mínima de huérfanos (predeterminado: 30 días).')

    def handle(self, *args, **options):
        days = options['days']
        if days < 7:
            raise ValueError('La antigüedad mínima es de 7 días.')
        apply = options['apply']
        if apply:
            for visit_id in VisitaTecnica.objects.filter(
                estado=VisitaTecnica.ESTADO_FINALIZADA, pdf_estado='generado',
                evidencias__es_temporal=True, evidencias__eliminada_en__isnull=True,
            ).distinct().values_list('pk', flat=True):
                _purge_temporary_images(visit_id)
        root = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'evidencias_temporales'))
        if not os.path.isdir(root):
            self.stdout.write('Sin archivos temporales.')
            return
        referenced = set(EvidenciaFotografica.objects.exclude(imagen='').values_list('imagen', flat=True))
        cutoff = time.time() - days * 86400
        candidates = 0
        removed = 0
        for directory, _, files in os.walk(root, followlinks=False):
            for filename in files:
                path = os.path.realpath(os.path.join(directory, filename))
                if os.path.commonpath((root, path)) != root or not os.path.isfile(path):
                    continue
                relative = os.path.relpath(path, settings.MEDIA_ROOT).replace(os.sep, '/')
                if relative in referenced or os.path.getmtime(path) > cutoff:
                    continue
                candidates += 1
                if apply:
                    os.remove(path)
                    removed += 1
        self.stdout.write(f'Archivos temporales huérfanos elegibles: {candidates}; eliminados: {removed}.')
