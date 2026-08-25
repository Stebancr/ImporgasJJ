# Documentación Completa - AppVisits (Sistema de Visitas Técnicas)

## 📋 Tabla de Contenidos
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelos de Datos](#modelos-de-datos)
4. [APIs REST](#apis-rest)
5. [Flujo de Negocio](#flujo-de-negocio)
6. [Permisos y Autenticación](#permisos-y-autenticación)
7. [Integración en la Aplicación](#integración-en-la-aplicación)
8. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 Descripción General

**AppVisits** es un módulo Django que gestiona las visitas técnicas de la empresa. El sistema permite:

- **Registrar visitas técnicas** desde la aplicación móvil o web
- **Asignar técnicos** a las visitas (empleados con rol técnico)
- **Gestionar el ciclo de vida** de una visita (pendiente → en proceso → finalizada)
- **Generar reportes técnicos** con detalles de la intervención
- **Capturar evidencia fotográfica** de los trabajos realizados
- **Generar PDFs** con los reportes formales
- **Tracking de visitas** mediante calendario

### Aclaración Importante: Técnicos vs Usuarios
- **Técnicos = Empleados con rol técnico** (tipo_usuario = 0 en la tabla Credenciales)
- **NO son usuarios regulares** de la plataforma
- Tienen acceso limitado: solo ven sus propias visitas asignadas
- Son gestionados por administradores

---

## 🏗️ Arquitectura del Sistema

```
AppVisits/
├── models.py           → Modelos de datos (ClienteVisita, VisitaTecnica, ReporteVisita, EvidenciaFotografica)
├── views.py            → Endpoints API REST
├── serializers.py      → Validación y serialización de datos
├── permissions.py      → Control de acceso (Admin vs Técnico)
├── urls.py             → Rutas de la API
├── admin.py            → Panel administrativo Django
├── apps.py             → Configuración de la app
└── migrations/         → Migraciones de base de datos
```

**Integración en el Proyecto:**
```
BACKEND/
├── core/
│   ├── settings.py     → Registra 'AppVisits' en INSTALLED_APPS (línea 73)
│   └── urls.py         → Incluye las rutas: path('visits/', include('AppVisits.urls')) (línea 31)
├── usuarios/           → Módulo de usuarios y autenticación
├── ecommerce/          → Módulo de productos y pedidos
├── crmChat/            → Módulo de chat CRM
└── AppVisits/          ← Aquí estamos
```

---

## 📊 Modelos de Datos

### 1. **ClienteVisita**
Información del cliente para quien se realiza la visita.

```python
class ClienteVisita(models.Model):
    nombre              # Nombre del cliente (requerido)
    identificacion      # Cédula/RUC (opcional)
    telefono           # Teléfono de contacto (opcional)
    correo             # Email del cliente (opcional)
    direccion          # Dirección donde se realiza la visita (requerido)
    fecha_creacion     # Fecha de registro automática
```

**Tabla en BD:** `visita_cliente`

---

### 2. **VisitaTecnica**
Representa una visita técnica asignada a un técnico.

```python
class VisitaTecnica(models.Model):
    # Identificación
    numero_tarea       # ID único auto-generado (ej: 3847562)
    
    # Relaciones
    tecnico            # FK → Credenciales (tipo_usuario=0) - Técnico asignado
    cliente            # FK → ClienteVisita
    creado_por         # FK → Credenciales - Quién creó la visita (Admin)
    
    # Información de la tarea
    tipo_tarea         # Choices: 'mantenimiento', 'instalacion', 'reparacion', 'revision', 'visita_tecnica', 'garantia'
    descripcion        # Descripción de la tarea a realizar
    
    # Programación
    fecha              # Fecha de la visita
    hora               # Hora programada
    
    # Estado
    estado             # Choices: 'pendiente', 'en_proceso', 'finalizada', 'cancelada'
    observaciones_iniciales  # Notas iniciales
    
    # Auditoría
    fecha_creacion     # Cuándo se creó el registro
    fecha_actualizacion # Cuándo se actualizó por última vez
```

**Estados de una Visita:**
- `pendiente` - Creada, esperando que técnico inicie
- `en_proceso` - Técnico ha iniciado la visita
- `finalizada` - Técnico completó y envió reporte
- `cancelada` - Visita cancelada

**Tabla en BD:** `visita_tecnica`

---

### 3. **ReporteVisita**
Reporte detallado que genera el técnico al finalizar la visita (relación 1:1 con VisitaTecnica).

```python
class ReporteVisita(models.Model):
    # Relación
    visita             # OneToOneField → VisitaTecnica
    
    # Información de la intervención
    persona_atiende    # Nombre de quién atendió en el cliente
    equipo             # Tipo de equipo: estufa, horno, calentador, parrilla, caldera, calefactor, otro
    equipo_otro        # Especificación si es "otro"
    ubicacion_equipo   # Dónde está: cocina, patio, balcón, exterior, sótano, otro
    ubicacion_otro     # Especificación si es "otro"
    
    # Descripción del trabajo
    motivo_servicio    # Por qué se llamó el técnico
    solucion_realizada # Qué se hizo para resolver
    observaciones      # Observaciones adicionales
    recomendaciones    # Recomendaciones al cliente
    
    # Tiempo y costos
    inicio_desplazamiento  # Hora exacta en que inició (auto-generada)
    duracion_desplazamiento # Tiempo de desplazamiento
    valor_servicio     # Monto cobrado
    metodo_pago        # Cómo pagó: efectivo, transferencia, tarjeta, crédito, otro
    
    # Firma y validación
    firma_cliente      # ImageField - Firma del cliente en la app móvil
    
    # Auditoría
    creado_en          # Fecha de creación
    actualizado_en     # Fecha de última actualización
```

**Tabla en BD:** `visita_reporte`

---

### 4. **EvidenciaFotografica**
Fotos que captura el técnico durante la visita (máximo 20 por visita).

```python
class EvidenciaFotografica(models.Model):
    visita             # FK → VisitaTecnica
    imagen             # ImageField - Foto capturada
    descripcion        # Descripción de qué muestra la foto (opcional)
    orden              # Número de orden para mostrar secuencialmente
    subida_en          # Timestamp de cuándo se subió
```

**Tabla en BD:** `visita_evidencia`

---

## 🔌 APIs REST

### **Base URL**
```
/visits/
```

### **1. Listar Técnicos (Admin)**

**GET** `/visits/tecnicos/`

**Autenticación:** Requerida (Admin solo)

**Respuesta:**
```json
[
  {
    "id": 5,
    "usuario": "tecnico1",
    "nombre_completo": "Juan Pérez García",
    "correo": "juan@example.com",
    "telefono": "3165266734"
  }
]
```

---

### **2. Listar Visitas**

**GET** `/visits/`

**Autenticación:** Requerida

**Comportamiento:**
- **Admin** (tipo_usuario ≥ 1): Ve TODAS las visitas
- **Técnico** (tipo_usuario = 0): Ve SOLO sus propias visitas

**Query Parameters:**
- `estado` - Filtrar por estado: 'pendiente', 'en_proceso', 'finalizada', 'cancelada' (default: all)
- `tecnico_id` - Filtrar visitas de un técnico específico
- `fecha` - Filtrar por fecha exacta (YYYY-MM-DD)
- `mes` - Filtrar por mes (YYYY-MM)
- `search` - Buscar por nombre cliente, dirección o número de tarea

**Respuesta:**
```json
[
  {
    "id": 1,
    "numero_tarea": "3847562",
    "cliente_nombre": "Carlos López",
    "cliente_direccion": "Calle 5 #12-34, Bogotá",
    "cliente_telefono": "3104567890",
    "tipo_tarea": "reparacion",
    "tipo_tarea_display": "Reparación",
    "fecha": "2026-08-15",
    "hora": "10:30:00",
    "estado": "pendiente",
    "estado_display": "Pendiente",
    "tecnico_id": 5,
    "tecnico_nombre": "Juan Pérez García",
    "tiene_reporte": false,
    "evidencias_count": 0,
    "fecha_creacion": "2026-08-05T10:00:00Z"
  }
]
```

---

### **3. Crear Visita (Admin)**

**POST** `/visits/`

**Autenticación:** Requerida (Admin solo)

**Request Body:**
```json
{
  "cliente_nombre": "María Rodríguez",
  "cliente_identificacion": "1234567890",
  "cliente_telefono": "3216543210",
  "cliente_correo": "maria@example.com",
  "cliente_direccion": "Carrera 7 #45-67, Medellín",
  "tipo_tarea": "instalacion",
  "fecha": "2026-08-20",
  "hora": "14:00:00",
  "descripcion": "Instalación de calentador nuevo",
  "observaciones_iniciales": "Cliente solicita instalación rápida",
  "tecnico_id": 5
}
```

**Respuesta (201 Created):**
```json
{
  "id": 2,
  "numero_tarea": "4562891",
  "cliente": { ... },
  "tecnico": { ... },
  "tipo_tarea": "instalacion",
  "fecha": "2026-08-20",
  "hora": "14:00:00",
  "descripcion": "Instalación de calentador nuevo",
  "observaciones_iniciales": "Cliente solicita instalación rápida",
  "estado": "pendiente",
  "reporte": null,
  "evidencias": []
}
```

---

### **4. Obtener Detalle de Visita**

**GET** `/visits/{id}/`

**Autenticación:** Requerida

**Permisos:**
- Admin: Acceso total
- Técnico: Solo si es su visita asignada

**Respuesta:**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "cliente": {
    "id": 1,
    "nombre": "Carlos López",
    "identificacion": "123456789",
    "telefono": "3104567890",
    "correo": "carlos@example.com",
    "direccion": "Calle 5 #12-34, Bogotá"
  },
  "tecnico": {
    "id": 5,
    "usuario": "tecnico1",
    "nombre_completo": "Juan Pérez García",
    "correo": "juan@example.com",
    "telefono": "3165266734"
  },
  "tipo_tarea": "reparacion",
  "tipo_tarea_display": "Reparación",
  "fecha": "2026-08-15",
  "hora": "10:30:00",
  "descripcion": "Reparación de estufa",
  "observaciones_iniciales": "Problema con piloto",
  "estado": "en_proceso",
  "estado_display": "En Proceso",
  "creado_por": { ... },
  "fecha_creacion": "2026-08-05T10:00:00Z",
  "fecha_actualizacion": "2026-08-15T10:15:00Z",
  "reporte": {
    "id": 1,
    "persona_atiende": "Doña Rosa",
    "equipo": "estufa",
    "equipo_display": "Estufa",
    "ubicacion_equipo": "cocina",
    "ubicacion_display": "Cocina",
    "motivo_servicio": "Piloto no enciende",
    "solucion_realizada": "Se limpió la tobera y se ajustó el piloto",
    "valor_servicio": "150000.00",
    "metodo_pago": "efectivo",
    "firma_cliente": "https://..."
  },
  "evidencias": [
    {
      "id": 1,
      "imagen": "https://...",
      "descripcion": "Estado anterior de la estufa",
      "orden": 0,
      "subida_en": "2026-08-15T10:30:00Z"
    }
  ]
}
```

---

### **5. Actualizar Visita (Admin)**

**PATCH** `/visits/{id}/`

**Autenticación:** Requerida (Admin solo)

**Campos actualizables:**
- `tipo_tarea`
- `fecha`
- `hora`
- `descripcion`
- `observaciones_iniciales`
- `estado`
- `tecnico`

**Request Body (ejemplo):**
```json
{
  "fecha": "2026-08-22",
  "tecnico_id": 6
}
```

**Respuesta:** Objeto VisitaTecnica actualizado

---

### **6. Eliminar Visita (Admin)**

**DELETE** `/visits/{id}/`

**Autenticación:** Requerida (Admin solo)

**Respuesta:** 204 No Content

---

### **7. Iniciar Visita (Técnico)**

**POST** `/visits/{id}/iniciar/`

**Autenticación:** Requerida

**Descripción:**
- Cambia estado de `pendiente` → `en_proceso`
- Auto-crea el ReporteVisita si no existe
- Registra `inicio_desplazamiento` con timestamp actual

**Validaciones:**
- Solo técnico asignado o admin puede iniciar
- La visita DEBE estar en estado `pendiente`

**Request Body:** (vacío)

**Respuesta (200 OK):**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "estado": "en_proceso",
  ...
}
```

---

### **8. Finalizar Visita (Técnico - Submit Report)**

**POST** `/visits/{id}/finalizar/`

**Autenticación:** Requerida

**Content-Type:** `multipart/form-data`

**Descripción:**
- Cambia estado de `pendiente|en_proceso` → `finalizada`
- Recibe datos del reporte técnico
- Acepta firma como imagen o base64
- Genera timestamp de finalización

**Form Data:**
```
persona_atiende=Doña Rosa
equipo=estufa
ubicacion_equipo=cocina
motivo_servicio=Piloto no enciende
solucion_realizada=Se limpió la tobera y se ajustó el piloto
observaciones=Equipo en buen estado después de la reparación
recomendaciones=Hacer mantenimiento cada 6 meses
valor_servicio=150000
metodo_pago=efectivo
firma_cliente=[file o base64]
duracion_desplazamiento=45 minutos
```

**Respuesta (200 OK):**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "estado": "finalizada",
  "reporte": {
    "persona_atiende": "Doña Rosa",
    ...
  }
}
```

---

### **9. Subir Fotos (Técnico)**

**POST** `/visits/{id}/fotos/`

**Autenticación:** Requerida

**Content-Type:** `multipart/form-data`

**Form Data:**
```
fotos=[archivo1.jpg]
fotos=[archivo2.jpg]
fotos=[archivo3.jpg]
```

**Validaciones:**
- Máximo 20 fotos por visita
- Solo técnico asignado o admin

**Respuesta (201 Created):**
```json
[
  {
    "id": 1,
    "imagen": "https://...",
    "descripcion": "",
    "orden": 0,
    "subida_en": "2026-08-15T10:30:00Z"
  },
  {
    "id": 2,
    "imagen": "https://...",
    "descripcion": "",
    "orden": 1,
    "subida_en": "2026-08-15T10:30:05Z"
  }
]
```

---

### **10. Eliminar Foto**

**DELETE** `/visits/{id}/fotos/{foto_id}/`

**Autenticación:** Requerida

**Permisos:**
- Admin o técnico asignado a la visita

**Respuesta:** 204 No Content

---

### **11. Calendario de Visitas**

**GET** `/visits/calendario/?mes=YYYY-MM`

**Autenticación:** Requerida

**Descripción:**
- Devuelve visitas agrupadas por fecha
- Admin ve todas, técnico ve solo sus visitas

**Respuesta:**
```json
{
  "2026-08-15": [
    {
      "id": 1,
      "numero_tarea": "3847562",
      "cliente_nombre": "Carlos López",
      "hora": "10:30:00",
      "estado": "en_proceso",
      "tipo_tarea": "Reparación",
      "tecnico_nombre": "Juan Pérez García"
    }
  ],
  "2026-08-20": [
    {
      "id": 2,
      "numero_tarea": "4562891",
      "cliente_nombre": "María Rodríguez",
      "hora": "14:00:00",
      "estado": "pendiente",
      "tipo_tarea": "Instalación",
      "tecnico_nombre": "Juan Pérez García"
    }
  ]
}
```

---

### **12. Descargar PDF del Reporte**

**GET** `/visits/{id}/pdf/`

**Autenticación:** Requerida (Admin solo)

**Descripción:**
- Genera un PDF profesional con toda la información de la visita
- Incluye datos del cliente, técnico, descripción, reporte, fotos y firma
- Descarga directa como adjunto

**Response Headers:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="reporte_3847562.pdf"
```

---

## 🔐 Permisos y Autenticación

### **Sistema de Roles**

La autenticación se basa en el campo `tipo_usuario` de la tabla `Credenciales`:

| tipo_usuario | Rol | Acceso | Nombre |
|---|---|---|---|
| `0` | Técnico/Empleado Técnico | Visitas propias | Colaborador |
| `≥ 1` | Administrador | Todo (CRUD, reportes, PDF) | Admin |

### **Matriz de Permisos**

| Endpoint | Técnico | Admin |
|---|---|---|
| `GET /tecnicos/` | ❌ | ✅ |
| `GET /` (listar) | ✅ (sus visitas) | ✅ (todas) |
| `POST /` (crear) | ❌ | ✅ |
| `GET /{id}/` | ✅ (propia) | ✅ |
| `PATCH /{id}/` | ❌ | ✅ |
| `DELETE /{id}/` | ❌ | ✅ |
| `POST /{id}/iniciar/` | ✅ (propia) | ✅ |
| `POST /{id}/finalizar/` | ✅ (propia) | ✅ |
| `POST /{id}/fotos/` | ✅ (propia) | ✅ |
| `DELETE /{id}/fotos/{foto_id}/` | ✅ (propia) | ✅ |
| `GET /calendario/` | ✅ (suyas) | ✅ (todas) |
| `GET /{id}/pdf/` | ❌ | ✅ |

---

## 📈 Flujo de Negocio

### **Flujo Completo de una Visita Técnica**

```
1. CREAR VISITA (Admin)
   ├─ Se registra cliente
   ├─ Se crea VisitaTecnica con estado "pendiente"
   ├─ Se asigna técnico
   └─ Se genera número de tarea único (ej: 3847562)

2. TÉCNICO RECIBE NOTIFICACIÓN
   ├─ Aparece en su lista de visitas
   └─ Ve fecha, hora, cliente, dirección

3. TÉCNICO INICIA VISITA
   ├─ Hace POST a /visits/{id}/iniciar/
   ├─ Estado cambia a "en_proceso"
   ├─ Se auto-crea ReporteVisita
   └─ Se registra inicio_desplazamiento

4. TÉCNICO TRABAJA EN EL SITIO
   ├─ Realiza la intervención técnica
   ├─ Captura fotos: POST /visits/{id}/fotos/
   └─ Máximo 20 fotos

5. TÉCNICO FINALIZA Y ENVÍA REPORTE
   ├─ Hace POST a /visits/{id}/finalizar/
   ├─ Envía datos del reporte
   ├─ Firma con su dedo en tablet (firma_cliente)
   ├─ Estado cambia a "finalizada"
   └─ Se registra fecha_actualizacion

6. ADMIN REVISA Y GENERA PDF
   ├─ Accede a GET /visits/{id}/
   ├─ Revisa todos los datos y fotos
   └─ Descarga PDF: GET /visits/{id}/pdf/

7. VISITA ARCHIVADA
   └─ Disponible en reportes y histórico
```

---

## 🔌 Integración en la Aplicación

### **1. Registro en Django**

En `BACKEND/core/settings.py` (línea 73):
```python
INSTALLED_APPS = [
    ...
    'AppVisits',  # ← Aquí está registrada
    ...
]
```

### **2. Rutas de la API**

En `BACKEND/core/urls.py` (línea 31):
```python
urlpatterns = [
    ...
    path('visits/', include('AppVisits.urls')),  # ← Prefix de todas las rutas
    ...
]
```

Esto significa que todos los endpoints se acceden como:
```
http://localhost:8000/visits/
http://localhost:8000/visits/{id}/
http://localhost:8000/visits/{id}/iniciar/
etc.
```

### **3. Relaciones con Otros Módulos**

**AppVisits depende de:**
- `usuarios.Credenciales` - Para técnicos y administradores
  - Campo `tecnico` en VisitaTecnica → FK a Credenciales
  - Campo `creado_por` en VisitaTecnica → FK a Credenciales

**Módulos que PUEDEN usar AppVisits:**
- `frontend_U` (React) - Interfaz de técnicos en tablet/móvil
- `frontend_S` (React) - Interfaz de administradores

### **4. Base de Datos**

Tablas creadas:
```sql
visita_cliente          -- Información de clientes
visita_tecnica          -- Visitas programadas
visita_reporte          -- Reportes técnicos
visita_evidencia        -- Fotos de evidencia
```

**Migraciones:**
```
BACKEND/AppVisits/migrations/
├── 0001_initial.py      -- Creación inicial de modelos
└── 0002_*.py            -- Alteraciones posteriores
```

---

## 💻 Ejemplos de Uso

### **Ejemplo 1: Crear una Visita (desde Admin)**

```bash
curl -X POST http://localhost:8000/visits/ \
  -H "Authorization: Bearer {token_admin}" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_nombre": "Carlos López",
    "cliente_identificacion": "123456789",
    "cliente_telefono": "3104567890",
    "cliente_correo": "carlos@example.com",
    "cliente_direccion": "Calle 5 #12-34, Bogotá",
    "tipo_tarea": "reparacion",
    "fecha": "2026-08-15",
    "hora": "10:30:00",
    "descripcion": "Reparación de estufa",
    "observaciones_iniciales": "Problema con piloto",
    "tecnico_id": 5
  }'
```

**Respuesta:**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "estado": "pendiente",
  ...
}
```

---

### **Ejemplo 2: Técnico Inicia Visita**

```bash
curl -X POST http://localhost:8000/visits/1/iniciar/ \
  -H "Authorization: Bearer {token_tecnico}" \
  -H "Content-Type: application/json"
```

**Respuesta:**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "estado": "en_proceso",
  ...
}
```

---

### **Ejemplo 3: Técnico Sube Fotos**

```bash
curl -X POST http://localhost:8000/visits/1/fotos/ \
  -H "Authorization: Bearer {token_tecnico}" \
  -F "fotos=@foto1.jpg" \
  -F "fotos=@foto2.jpg"
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "imagen": "https://...",
    "orden": 0,
    "subida_en": "2026-08-15T10:30:00Z"
  },
  {
    "id": 2,
    "imagen": "https://...",
    "orden": 1,
    "subida_en": "2026-08-15T10:30:05Z"
  }
]
```

---

### **Ejemplo 4: Técnico Finaliza y Envía Reporte**

```bash
curl -X POST http://localhost:8000/visits/1/finalizar/ \
  -H "Authorization: Bearer {token_tecnico}" \
  -F "persona_atiende=Doña Rosa" \
  -F "equipo=estufa" \
  -F "ubicacion_equipo=cocina" \
  -F "motivo_servicio=Piloto no enciende" \
  -F "solucion_realizada=Se limpió la tobera y se ajustó el piloto" \
  -F "valor_servicio=150000" \
  -F "metodo_pago=efectivo" \
  -F "firma_cliente=@firma.png" \
  -F "duracion_desplazamiento=45 minutos"
```

**Respuesta:**
```json
{
  "id": 1,
  "numero_tarea": "3847562",
  "estado": "finalizada",
  "reporte": {
    "persona_atiende": "Doña Rosa",
    "equipo": "estufa",
    ...
  }
}
```

---

### **Ejemplo 5: Admin Descarga PDF**

```bash
curl -X GET http://localhost:8000/visits/1/pdf/ \
  -H "Authorization: Bearer {token_admin}" \
  -o reporte_3847562.pdf
```

---

### **Ejemplo 6: Listar Visitas del Técnico**

```bash
# Técnico solo ve sus visitas
curl -X GET http://localhost:8000/visits/ \
  -H "Authorization: Bearer {token_tecnico}"
```

**Respuesta:** (solo visitas asignadas a este técnico)

```bash
# Admin ve todas y puede filtrar
curl -X GET "http://localhost:8000/visits/?estado=pendiente&tecnico_id=5" \
  -H "Authorization: Bearer {token_admin}"
```

---

### **Ejemplo 7: Calendario de Visitas**

```bash
# Ver visitas de agosto 2026
curl -X GET "http://localhost:8000/visits/calendario/?mes=2026-08" \
  -H "Authorization: Bearer {token}"
```

**Respuesta:**
```json
{
  "2026-08-15": [
    {
      "id": 1,
      "numero_tarea": "3847562",
      "cliente_nombre": "Carlos López",
      "hora": "10:30:00",
      "estado": "en_proceso"
    }
  ],
  "2026-08-20": [
    ...
  ]
}
```

---

## 🚀 Checklist de Integración

Para integrar correctamente AppVisits en una aplicación:

- [x] **Backend (Django):** Registrado en `INSTALLED_APPS`
- [x] **Backend (Django):** Rutas incluidas en `core/urls.py`
- [x] **Base de Datos:** Migraciones ejecutadas
- [ ] **Frontend:** Crear pantalla para crear visitas (solo admin)
- [ ] **Frontend:** Crear pantalla de lista de visitas
- [ ] **Frontend:** Crear vista de detalle de visita
- [ ] **Frontend (Móvil):** Pantalla para técnico inicie visita
- [ ] **Frontend (Móvil):** Interfaz para capturar fotos
- [ ] **Frontend (Móvil):** Formulario para enviar reporte
- [ ] **Frontend (Móvil):** Pad de firma digital para cliente
- [ ] **Frontend (Admin):** Pantalla para descargar PDF
- [ ] **Frontend:** Implementar autenticación y autorización
- [ ] **API:** Configurar CORS si frontend está en servidor diferente
- [ ] **Servidor:** Configurar almacenamiento de imágenes (fotos y firmas)
- [ ] **Testing:** Pruebas de flujo completo

---

## 📝 Notas Técnicas Importantes

### **Firma del Cliente**
- Se acepta como archivo de imagen (PNG, JPG) o como base64
- Se procesa en `FinalizarVisitaView` (línea 230-245)
- Se almacena en `media/firmas/`

### **Generación de PDF**
- Usa librería **ReportLab** (reportlab)
- Se genera dinámicamente sin guardar en BD
- Incluye todas las fotos (máximo 20 en grid de 3 columnas)
- Usa plantilla con logo y formato profesional de IMPORGAS JJ

### **Fotos de Evidencia**
- Se almacenan en `media/evidencias/`
- Máximo 20 por visita (validado en `FotosView` línea 276)
- Se ordenan por `orden` y `subida_en`
- Se pueden eliminar individualmente

### **Número de Tarea**
- Se genera automáticamente en `save()` del modelo
- Formato: 7 dígitos aleatorios (1000000 a 9999999)
- Es único en toda la base de datos
- Se genera cada vez que se crea una visita

### **Permisos Granulares**
- Técnico solo ve sus visitas (filtro por `tecnico_id == request.user.id`)
- Técnico no puede ver visitas de otros técnicos
- Técnico no puede modificar visitas (solo crear reporte)
- Admin acceso total a todo

---

## 🐛 Troubleshooting

### **"useFavorites must be used within a FavoritesProvider"**
→ Ver si tienes el mismo problema de context providers en frontend

### **"Visita no encontrada"**
→ Verifica que el ID es válido y que tienes permisos

### **"No autorizado" (403)**
→ Verifica que eres técnico de esa visita o admin

### **Fotos no se suben**
→ Verifica que no excedas 20 fotos
→ Verifica que tienes permiso de escritura en `media/evidencias/`

### **PDF no genera**
→ Verifica que la visita tiene reporte
→ Verifica que tienes ReportLab instalado: `pip install reportlab`

---

## 📞 Contacto y Soporte

Para dudas o mejoras en AppVisits, revisar:
- Modelos: `BACKEND/AppVisits/models.py`
- Endpoints: `BACKEND/AppVisits/views.py`
- Serialización: `BACKEND/AppVisits/serializers.py`
- Permisos: `BACKEND/AppVisits/permissions.py`

---

**Última actualización:** 2026-08-05
**Versión:** 1.0.0
