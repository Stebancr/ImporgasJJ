"""Healthcheck mínimo para Docker y el proxy de producción."""

from django.db import connection
from django.http import JsonResponse


def health(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.fetchone()
    return JsonResponse({'status': 'ok'})


def api_root(request):
    """Respuesta estable para comprobar la API pública sin revelar configuración."""

    return JsonResponse({
        'status': 'ok',
        'service': 'Imporgas JJ API',
        'version': 'v1',
    })
