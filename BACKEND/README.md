# LMS Backend - Sistema 360

python manage.py runserver 0.0.0.0:8000      

Sistema de gestión de aprendizaje (LMS) construido con Django REST Framework.

## 📚 Documentación Completa

Para la documentación completa del proyecto, consulta: **[DOCUMENTACION.md](DOCUMENTACION.md)**

## 🚀 Instalación Rápida

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
python manage.py makemigrations
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

## 📋 Dependencias Principales

```bash
pip install django djangorestframework django-cors-headers
pip install mysqlclient pymysql python-decouple
pip install djangorestframework-simplejwt
pip install pandas openpyxl
pip install django-crontab redis celery
pip install cloudinary
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
python manage.py test

# Tests por app
python manage.py test usuarios
python manage.py test examenes
python manage.py test capacitaciones
python manage.py test analitica
```

## 📂 Estructura del Proyecto

```
LMS-backend/
├── core/                   # Configuración principal
├── usuarios/               # Gestión de usuarios y autenticación
├── capacitaciones/         # Módulo de capacitaciones
├── examenes/               # Sistema de exámenes ocupacionales
├── analitica/              # Reportes y analítica
├── notificaciones/         # Sistema de notificaciones
├── media/                  # Archivos subidos
├── static/                 # Archivos estáticos
└── DOCUMENTACION.md        # Documentación completa
```

## 🔗 Enlaces

- **Documentación:** [DOCUMENTACION.md](DOCUMENTACION.md)
- **API REST:** http://localhost:8000/api/
- **Admin Panel:** http://localhost:8000/admin/

## 📞 Soporte

Para más información, consulta la documentación completa en `DOCUMENTACION.md`.


def get(self, request, *args, **kwargs):
        colaborador_id = kwargs.get('id')
        try:
            colaborador = Colaboradores.objects.values(
                'idcolaborador',
                'nombrecolaborador',
                'apellidocolaborador',
                'cccolaborador'
            ).get(idcolaborador=colaborador_id)
            return JsonResponse(colaborador, safe=False)
        except Colaboradores.DoesNotExist:
            return JsonResponse({'error': 'Colaborador no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)




registar usuario

{
  "usuario": "steban",
  "clave": "123456",
  "idcolaborador": {
    "cc_colaborador": "10223344",
    "nombre_colaborador": "Steban",
    "apellido_colaborador": "Rodriguez",
    "cargo_colaborador": 1,
    "correo_colaborador": "steban@example.com",
    "telefo_colaborador": "3001234567",
    "nivel_colaborador": 2,
    "empresa_colab": 1,
    "regional_colab": 1
  }
}


python manage.py makemigrations
python manage.py migrate


pip install djangorestframework PyJWT


django.db.utils.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails (`formularios`.`colaboradores`, CONSTRAINT `fkCentropU` FOREIGN KEY (`centroOP`) REFERENCES `centroop` (`idCentrOp`))')
[22/Oct/2025 11:17:42] "POST /user/register/ HTTP/1.1" 500 292075




ALTER TABLE colaboradores DROP FOREIGN KEY fkCentropU;
ALTER TABLE colaboradores DROP COLUMN centroOP;


python manage.py makemigrations
python manage.py migrate contenttypes
python manage.py migrate auth
python manage.py migrate

{
    "usuario": "stebanC",
    "clave": "123456",
    "is_staff": "1",
    "idcolaborador": {
        "cc_colaborador": "10223344455",
        "nombre_colaborador": "StebanC",
        "apellido_colaborador": "RodriguezC",
        "cargo_colaborador": 1,
        "correo_colaborador": "steban@example.com",
        "telefo_colaborador": "3001234567",
        "nivel_colaborador": 1,
        "empresa_colab": 1,
        "regional_colab": 1
    },
    "centros": [1]
}

{
    "idcolaborador": {
        "cc_colaborador": [
            "colaboradores with this cc colaborador already exists."
        ]
    }
}



al momento de crear usuarios de prueba se determina si queire crear colaborador o un colaborador a prueba, el cual no tendra todos los datos, solo un (preguntar bien esta parte)


iniciar redis

1. sudo service redis-server start
2. verificar uncionamiento "redis-cli ping" tiene que retornar pong



iniciar celery

1. celery -A core worker --loglevel=info --pool=solo
2. celery -A core beat -l info



12/12/2025

se pide agregar una nueva modalidad la cual se agrega un gerente/encargado a los proyectos y unidad de negocio el cual le comunique a los encargados los usuarios que no realizan las capacitaciones, se agrega una nueva columna a los modelos proyectos y centroo de operacion, para llenarlos obligatiriamente al crear una unidad y proyecto, 



vista, no hace falta comprar la empresa con la unidad y demas, ya se hace solo ya que como esta la jerarquia ya predispone de esta consulta sin duplicar datos