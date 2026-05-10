# 📚 Documentación LMS Backend

## 🏗️ Arquitectura del Sistema

Sistema de gestión de aprendizaje (LMS) construido con Django REST Framework que integra:
- Gestión de usuarios y permisos
- Capacitaciones y evaluaciones
- Sistema de exámenes ocupacionales
- Generación de certificados
- Reportes y analítica

---

## 📋 Índice

1. [Instalación y Configuración](#instalación-y-configuración)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Módulos Principales](#módulos-principales)
4. [Sistema de Exámenes](#sistema-de-exámenes)
5. [Sistema de Certificados](#sistema-de-certificados)
6. [APIs y Endpoints](#apis-y-endpoints)
7. [Testing](#testing)
8. [Deployment](#deployment)

---

## 🚀 Instalación y Configuración

### Pre-requisitos
```bash
Python 3.8+
MySQL/MariaDB
Redis (para Celery)
```

### Instalación de Dependencias
```bash
pip install django djangorestframework django-cors-headers
pip install mysqlclient pymysql python-decouple
pip install djangorestframework-simplejwt
pip install pandas openpyxl
pip install django-crontab redis celery
pip install cloudinary  # Para almacenamiento en la nube
```

### Configuración Inicial
```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

### Variables de Entorno (.env)
```env
DEBUG=True
SECRET_KEY=tu-secret-key
DATABASE_NAME=nombre_bd
DATABASE_USER=usuario
DATABASE_PASSWORD=password
DATABASE_HOST=localhost
DATABASE_PORT=3306

# Cloudinary (opcional)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## 📁 Estructura del Proyecto

```
LMS-backend/
├── core/                   # Configuración principal
│   ├── settings.py         # Configuración Django
│   ├── urls.py             # URLs principales
│   ├── celery.py           # Configuración Celery
│   └── wsgi.py
├── usuarios/               # Gestión de usuarios
│   ├── models.py           # Usuarios, Roles, Permisos
│   ├── views.py            # Autenticación, Registro
│   ├── serializers.py
│   ├── permissions.py      # Permisos personalizados
│   └── tests.py
├── capacitaciones/         # Módulo de capacitaciones
│   ├── models.py           # Capacitaciones, Lecciones, Módulos
│   ├── views.py            # CRUD capacitaciones
│   ├── serializers.py
│   ├── utils.py            # Certificados, Excel
│   └── tests.py
├── examenes/               # Sistema de exámenes ocupacionales
│   ├── models.py           # Examen, RegistroExamenes, ExamenTrabajador
│   ├── views.py            # Envío masivo, Consultas
│   ├── serializers.py
│   └── tests.py
├── analitica/              # Reportes y analítica
│   ├── models.py           # Empresas, Proyectos, Centros OP
│   ├── views.py
│   ├── tasks.py            # Tareas Celery
│   └── tests.py
├── notificaciones/         # Sistema de notificaciones
│   ├── models.py
│   ├── views.py
│   ├── tasks.py
│   └── tests.py
├── media/                  # Archivos subidos
├── static/                 # Archivos estáticos
├── templates/              # Plantillas HTML
├── requirements.txt
├── manage.py
└── DOCUMENTACION.md        # Este archivo
```

---

## 🎯 Módulos Principales

### 1. Usuarios (usuarios/)
Sistema completo de autenticación y autorización.

**Modelos:**
- `Usuarios`: Información de usuario extendida
- `Cargo`: Cargos organizacionales
- `Niveles`: Niveles de acceso
- `Regional`: Regiones geográficas

**Endpoints Principales:**
```
POST   /usuarios/register/              # Registro
POST   /usuarios/login/                 # Login (JWT)
POST   /usuarios/token/refresh/         # Refresh token
GET    /usuarios/profile/               # Perfil actual
PUT    /usuarios/profile/update/        # Actualizar perfil
GET    /usuarios/list/                  # Listar usuarios
```

**Sistema de Permisos:**
```python
from usuarios.permissions import IsAdmin, IsCoordinador

class MiVista(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
```

---

### 2. Capacitaciones (capacitaciones/)
Gestión completa de cursos y capacitaciones.

**Modelos:**
- `Capacitaciones`: Curso/capacitación
- `Modulos`: Módulos del curso
- `Lecciones`: Lecciones de cada módulo
- `PreguntasLecciones`: Preguntas de evaluación
- `ProgresoColaboradores`: Progreso del estudiante

**Endpoints Principales:**
```
GET    /capacitaciones/                 # Listar capacitaciones
POST   /capacitaciones/                 # Crear capacitación
GET    /capacitaciones/{id}/            # Detalle
PUT    /capacitaciones/{id}/            # Actualizar
DELETE /capacitaciones/{id}/            # Eliminar
GET    /capacitaciones/{id}/progreso/   # Progreso del usuario
POST   /capacitaciones/{id}/completar/  # Marcar como completada
```

**Características:**
- Upload de materiales (videos, PDFs, imágenes)
- Generación automática de certificados
- Tracking de progreso
- Evaluaciones con calificación

---

### 3. Exámenes (examenes/)
Sistema dual de exámenes ocupacionales de SST.

**Modelos:**
- `Examen`: Tipos de examen (Audiometría, Optometría, etc.)
- `CorreoExamenEnviado`: Lote de envío masivo
- `RegistroExamenes`: Registro individual por trabajador
- `ExamenTrabajador`: Relación M2M (registro-examen)

**Tipos de Examen:**
- `INGRESO`: Exámenes para nuevos colaboradores
- `PERIODICO`: Exámenes periódicos de SST

**Endpoints Principales:**
```
POST   /examenes/correo/enviar-masivo/              # Envío masivo CSV
GET    /examenes/correo/detalle/{uuid}/             # Detalle de lote
GET    /examenes/trabajadores/{documento}/          # Exámenes por trabajador
GET    /examenes/registros-por-tipo/?tipo=INGRESO   # Filtrar por tipo
GET    /examenes/                                   # Listar todos
POST   /examenes/                                   # Crear examen
```

**Formato CSV para Envío Masivo:**
```csv
NombresCompletos,TipoDocumento,NumeroDocumento,Celular,CorreoElectronico,FechaNacimiento,Edad,EPS,Cargo,TipoExamen,Examenes
Juan Perez,CC,1234567890,3001234567,juan@email.com,1990-01-15,34,SURA,Operario,INGRESO,"AUDIOMETRIA,OPTOMETRIA"
Maria Lopez,CC,9876543210,3009876543,maria@email.com,1985-05-20,39,SANITAS,Supervisor,PERIODICO,"ESPIROMETRIA,GLICEMIA"
```

**Características:**
- Auto-detección de encoding (UTF-8, Latin-1, CP1252, ISO-8859-1)
- Auto-detección de delimitador (coma, punto y coma)
- Validación exhaustiva de datos
- Generación de Excel con hojas separadas por tipo
- Asignación flexible de exámenes por trabajador
- Relación M2M normalizada en BD

**Flujo de Trabajo:**
1. Preparar CSV con trabajadores y exámenes
2. POST a `/examenes/correo/enviar-masivo/`
3. Sistema valida y procesa
4. Genera Excel con hojas INGRESO/PERIODICO
5. Retorna uuid_correo para tracking
6. Consultar estado: `/examenes/correo/detalle/{uuid}/`

---

### 4. Certificados (capacitaciones/utils.py)
Generación automática de certificados PDF.

**Características:**
- Plantillas HTML personalizables
- Conversión HTML → PDF
- Almacenamiento en media/ o Cloudinary
- Generación automática al completar curso

**Uso:**
```python
from capacitaciones.utils import generar_certificado_pdf

certificado_path = generar_certificado_pdf(
    usuario=request.user,
    capacitacion=capacitacion,
    fecha_completado=timezone.now()
)
```

---

### 5. Analítica (analitica/)
Reportes y métricas del sistema.

**Modelos:**
- `Empresa`: Empresas del sistema
- `UnidadNegocio`: Unidades de negocio
- `Proyecto`: Proyectos
- `CentroOp`: Centros operativos

**Endpoints:**
```
GET    /analitica/dashboard/            # Dashboard general
GET    /analitica/reportes/capacitaciones/  # Reporte capacitaciones
GET    /analitica/reportes/examenes/    # Reporte exámenes
GET    /analitica/empresas/             # Listar empresas
```

---

## 🔌 APIs y Endpoints

### Autenticación
Todos los endpoints (excepto login/register) requieren JWT token:
```bash
# Header requerido
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Formato de Respuesta Estándar
```json
{
  "status": "success",
  "data": { /* datos */ },
  "message": "Operación exitosa"
}
```

### Errores
```json
{
  "status": "error",
  "message": "Descripción del error",
  "errors": { /* detalles */ }
}
```

### Paginación
```
GET /endpoint/?page=1&page_size=20
```

Respuesta:
```json
{
  "count": 100,
  "next": "http://api.com/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## 🧪 Testing

### Ejecutar Tests
```bash
# Todos los tests
python manage.py test

# Tests de una app específica
python manage.py test usuarios
python manage.py test examenes
python manage.py test capacitaciones

# Test específico
python manage.py test usuarios.tests.TestLogin
```

### Estructura de Tests
Cada app tiene su archivo `tests.py` con:
- Tests de modelos
- Tests de APIs/endpoints
- Tests de permisos
- Tests de validaciones

**Ejemplo (examenes/tests.py):**
```python
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

class ExamenesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Setup inicial
    
    def test_envio_masivo_csv(self):
        # Test envío CSV
        pass
    
    def test_filtro_por_tipo(self):
        # Test endpoint filtro
        pass
```

---

## 🚀 Deployment

### Producción con Gunicorn
```bash
pip install gunicorn

gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/static/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}
```

### Celery Worker (Background Tasks)
```bash
# Worker
celery -A core worker -l info

# Beat (tareas programadas)
celery -A core beat -l info
```

### Configuración de Producción
```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['tu-dominio.com']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': '/path/to/my.cnf',
        }
    }
}

# Static files
STATIC_ROOT = '/var/www/static/'
MEDIA_ROOT = '/var/www/media/'

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🔒 Seguridad

### Mejores Prácticas Implementadas
- ✅ JWT para autenticación
- ✅ Permisos granulares por endpoint
- ✅ Validación exhaustiva de entrada
- ✅ ORM para prevenir SQL injection
- ✅ CORS configurado
- ✅ Rate limiting (opcional con DRF throttling)
- ✅ Sanitización de archivos subidos

---

## 📊 Base de Datos

### Migraciones
```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Ver migraciones
python manage.py showmigrations

# Rollback
python manage.py migrate examenes 0005
```

### Respaldo
```bash
# Dump
python manage.py dumpdata > backup.json

# Restore
python manage.py loaddata backup.json

# MySQL dump
mysqldump -u user -p database_name > backup.sql
```

---

## 🛠️ Utilidades

### Comandos Personalizados
```bash
# Inspeccionar tablas existentes
python manage.py inspectdb tabla_nombre > app/models.py

# Crear datos de prueba
python manage.py loaddata fixtures/initial_data.json

# Limpiar sesiones expiradas
python manage.py clearsessions
```

### Django Shell
```python
python manage.py shell

# Ejemplos
from usuarios.models import Usuarios
from examenes.models import RegistroExamenes

# Ver registros por tipo
RegistroExamenes.objects.filter(tipo_examen='INGRESO').count()

# Crear usuario
user = Usuarios.objects.create_user(
    username='test',
    email='test@email.com',
    password='password123'
)
```

---

## 📝 Convenciones de Código

### Estilo
```python
# PEP 8
- Indentación: 4 espacios
- Líneas: máximo 79 caracteres (flexible a 120)
- Imports: stdlib, third-party, local

# Nombres
class MiModelo(models.Model):  # PascalCase
def mi_funcion():              # snake_case
MI_CONSTANTE = "valor"         # UPPER_CASE
```

### Docstrings
```python
def mi_funcion(param1, param2):
    """
    Descripción breve.
    
    Args:
        param1 (str): Descripción
        param2 (int): Descripción
    
    Returns:
        dict: Descripción del retorno
    """
    pass
```

---

## 🐛 Troubleshooting

### Problemas Comunes

**Error de conexión a BD:**
```bash
# Verificar credenciales en .env
# Verificar que MySQL esté corriendo
sudo service mysql status
```

**Migraciones conflictivas:**
```bash
python manage.py migrate --fake app_name migration_name
```

**Archivos media no se sirven:**
```python
# settings.py (solo development)
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 📞 Soporte

### Logs
```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
}
```

### Debug
```python
# Activar Django Debug Toolbar
pip install django-debug-toolbar

# settings.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

---

## 📈 Roadmap

### Funcionalidades Futuras
- [ ] Sistema de notificaciones push
- [ ] Integración con LDAP/Active Directory
- [ ] Dashboard de analítica avanzada
- [ ] App móvil (React Native)
- [ ] Videoconferencias integradas
- [ ] Gamificación
- [ ] Reportes personalizables

---

## 📄 Licencia

Propiedad de Regency. Todos los derechos reservados.

---

## 🤝 Contribución

Este es un proyecto interno. Para contribuir:
1. Crear branch desde `main`
2. Hacer cambios y commits descriptivos
3. Push y crear Pull Request
4. Esperar code review
5. Merge una vez aprobado

---

**Última actualización:** Enero 2026  
**Versión:** 2.0  
**Mantenido por:** Equipo de Desarrollo Regency
