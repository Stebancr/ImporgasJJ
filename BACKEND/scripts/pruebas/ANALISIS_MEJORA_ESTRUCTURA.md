# 📊 ANÁLISIS DE MEJORA DE ESTRUCTURA - Tipos de Examen Flexible

## 🔴 PROBLEMA ACTUAL

### Estructura Existente:
```
Examen (tabla)
├── id_examen
├── nombre
└── activo

ExamenesCargo (tabla) - VALIDACIÓN RÍGIDA
├── empresa_id ──→ Epresa
├── cargo_id ──→ Cargo
├── examen_id ──→ Examen
├── tipo (INGRESO, PERIODICO, RETIRO)
└── fecha_creacion

CorreoExamenEnviado (tabla)
├── uuid_correo
├── enviado_por ──→ Colaboradores
├── tipo_examen (INGRESO, PERIODICO, RETIRO)
└── ...

RegistroExamenes (tabla) - POR TRABAJADOR
├── uuid_trabajador
├── correo_lote ──→ CorreoExamenEnviado
├── nombre_trabajador
├── documento_trabajador
├── empresa_id ──→ Epresa
├── cargo_id ──→ Cargo
├── centro_id ──→ Centroop
├── tipo_examen (INGRESO, PERIODICO, RETIRO)
├── examenes_asignados (TEXT: CSV de nombres)
└── estado_trabajador

ExamenTrabajador (tabla M:N)
├── registro_examen_id ──→ RegistroExamenes
├── examen_id ──→ Examen
└── fecha_asignacion
```

### Problemas:
1. ✗ Validación rígida contra `ExamenesCargo` impide tipos flexibles (ESPECIAL, POST_INCAPACIDAD)
2. ✗ No hay trazabilidad de QUÉ EXÁMENES se enviaron por correo
3. ✗ `examenes_asignados` es TEXT/CSV, sin FK directa a Examen
4. ✗ `ExamenTrabajador` es M:N pero no se usa en el flujo actual (datos en CSV)
5. ✗ Para ESPECIAL/POST_INCAPACIDAD, el usuario puede enviar CUALQUIER examen sin restricción

---

## 🟢 SOLUCIÓN PROPUESTA

### Nueva Estructura Mejorada:

```
1. TABLA: ExamenesCargo (SIN CAMBIOS)
   ├── Propósito: SOLO VISUALIZACIÓN/PREVIEW en endpoints
   ├── empresa_id, cargo_id, examen_id, tipo
   └── Se usa para mostrar "exámenes sugeridos" pero NO para validar envío

2. TABLA NUEVA: RegistroExamenesEnviados (INTERMEDIARIA - KEY)
   ├── Propósito: Registrar QUÉ EXÁMENES se enviaron POR CORREO
   ├── id (PK)
   ├── registro_examen_id (FK) ──→ RegistroExamenes
   ├── examen_id (FK) ──→ Examen
   ├── tipo_examen (INGRESO, PERIODICO, RETIRO, ESPECIAL, POST_INCAPACIDAD)
   ├── fecha_envio
   ├── estado (pendiente, completado, no_realizado)
   └── resultado (aprobado, no_aprobado, null)
   
   CONSTRAINT: unique_together = (registro_examen, examen, tipo_examen)

3. TABLA: RegistroExamenes (ACTUALIZADA)
   ├── Propósito: Registro GENERAL del trabajador
   ├── uuid_trabajador, correo_lote, nombre, documento, empresa, cargo, centro
   ├── tipo_examen (el TIPO de correo que se envió - puede ser MIXTO si varios tipos)
   ├── examenes_asignados (TEXTO: se mantiene para compatibilidad, puede ser NULL)
   ├── examenes_realizados (JSON: {id_examen: {completado, resultado, fecha}})
   └── estado_trabajador
   
   ✓ Los exámenes REALES asignados están en RegistroExamenesEnviados
   ✓ Trazabilidad completa: quién, cuándo, qué, resultado

4. TABLA: ExamenTrabajador (SE PUEDE DEPRECAR O DEJAR)
   └── Reemplazada por RegistroExamenesEnviados (más detallada)
```

---

## 🔄 FLUJO DE PROCESAMIENTO CON NUEVA ESTRUCTURA

### FASE 1: CSV INGRESO (correo/enviar-masivo/)

```
CSV INPUT:
┌─────────┬────────┬──────┬────────┬────────────┬──────────────────────┐
│ Empresa │ Unidad │ Proy │ Centro │ TipoExamen │ Examenes             │
├─────────┼────────┼──────┼────────┼────────────┼──────────────────────┤
│ Regency │ Ops    │ Reg  │ Bog    │ INGRESO    │ Radiografía, Sangre  │
│ Regency │ Ops    │ Reg  │ Bog    │ ESPECIAL   │ Cardiología, Psico   │
│ Regency │ Ops    │ Reg  │ Bog    │ POST_INCAP │ Radiografía, EKG     │
└─────────┴────────┴──────┴────────┴────────────┴──────────────────────┘

VALIDACIÓN (SIN COMPARAR ExamenesCargo):
┌──────────────────────────────────────────────────────────────┐
│ 1. Validar que empresa, unidad, proyecto, centro existan     │
│ 2. Validar que cargo exista                                  │
│ 3. Validar que cada examen en columna "Examenes" existe      │
│    (sin importar ExamenesCargo)                              │
│ 4. Validar tipo_examen ∈ {INGRESO, PERIODICO, RETIRO,       │
│    ESPECIAL, POST_INCAPACIDAD}                               │
│ 5. ✓ SI ESPECIAL/POST_INCAPACIDAD: acepta CUALQUIER examen  │
│ 6. ✓ SI INGRESO/PERIODICO/RETIRO: OPCIONAL validar contra   │
│    ExamenesCargo (pero NO es obligatorio)                    │
└──────────────────────────────────────────────────────────────┘
```

### FASE 2: GUARDAR REGISTROS

```
Para CADA trabajador en CSV:
│
├─ Crear RegistroExamenes
│  ├── uuid_trabajador (UUID)
│  ├── correo_lote_id (FK a CorreoExamenEnviado)
│  ├── nombre_trabajador
│  ├── documento_trabajador
│  ├── empresa, cargo, centro
│  ├── tipo_examen (del CSV: INGRESO, ESPECIAL, etc.)
│  └── examenes_asignados = NULL (opcional, para compatibilidad)
│
└─ Para CADA examen en columna "Examenes":
   │
   └─ Crear RegistroExamenesEnviados
      ├── registro_examen_id (FK recién creada)
      ├── examen_id (FK a Examen)
      ├── tipo_examen (COPIA del RegistroExamenes.tipo_examen)
      ├── fecha_envio = NOW()
      ├── estado = 'pendiente'
      └── resultado = NULL
```

### FASE 3: TRACKING Y ACTUALIZACIÓN

```
Cuando trabajador completa examen:

PUT /examenes/trabajador/<uuid>/examen-completado/
{
    "examen_id": 1,
    "resultado": "APROBADO"
}

ACTUALIZAR:
├─ RegistroExamenesEnviados
│  ├── estado = 'completado'
│  ├── resultado = 'APROBADO'
│  └── fecha_completado = NOW()
│
└─ RegistroExamenes (ACTUALIZAR ESTADO GENERAL)
   ├── examenes_realizados JSON:
   │   {
   │     "1": {"completado": true, "resultado": "APROBADO", "fecha": "2026-01-05T10:30:00"},
   │     "2": {"completado": false, "resultado": null, "fecha": null}
   │   }
   └── estado_trabajador = 1 (si TODOS están completados)
```

---

## 📋 COMPARACIÓN: ANTES vs DESPUÉS

### ANTES (Actual):
```
CSV: INGRESO, RADIOGRAFÍA, SANGRE
    ↓ Valida contra ExamenesCargo
    ↓ ¿Existe INGRESO+RADIOGRAFÍA en config? SÍ
    ↓ ¿Existe INGRESO+SANGRE? SÍ
    ↓ OK → Guardar
    
CSV: ESPECIAL, CARDIOLOGÍA, PSICO
    ↓ Valida contra ExamenesCargo
    ↓ ¿Existe ESPECIAL+CARDIOLOGÍA? NO (tipo no existe en DB)
    ✗ RECHAZAR
```

### DESPUÉS (Propuesto):
```
CSV: INGRESO, RADIOGRAFÍA, SANGRE
    ↓ Valida que Radiografía y Sangre existan en tabla Examen
    ↓ Valida que INGRESO sea tipo válido
    ✓ OK → Guardar en RegistroExamenes + RegistroExamenesEnviados

CSV: ESPECIAL, CARDIOLOGÍA, PSICO
    ↓ Valida que Cardiología y Psico existan en tabla Examen
    ↓ Valida que ESPECIAL sea tipo válido (NUEVO)
    ✓ OK → Guardar en RegistroExamenes + RegistroExamenesEnviados
    
CSV: POST_INCAPACIDAD, RADIOGRAFÍA, EKG
    ↓ Valida que Radiografía y EKG existan en tabla Examen
    ↓ Valida que POST_INCAPACIDAD sea tipo válido (NUEVO)
    ✓ OK → Guardar en RegistroExamenes + RegistroExamenesEnviados

SIN RESTRICCIONES: Cualquier combinación tipo+examen es válida
```

---

## 🎯 VENTAJAS DE LA NUEVA ESTRUCTURA

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Flexibilidad de tipos** | Solo INGRESO, PERIODICO, RETIRO | INGRESO, PERIODICO, RETIRO, ESPECIAL, POST_INCAPACIDAD + futuros |
| **Restricción de exámenes** | Rígida: valida contra ExamenesCargo | Flexible: solo validar existencia en tabla Examen |
| **Trazabilidad** | CSV text, sin FK | FK directa a Examen en RegistroExamenesEnviados |
| **Quién envió qué** | Implícito en RegistroExamenes | Explícito en RegistroExamenesEnviados |
| **Tracking resultados** | examenes_asignados (TEXT) | RegistroExamenesEnviados.resultado |
| **Reportes** | Difícil agrupar por examen | Fácil: JOIN RegistroExamenesEnviados |
| **Auditoría** | Limitada | Completa: fechas, estados, resultados |

---

## 🛠️ CAMBIOS TÉCNICOS REQUERIDOS

### 1. CREAR NUEVA TABLA: `RegistroExamenesEnviados`

```python
class RegistroExamenesEnviados(models.Model):
    """
    Tabla intermediaria que registra cada EXAMEN enviado a un trabajador.
    Proporciona trazabilidad completa: qué examen, cuándo, resultado.
    """
    registro_examen = models.ForeignKey(
        RegistroExamenes,
        on_delete=models.CASCADE,
        related_name='examenes_enviados'
    )
    examen = models.ForeignKey(
        Examen,
        on_delete=models.PROTECT,
        related_name='registros_enviados'
    )
    tipo_examen = models.CharField(
        max_length=20,
        choices=[
            ("INGRESO", "Examen de Ingreso"),
            ("PERIODICO", "Examen Periódico"),
            ("RETIRO", "Examen de Retiro"),
            ("ESPECIAL", "Examen Especial"),
            ("POST_INCAPACIDAD", "Examen Post-Incapacidad")
        ]
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("completado", "Completado"),
            ("no_realizado", "No Realizado")
        ],
        default="pendiente"
    )
    resultado = models.CharField(
        max_length=50,
        choices=[
            ("aprobado", "Aprobado"),
            ("no_aprobado", "No Aprobado"),
            ("incompleto", "Incompleto"),
            ("", "Sin resultado")
        ],
        blank=True,
        null=True
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('registro_examen', 'examen', 'tipo_examen')
        verbose_name = 'Registro de Examen Enviado'
        verbose_name_plural = 'Registros de Exámenes Enviados'
```

### 2. ACTUALIZAR `RegistroExamenes`

```python
# Agregar opciones nuevas a tipo_examen
tipo_examen = models.CharField(
    max_length=20,
    choices=[
        ("INGRESO", "Examen de Ingreso"),
        ("PERIODICO", "Examen Periódico"),
        ("RETIRO", "Examen de Retiro"),
        ("ESPECIAL", "Examen Especial"),
        ("POST_INCAPACIDAD", "Examen Post-Incapacidad"),
        ("MIXTO", "Múltiples tipos")  # Opcional
    ]
)

# Agregar campo para trazabilidad
examenes_realizados = models.JSONField(
    default=dict,
    blank=True,
    null=True,
    help_text="Trazabilidad: {id_examen: {completado, resultado, fecha}}"
)
```

### 3. ACTUALIZAR `CorreoExamenEnviado`

```python
# Agregar nuevos tipos
tipo_examen = models.CharField(
    max_length=20,
    choices=[
        ("INGRESO", "Examen de Ingreso"),
        ("PERIODICO", "Examen Periódico"),
        ("RETIRO", "Examen de Retiro"),
        ("ESPECIAL", "Examen Especial"),
        ("POST_INCAPACIDAD", "Examen Post-Incapacidad"),
        ("MIXTO", "Múltiples tipos")
    ]
)
```

### 4. ACTUALIZAR `EnviarCorreoMasivoView`

```python
# CAMBIOS EN VALIDACIÓN:

CAMBIO 1: Aceptar nuevos tipos
✗ if tipo_examen not in ['INGRESO', 'PERIODICO']:
✓ if tipo_examen not in ['INGRESO', 'PERIODICO', 'RETIRO', 'ESPECIAL', 'POST_INCAPACIDAD']:

CAMBIO 2: Validación de exámenes SIN restricción de ExamenesCargo
✗ examenes_cargo = ExamenesCargo.objects.filter(
    empresa=empresa,
    cargo=cargo,
    tipo=tipo_examen  # ← Esto restriccionaba
)
✓ # Para ESPECIAL y POST_INCAPACIDAD: 
  # - Solo validar que el examen exista en tabla Examen
  # - NO validar contra ExamenesCargo
  # Para INGRESO/PERIODICO/RETIRO:
  # - OPCIONAL: validar contra ExamenesCargo (pero NO obligatorio)

CAMBIO 3: Guardar en nueva tabla intermediaria
✗ examenes_asignados = "Radiografía, Sangre"
✓ Para cada examen:
   RegistroExamenesEnviados.objects.create(
       registro_examen=registro,
       examen=examen_obj,
       tipo_examen=tipo_examen,
       estado='pendiente'
   )
```

### 5. NUEVOS ENDPOINTS

```python
# 1. Actualizar resultado de examen
PUT /examenes/trabajador/<uuid>/examen-completado/
{
    "examen_id": 1,
    "resultado": "APROBADO"
}
→ Actualiza RegistroExamenesEnviados + RegistroExamenes.examenes_realizados

# 2. Listar exámenes enviados a un trabajador
GET /examenes/trabajador/<uuid>/examenes-enviados/
→ Retorna lista de RegistroExamenesEnviados con detalles

# 3. Reportes por tipo de examen
GET /examenes/reportes/por-tipo/?tipo=ESPECIAL&fecha_inicio=2026-01-01
→ Agregar datos de RegistroExamenesEnviados
```

---

## 📊 EJEMPLOS DE CONSULTAS MEJORADAS

### Antes:
```python
# Difícil: QUÉ exámenes se enviaron a un trabajador
trabajador = RegistroExamenes.objects.get(uuid=uuid)
examenes_str = trabajador.examenes_asignados  # "Radiografía, Sangre"
# Necesito parsear string manualmente
```

### Después:
```python
# Fácil: QUÉ exámenes se enviaron a un trabajador
examenes_enviados = RegistroExamenesEnviados.objects.filter(
    registro_examen__uuid_trabajador=uuid
).select_related('examen')

for env in examenes_enviados:
    print(f"{env.examen.nombre}: {env.estado} - {env.resultado}")
# OUTPUT:
# Radiografía: pendiente - None
# Sangre: completado - aprobado
```

---

## 🎓 CONCLUSIÓN

**Problema:** ExamenesCargo restriccionaba tipos flexibles

**Solución:** 
1. ExamenesCargo → solo previsualizacion/recomendación
2. Nueva tabla RegistroExamenesEnviados → registro real de envío
3. Validación flexible → solo existencia en tabla Examen, no en ExamenesCargo
4. Trazabilidad completa → quién, cuándo, qué, resultado

**Resultado:** Sistema flexible, escalable, auditable

