# 📊 DIAGRAMA VISUAL DEL FLUJO COMPLETO

## FLUJO DE DATOS: CSV → CORREOS → TRAZABILIDAD

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ENTRADA: CSV EN ENDPOINT POST /examenes/correo/enviar-masivo/            │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ Empresa │ Unidad │ Proyecto │ Centro │ ... │ TipoExamen │ Examenes │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ Regency │ Ops    │ Regional │ Bog    │ ... │ INGRESO    │ Radio,… │    │
│  │ Regency │ Ops    │ Regional │ Bog    │ ... │ ESPECIAL   │ Cardio… │    │
│  │ Regency │ Ops    │ Regional │ Bog    │ ... │ POST_INCAP │ Radio,… │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  VALIDACIÓN (SIN validar ExamenesCargo)                                    │
│                                                                             │
│  ✓ Empresa existe        ✓ Tipo en choices (INGRESO, ESPECIAL, etc)      │
│  ✓ Cargo existe          ✓ Cada examen existe en tabla Examen             │
│  ✓ Centro existe         ✗ NO validar combo en ExamenesCargo              │
│                                                                             │
│  RESULTADO: 3 trabajadores válidos                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CREAR REGISTROS EN BASE DE DATOS                        │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. CorreoExamenEnviado (1 registro)                                │  │
│  │    ├─ uuid_correo: a3f7d2b5-20260105130045                        │  │
│  │    ├─ tipo_examen: MIXTO (hay múltiples tipos)                    │  │
│  │    └─ fecha_envio: 2026-01-05 13:00:45                            │  │
│  │    → DB: INSERT INTO correoexamenenviado VALUES (...)             │  │
│  │    → PK: id=1                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 2. RegistroExamenes (3 registros - 1 POR TRABAJADOR)              │  │
│  │                                                                    │  │
│  │    JUAN PÉREZ (INGRESO)                                          │  │
│  │    ├─ uuid_trabajador: f8e2c1a9-4d7f-11eb-ae93...               │  │
│  │    ├─ correo_lote_id: 1                                          │  │
│  │    ├─ tipo_examen: INGRESO                                       │  │
│  │    └─ examenes_asignados: NULL (no se usa)                       │  │
│  │    → DB: INSERT INTO registroexamenes VALUES (...)               │  │
│  │    → PK: id=1                                                     │  │
│  │                                                                    │  │
│  │    MARÍA LÓPEZ (ESPECIAL)                                        │  │
│  │    ├─ uuid_trabajador: g9f3d2b0-5e8g-12fc-bf94...               │  │
│  │    ├─ correo_lote_id: 1                                          │  │
│  │    ├─ tipo_examen: ESPECIAL      ← NUEVO TIPO                    │  │
│  │    └─ examenes_asignados: NULL                                   │  │
│  │    → DB: INSERT INTO registroexamenes VALUES (...)               │  │
│  │    → PK: id=2                                                     │  │
│  │                                                                    │  │
│  │    CARLOS RUIZ (POST_INCAPACIDAD)                                │  │
│  │    ├─ uuid_trabajador: h0g4e3c1-6f9h-13gd-cg05...               │  │
│  │    ├─ correo_lote_id: 1                                          │  │
│  │    ├─ tipo_examen: POST_INCAPACIDAD ← NUEVO TIPO                │  │
│  │    └─ examenes_asignados: NULL                                   │  │
│  │    → DB: INSERT INTO registroexamenes VALUES (...)               │  │
│  │    → PK: id=3                                                     │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 3. RegistroExamenesEnviados (6 registros - M:N EXAMEN:TRABAJADOR) │  │
│  │    ↑ ESTA ES LA TABLA NUEVA Y CRUCIAL                            │  │
│  │                                                                    │  │
│  │    JUAN PÉREZ - Radiografía                                      │  │
│  │    ├─ registro_examen_id: 1 (FK)                                 │  │
│  │    ├─ examen_id: 1 (Radiografía) (FK)                            │  │
│  │    ├─ tipo_examen: INGRESO                                       │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → DB: INSERT INTO registroexamenesenviados VALUES (...)       │  │
│  │    → PK: id=1                                                     │  │
│  │                                                                    │  │
│  │    JUAN PÉREZ - Análisis de Sangre                               │  │
│  │    ├─ registro_examen_id: 1 (FK)                                 │  │
│  │    ├─ examen_id: 2 (Análisis Sangre) (FK)                        │  │
│  │    ├─ tipo_examen: INGRESO                                       │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → PK: id=2                                                     │  │
│  │                                                                    │  │
│  │    MARÍA LÓPEZ - Cardiología                                     │  │
│  │    ├─ registro_examen_id: 2 (FK)                                 │  │
│  │    ├─ examen_id: 5 (Cardiología) (FK)                            │  │
│  │    ├─ tipo_examen: ESPECIAL     ← NUEVO                          │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → PK: id=3                                                     │  │
│  │                                                                    │  │
│  │    MARÍA LÓPEZ - Psicología                                      │  │
│  │    ├─ registro_examen_id: 2 (FK)                                 │  │
│  │    ├─ examen_id: 6 (Psicología) (FK)                             │  │
│  │    ├─ tipo_examen: ESPECIAL                                      │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → PK: id=4                                                     │  │
│  │                                                                    │  │
│  │    CARLOS RUIZ - Radiografía                                     │  │
│  │    ├─ registro_examen_id: 3 (FK)                                 │  │
│  │    ├─ examen_id: 1 (Radiografía) (FK) ← REUTILIZADA              │  │
│  │    ├─ tipo_examen: POST_INCAPACIDAD                              │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → PK: id=5                                                     │  │
│  │                                                                    │  │
│  │    CARLOS RUIZ - EKG                                             │  │
│  │    ├─ registro_examen_id: 3 (FK)                                 │  │
│  │    ├─ examen_id: 7 (EKG) (FK)                                    │  │
│  │    ├─ tipo_examen: POST_INCAPACIDAD                              │  │
│  │    ├─ estado: pendiente                                          │  │
│  │    └─ resultado: NULL                                            │  │
│  │    → PK: id=6                                                     │  │
│  │                                                                    │  │
│  │    ✓ TRAZABILIDAD COMPLETA: QUÉ EXAMEN A QUIÉN Y CUÁNDO        │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENVIAR CORREOS A LOS 3                              │
│                                                                             │
│  EMAIL 1: juan.perez@company.com                                          │
│  ├─ Asunto: "Convocatoria a exámenes médicos"                            │
│  ├─ Tipo: INGRESO                                                         │
│  └─ Exámenes: Radiografía, Análisis de Sangre                            │
│                                                                             │
│  EMAIL 2: maria.lopez@company.com                                         │
│  ├─ Asunto: "Convocatoria a exámenes médicos"                            │
│  ├─ Tipo: ESPECIAL     ← Nuevo tipo en el email                           │
│  └─ Exámenes: Cardiología, Psicología                                     │
│                                                                             │
│  EMAIL 3: carlos.ruiz@company.com                                         │
│  ├─ Asunto: "Convocatoria a exámenes médicos"                            │
│  ├─ Tipo: POST_INCAPACIDAD ← Nuevo tipo en el email                       │
│  └─ Exámenes: Radiografía, EKG                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TRABAJADOR COMPLETA EXAMEN (FUTURO)                   │
│                                                                             │
│  JUAN accede a portal con su UUID: f8e2c1a9-4d7f-11eb-ae93-0242ac120002  │
│  Completa: Radiografía → Resultado: APROBADO                             │
│                                                                             │
│  REQUEST: PUT /examenes/trabajador/f8e2c1a9-4d7f-11eb-ae93.../          │
│           examen-completado/                                              │
│  BODY: { "examen_id": 1, "resultado": "aprobado" }                       │
│                                                                             │
│  ACTUALIZACIÓN:                                                            │
│  RegistroExamenesEnviados.objects.filter(                                │
│      registro_examen_id=1,    # Juan                                      │
│      examen_id=1              # Radiografía                               │
│  ).update(                                                                 │
│      estado='completado',     # ← Cambio                                  │
│      resultado='aprobado',    # ← Cambio                                  │
│      fecha_completado=NOW()   # ← Cambio                                  │
│  )                                                                          │
│                                                                             │
│  ESTADO EN DB - RegistroExamenesEnviados (id=1):                          │
│  ├─ estado: 'pendiente' → 'completado'                                    │
│  ├─ resultado: NULL → 'aprobado'                                          │
│  └─ fecha_completado: NULL → 2026-01-05 14:30:00                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REPORTES Y CONSULTAS FÁCILES                       │
│                                                                             │
│  1. ¿Qué exámenes tiene María López pendientes?                           │
│     SELECT * FROM registroexamenesenviados                                │
│     WHERE registro_examen_id=2 AND estado='pendiente'                     │
│     → Resultado: Cardiología (ESPECIAL), Psicología (ESPECIAL)           │
│                                                                             │
│  2. ¿Cuántos exámenes ESPECIAL se han completado?                        │
│     SELECT COUNT(*) FROM registroexamenesenviados                         │
│     WHERE tipo_examen='ESPECIAL' AND estado='completado'                  │
│     → Resultado: 0 (María aún no completa)                               │
│                                                                             │
│  3. ¿Cuándo se envió el examen a Juan y cuándo lo completó?              │
│     SELECT fecha_envio, fecha_completado FROM registroexamenesenviados   │
│     WHERE registro_examen_id=1 AND examen_id=1                           │
│     → Resultado: Enviado: 2026-01-05 13:00:45, Completado: 14:30:00    │
│                                                                             │
│  4. ¿Auditoría: quién completó qué, cuándo, con qué resultado?           │
│     SELECT r.nombre_trabajador, e.nombre, ree.resultado,                 │
│            ree.fecha_completado                                           │
│     FROM registroexamenesenviados ree                                     │
│     JOIN registroexamenes r ON ree.registro_examen_id = r.id             │
│     JOIN examenes e ON ree.examen_id = e.id                              │
│     → Trazabilidad COMPLETA                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ ESQUEMA DE TABLAS EN BASE DE DATOS

```sql
-- TABLA 1: CorreoExamenEnviado (EXISTENTE - SIN CAMBIOS ESTRUCTURA)
CREATE TABLE correoexamenenviado (
    id INT PRIMARY KEY AUTO_INCREMENT,
    uuid_correo VARCHAR(255) UNIQUE,
    enviado_por_id INT,
    asunto VARCHAR(200),
    cuerpo_correo LONGTEXT,
    correos_destino VARCHAR(500),
    tipo_examen VARCHAR(20),  -- INGRESO, PERIODICO, RETIRO, ESPECIAL, POST_INCAPACIDAD, MIXTO
    enviado_correctamente BOOLEAN DEFAULT FALSE,
    error_envio TEXT,
    fecha_envio DATETIME AUTO_TIMESTAMP,
    FOREIGN KEY (enviado_por_id) REFERENCES colaboradores(idcolaborador)
);

-- TABLA 2: RegistroExamenes (EXISTENTE - SOLO ACTUALIZAR CHOICES)
CREATE TABLE registroexamenes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    uuid_trabajador VARCHAR(255) UNIQUE,
    correo_lote_id INT,
    nombre_trabajador VARCHAR(150),
    documento_trabajador VARCHAR(50),
    empresa_id INT,
    cargo_id INT,
    centro_id INT,
    tipo_examen VARCHAR(20),  -- INGRESO, PERIODICO, RETIRO, ESPECIAL, POST_INCAPACIDAD
    examenes_asignados TEXT,  -- Puede ser NULL
    estado_trabajador INT DEFAULT 0,  -- 0=Pendiente, 1=Completado
    fecha_registro DATETIME AUTO_TIMESTAMP,
    FOREIGN KEY (correo_lote_id) REFERENCES correoexamenenviado(id),
    FOREIGN KEY (empresa_id) REFERENCES epresa(idempresa),
    FOREIGN KEY (cargo_id) REFERENCES cargo(idcargo),
    FOREIGN KEY (centro_id) REFERENCES centroop(id_centro),
    UNIQUE (correo_lote_id, documento_trabajador)
);

-- TABLA 3: RegistroExamenesEnviados (NUEVA - LA CLAVE)
CREATE TABLE registroexamenesenviados (
    id INT PRIMARY KEY AUTO_INCREMENT,
    registro_examen_id INT NOT NULL,
    examen_id INT NOT NULL,
    tipo_examen VARCHAR(20),
    estado VARCHAR(20) DEFAULT 'pendiente',  -- pendiente, completado, no_realizado
    resultado VARCHAR(50),  -- aprobado, no_aprobado, NULL
    fecha_envio DATETIME AUTO_TIMESTAMP,
    fecha_completado DATETIME NULL,
    FOREIGN KEY (registro_examen_id) REFERENCES registroexamenes(id) ON DELETE CASCADE,
    FOREIGN KEY (examen_id) REFERENCES examenes(id) ON DELETE PROTECT,
    UNIQUE (registro_examen_id, examen_id, tipo_examen)
);

-- TABLA 4: ExamenesCargo (EXISTENTE - NO CAMBIOS FUNCIONALES, SOLO CHOICES)
-- Solo se actualiza el campo tipo para agregar nuevas opciones
-- Pero ya NO se usa para validar en enviar-masivo
ALTER TABLE examenes_examenescargo 
MODIFY tipo VARCHAR(20) DEFAULT 'INGRESO';
-- tipo puede ser: INGRESO, PERIODICO, RETIRO, ESPECIAL (opcional), POST_INCAPACIDAD (opcional)
```

---

## 🔗 RELACIONES DE CLAVES FORÁNEAS

```
                          Colaboradores
                                │
                                │ (enviado_por)
                                ↓
            ┌────────────────────────────────────────────┐
            │    CorreoExamenEnviado (Lote)              │
            │    - 1 lote contiene N trabajadores        │
            │    - Representa UN envío masivo            │
            └────────────────────────────────────────────┘
                                │
                                │ (correo_lote)
                                ↓
            ┌────────────────────────────────────────────┐
            │    RegistroExamenes (Trabajador)           │
            │    - 1 trabajador puede tener N exámenes  │
            │    - Cada trabajador tiene tipo_examen     │
            └────────────────────────────────────────────┘
                                │
                                │ (registro_examen)
                                ↓
            ┌────────────────────────────────────────────┐
            │ RegistroExamenesEnviados (Intermediaria)   │
            │ - Registro REAL de cada examen enviado     │
            │ - Contiene: examen, tipo, estado, resultado│
            │ - ← LA TABLA CLAVE                         │
            └────────────────────────────────────────────┘
                                │
                                │ (examen)
                                ↓
                            Examen
                        (Radiografía, etc)

TAMBIÉN ENLAZA A:
- Epresa (empresa)
- Cargo (cargo)
- Centroop (centro)
```

---

## 💡 COMPARACIÓN DE CONSULTAS: ANTES vs DESPUÉS

### CONSULTA 1: ¿Qué exámenes se enviaron a María López?

**ANTES (CSV text):**
```python
registro = RegistroExamenes.objects.get(documento_trabajador='87654321')
examenes_str = registro.examenes_asignados  # "Cardiología, Psicología"
examenes_lista = examenes_str.split(',')    # ['Cardiología', ' Psicología']
# Necesito parsear manualmente, sin FK
```

**DESPUÉS (FK directo):**
```python
examenes_enviados = RegistroExamenesEnviados.objects.filter(
    registro_examen__documento_trabajador='87654321'
).select_related('examen')
for env in examenes_enviados:
    print(f"{env.examen.nombre}: {env.estado}")
# OUTPUT:
# Cardiología: pendiente
# Psicología: pendiente
```

### CONSULTA 2: ¿Cuándo se completó el examen de María?

**ANTES (no hay info):**
```python
# No hay columna de fecha_completado en RegistroExamenes
# No se puede saber CUÁNDO se completó
```

**DESPUÉS (trazabilidad completa):**
```python
env = RegistroExamenesEnviados.objects.get(
    registro_examen__documento_trabajador='87654321',
    examen__nombre='Cardiología'
)
print(f"Enviado: {env.fecha_envio}")
print(f"Completado: {env.fecha_completado}")
print(f"Resultado: {env.resultado}")
# OUTPUT:
# Enviado: 2026-01-05 13:00:45
# Completado: None (aún pendiente)
# Resultado: None
```

### CONSULTA 3: Reporte de exámenes ESPECIAL completados

**ANTES (no hay tipo en ExamenTrabajador):**
```python
# Difícil: no hay forma de saber qué tipo de examen es
# Solo en RegistroExamenes.tipo_examen (nivel trabajador, no examen)
```

**DESPUÉS (tipo por examen):**
```python
especiales_completados = RegistroExamenesEnviados.objects.filter(
    tipo_examen='ESPECIAL',
    estado='completado'
).select_related('registro_examen', 'examen')

for env in especiales_completados:
    print(f"{env.registro_examen.nombre_trabajador}: {env.examen.nombre} - {env.resultado}")
# OUTPUT:
# María López: Cardiología - aprobado
# José García: Oftalmología - no_aprobado
```

