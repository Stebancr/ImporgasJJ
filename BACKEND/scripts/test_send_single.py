# Script de prueba para EnviarCorreoView
from django.contrib.auth import get_user_model
from django.test import Client
from usuarios.models import Colaboradores
from analitica.models import Epresa, Unidadnegocio, Proyecto, Centroop
from examenes.models import Cargo, Examen
from rest_framework_simplejwt.tokens import RefreshToken
import os

User = get_user_model()

# Asegurar usuario (modelo usa el campo `usuario` como USERNAME_FIELD)
username = '1112039941'
password = '1112039941'
user, created = User.objects.get_or_create(usuario=username)
if created:
    user.set_password(password)
    user.save()
print('User id:', user.id)

# Nota: creación de colaborador se realiza después de crear el cargo (campo obligatorio en el modelo)

# Preparar catálogos mínimos (reusar si existen, crear con campos obligatorios si no)
empresa = Epresa.objects.filter(estadoempresa=1).first()
if not empresa:
    empresa = Epresa.objects.create(nitempresa='900000000', nombre_empresa='EMPRESA TEST', estadoempresa=1)

unidad = Unidadnegocio.objects.filter(estadounidad=1).first()
if not unidad:
    unidad = Unidadnegocio.objects.create(nombreunidad='UNIDAD TEST', descripcionunidad='Unidad test', estadounidad=1, id_empresa=empresa)

proyecto = Proyecto.objects.filter(estadoproyecto=1).first()
if not proyecto:
    proyecto = Proyecto.objects.create(nombreproyecto='PROYECTO TEST', estadoproyecto=1, id_unidad=unidad)

centro = Centroop.objects.filter(estadocentrop=1).first()
if not centro:
    centro = Centroop.objects.create(nombrecentrop='CENTRO TEST', estadocentrop=1, id_proyecto=proyecto)

cargo, _ = Cargo.objects.get_or_create(nombrecargo='CARGO TEST')
examen, _ = Examen.objects.get_or_create(nombre='EXAMEN TEST', activo=True)

# Generar token
refresh = RefreshToken.for_user(user)
access = str(refresh.access_token)
print('ACCESS_TOKEN:', access)

# Cliente de pruebas
client = Client(HTTP_AUTHORIZATION=f'Bearer {access}')

# Preparar payload para envío individual
payload = {
    'nombre_trabajador': 'Prueba Uno',
    'documento_trabajador': '999999999',
    'correo_destino': 'destino.prueba@example.com',
    'centro_id': centro.idcentrop,
    'cargo_id': cargo.idcargo,
    'tipo_examen': 'INGRESO',
    'examenes_ids': [examen.id_examen]
}

# Intentar localizar colaborador existente y asociarlo al usuario (si existe)
col = Colaboradores.objects.filter(idcolaborador=1112039941).first()
if col:
    try:
        user.idcolaboradoru = col
        user.save()
        print('Usuario asociado al colaborador', col.idcolaborador)
    except Exception:
        pass
else:
    print('No se encontró Colaboradores(id=1112039941), se omite asociación')

# Ejecutar POST
resp = client.post('/examenes/correo/enviar/', payload, content_type='application/json')
print('Response status:', resp.status_code)
try:
    print('Response JSON:', resp.json())
except Exception:
    print('Response content:', resp.content)

# Consultar último cuerpo de correo creado
from examenes.models import CorreoExamenEnviado
correo = CorreoExamenEnviado.objects.filter(correos_destino__icontains=payload['correo_destino']).order_by('-id').first()
print('\n== cuerpo_correo en DB ==\n')
if correo:
    print(correo.cuerpo_correo)
else:
    print('No se encontró CorreoExamenEnviado para el destinatario')

print('\nFin script')
