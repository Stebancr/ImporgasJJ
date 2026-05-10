from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import Client
import json

User = get_user_model()

# 1) Obtener o crear usuario
usuario_val = '1112039941'
password_val = '1112039941'
user, created = User.objects.get_or_create(usuario=usuario_val)
if created:
    user.tipousuario = 1
    user.set_password(password_val)
    user.save()
else:
    # Asegurar password conocido
    user.set_password(password_val)
    user.save()

print('User id:', user.id)

# 2) Asegurar colaborador ligado
from usuarios.models import Colaboradores
colab, ccreated = Colaboradores.objects.get_or_create(cccolaborador=usuario_val, defaults={
    'nombrecolaborador': 'UsuarioPrueba',
    'apellidocolaborador': 'Prueba',
    'correocolaborador': 'usuario.prueba@example.com'
})
if not ccreated:
    # update email/name
    colab.nombrecolaborador = colab.nombrecolaborador or 'UsuarioPrueba'
    colab.correocolaborador = colab.correocolaborador or 'usuario.prueba@example.com'
    colab.save()

# Asociar al usuario
# Usuarios model uses field idcolaboradoru FK
try:
    # Some user instances might already have the FK object
    if getattr(user, 'idcolaboradoru', None) != colab:
        user.idcolaboradoru = colab
        user.save()
except Exception:
    # Fallback if direct assignment incompatible
    pass

print('Colaborador id:', colab.idcolaborador)

# 3) Crear catálogo mínimo necesario
from analitica.models import Epresa, Unidadnegocio, Proyecto, Centroop
from usuarios.models import Cargo
from examenes.models import Examen

empresa, _ = Epresa.objects.get_or_create(nombre_empresa='TEST EMPRESA', defaults={'nitempresa':'000','estadoempresa':1})
unidad, _ = Unidadnegocio.objects.get_or_create(nombreunidad='TEST UNIDAD', defaults={'descripcionunidad':'desc','estadounidad':1,'id_empresa':empresa})
proyecto, _ = Proyecto.objects.get_or_create(nombreproyecto='TEST PROYECTO', defaults={'estadoproyecto':1,'id_unidad':unidad})
centro, _ = Centroop.objects.get_or_create(nombrecentrop='TEST CENTRO', defaults={'estadocentrop':1,'id_proyecto':proyecto})
cargo, _ = Cargo.objects.get_or_create(nombrecargo='TEST CARGO', defaults={'estadocargo':1})
examen, _ = Examen.objects.get_or_create(nombre='TEST EXAMEN', defaults={'activo':True})

print('Catalogos preparados')

# 4) Generar token JWT
refresh = RefreshToken.for_user(user)
access = str(refresh.access_token)
print('ACCESS_TOKEN:', access)

# 5) Escribir CSV de prueba
csv_path = 'scripts/trabajadores_test.csv'
with open(csv_path, 'w', encoding='utf-8') as f:
    f.write('empresa,unidad,proyecto,centro,nombre,cc,ciudad,cargo,tipoexamen,examenes\n')
    f.write('TEST EMPRESA,TEST UNIDAD,TEST PROYECTO,TEST CENTRO,Juan Perez,12345678,Medellin,TEST CARGO,INGRESO,TEST EXAMEN\n')

print('CSV escrito en', csv_path)

# 6) Usar Django test client para POST multipart
client = Client(HTTP_AUTHORIZATION=f'Bearer {access}')
with open(csv_path, 'rb') as csvfile:
    response = client.post('/examenes/correo/enviar-masivo/', {'archivo_csv': csvfile})

print('Response status:', response.status_code)
try:
    data = json.loads(response.content)
    print('Response JSON:', json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print('Response content:', response.content)

# 7) Si se devolvió uuid_correo, consultar en BD e imprimir cuerpo
uuid_correo = None
try:
    if isinstance(data, dict) and 'uuid_correo' in data:
        uuid_correo = data['uuid_correo']
except Exception:
    pass

if uuid_correo:
    from examenes.models import CorreoExamenEnviado
    c = CorreoExamenEnviado.objects.filter(uuid_correo=uuid_correo).first()
    if c:
        print('\n== cuerpo_correo en DB ==\n')
        print(c.cuerpo_correo)
    else:
        print('No se encontró CorreoExamenEnviado con ese uuid')
else:
    print('No se obtuvo uuid_correo en la respuesta')

print('Fin script')
