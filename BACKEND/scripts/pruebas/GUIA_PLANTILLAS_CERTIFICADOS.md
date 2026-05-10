# GUÍA DE PLANTILLAS PARA CERTIFICADOS

## Ubicación
Las plantillas deben estar en la carpeta: `plantillas/`

## Archivos requeridos
- `REGENCY.docx` - Para empresa "REGENCY"
- `PROTINCO.docx` - Para empresa "PROTINCO"
- `CONSORCIO.docx` - Para empresa "CONSORCIO"
- `REGENCY_HEALTH.docx` - Para empresa "REGENCY HEALTH" o "REGENCY_HEALTH"
- `REGENC_TECH.docx` - Para empresa "REGENCY TECH" o "REGENCY_TECH"

## Variables disponibles

Las plantillas Word deben contener variables entre llaves dobles `{{}}`:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `{{nombre_completo}}` | Nombre y apellido completo | Juan Pérez |
| `{{nombre}}` | Solo el nombre | Juan |
| `{{apellido}}` | Solo el apellido | Pérez |
| `{{cedula}}` | Cédula del colaborador | 1234567890 |
| `{{capacitacion}}` | Título de la capacitación | Seguridad Industrial |
| `{{fecha}}` | Fecha completa en español | 5 de enero de 2026 |
| `{{fecha_corta}}` | Fecha formato corto | 05/01/2026 |
| `{{empresa}}` | Nombre de la empresa | REGENCY |
| `{{cargo}}` | Cargo del colaborador | Desarrollador |
| `{{centro}}` | Centro operativo | Centro Principal |

## Ejemplo de uso en Word

```
                    CERTIFICADO DE CAPACITACIÓN

Por medio del presente certificado, se hace constar que:

                    {{nombre_completo}}
            Identificado con cédula: {{cedula}}

Ha completado satisfactoriamente la capacitación:

                    {{capacitacion}}

Otorgado por {{empresa}} el {{fecha}}

Cargo: {{cargo}}
Centro: {{centro}}
```

## Dónde usar las variables

Las variables pueden usarse en:
- ✅ Texto del cuerpo del documento
- ✅ Tablas
- ✅ Encabezados (headers)
- ✅ Pies de página (footers)

## Formato

- Las variables mantienen el formato del texto donde están insertadas
- Puedes aplicar: **negrita**, *cursiva*, <u>subrayado</u>, colores, fuentes, etc.
- La variable se reemplazará manteniendo el formato aplicado

## Proceso de generación

1. Se carga la plantilla según la empresa del colaborador
2. Se reemplazan todas las variables con los datos reales
3. Se convierte el Word a PDF usando MS Word COM
4. Se guarda en `media/certificados_generados/YYYY/MM/DD/`
5. Se crea registro en base de datos para caché (30 días)

## Caché de certificados

- Los certificados generados se guardan por 30 días
- Si se solicita el mismo certificado dentro de los 30 días, se retorna el archivo guardado
- No se regenera a menos que:
  - Hayan pasado más de 30 días
  - Se elimine manualmente el archivo

## Requisitos para generar certificado

1. Usuario autenticado con token JWT
2. Usuario debe tener colaborador asociado
3. Capacitación debe estar completada al 100% (`completada=1`)
4. Colaborador debe tener empresa asociada
5. Debe existir plantilla Word para esa empresa

## Endpoints disponibles

### Endpoint simplificado (Recomendado)
```
GET /capacitaciones/certificado/<id_capacitacion>/
```
- Obtiene `colaborador_id` automáticamente del token
- Solo requiere ID de capacitación

**Ejemplo:**
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/capacitaciones/certificado/1/
```

### Endpoint completo
```
GET /capacitaciones/descargar-certificado/<id_colaborador>/<id_capacitacion>/
```
- Requiere especificar colaborador_id y capacitacion_id
- Valida que el token corresponda al colaborador solicitado

**Ejemplo:**
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/capacitaciones/descargar-certificado/123/1/
```

## Respuestas

### 200 OK - Certificado generado
- Content-Type: `application/pdf`
- Header: `Cache-Control: max-age=2592000` (30 días)
- Header: `Content-Disposition: attachment; filename="certificado_<nombre>_<apellido>.pdf"`

### 400 Bad Request - Capacitación no completada
```json
{
  "error": "No has completado esta capacitación. Debes completarla al 100% para obtener el certificado."
}
```

### 400 Bad Request - Usuario sin colaborador
```json
{
  "error": "El usuario no tiene un colaborador asociado"
}
```

### 400 Bad Request - Sin empresa
```json
{
  "error": "El colaborador no tiene empresa asociada"
}
```

### 403 Forbidden - Sin permiso
```json
{
  "error": "No tienes permiso para descargar este certificado"
}
```

### 404 Not Found - Plantilla no encontrada
```json
{
  "error": "No se encontró la plantilla para la empresa EMPRESA_X"
}
```

### 500 Internal Server Error - Error de conversión
```json
{
  "error": "No se pudo convertir el certificado a PDF. Instala Microsoft Word o configura un conversor alternativo."
}
```

## Configuración técnica

### Base de datos
Tabla: `certificados_generados`

Campos:
- `id` (PK)
- `colaborador_id` (INT)
- `capacitacion_id` (INT)
- `archivo_pdf` (VARCHAR - ruta relativa)
- `fecha_generacion` (DATETIME)
- `fecha_actualizacion` (DATETIME)
- Unique constraint: `(colaborador_id, capacitacion_id)`

### Dependencias Python
```
python-docx==1.1.2
comtypes==1.4.14
```

### Requisitos del sistema
- Windows con Microsoft Word instalado (para conversión a PDF)
- O configurar conversor alternativo (pypandoc, unoconv, etc.)

## Troubleshooting

### Error: "No se pudo convertir el certificado a PDF"
**Causa:** Microsoft Word no está instalado o no se puede acceder vía COM

**Soluciones:**
1. Instalar Microsoft Word
2. Verificar que Word se puede abrir desde el sistema
3. Ejecutar como administrador si hay problemas de permisos

### Error: "No se encontró la plantilla"
**Causa:** Nombre de empresa no coincide con archivo de plantilla

**Soluciones:**
1. Verificar que existe el archivo en `plantillas/`
2. Revisar mapeo en código: `plantilla_map` en la vista
3. Verificar nombre de empresa en base de datos (tabla `epresa`)

### Variables no se reemplazan
**Causa:** Variables mal escritas en la plantilla

**Soluciones:**
1. Verificar que las variables usan llaves dobles: `{{variable}}`
2. No usar espacios: `{{ variable }}` ❌ vs `{{variable}}` ✅
3. Respetar mayúsculas/minúsculas exactas

## Ejemplo de prueba

```python
import requests

TOKEN = "tu_token_jwt_aqui"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Descargar certificado
response = requests.get(
    "http://localhost:8000/capacitaciones/certificado/1/",
    headers=headers
)

# Guardar PDF
if response.status_code == 200:
    with open("certificado.pdf", "wb") as f:
        f.write(response.content)
    print("Certificado descargado: certificado.pdf")
else:
    print(f"Error: {response.json()}")
```
