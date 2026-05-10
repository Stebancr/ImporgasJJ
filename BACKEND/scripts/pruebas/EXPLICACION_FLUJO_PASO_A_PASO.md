# 🔄 EXPLICACIÓN DETALLADA: FLUJO PASO A PASO CON EJEMPLO REAL

## 📥 ENTRADA: CSV ENVIADO EN correo/enviar-masivo/

Usuario sube un CSV así:

```
Empresa,Unidad,Proyecto,Centro,Nombre,CC,Ciudad,Cargo,TipoExamen,Examenes
Regency,Operaciones,Regional,Bogotá,Juan Pérez,12345678,BOG,Ingeniero,INGRESO,"Radiografía, Análisis de Sangre"
Regency,Operaciones,Regional,Bogotá,María López,87654321,BOG,Ingeniero,ESPECIAL,"Cardiología, Psicología"
Regency,Operaciones,Regional,Bogotá,Carlos Ruiz,11111111,BOG,Gerente,POST_INCAPACIDAD,"Radiografía, EKG"
```

---

## ✅ PASO 1: VALIDACIÓN (SIN RESTRICCIÓN DE ExamenesCargo)

### 1.1 Para CADA FILA del CSV:

```
FILA 1: Juan Pérez, INGRESO, "Radiografía, Análisis de Sangre"

Validaciones realizadas:
├─ ✓ ¿Empresa "Regency" existe? → SÍ (id=6)
├─ ✓ ¿Unidad "Operaciones" existe? → SÍ (id=15)
├─ ✓ ¿Proyecto "Regional" existe? → SÍ (id=42)
├─ ✓ ¿Centro "Bogotá" existe? → SÍ (id=101)
├─ ✓ ¿Cargo "Ingeniero" existe? → SÍ (id=3)
├─ ✓ ¿Tipo "INGRESO" es válido? → SÍ (en choices)
├─ ✓ ¿Examen "Radiografía" existe y está activo? → SÍ (id=1)
└─ ✓ ¿Examen "Análisis de Sangre" existe y está activo? → SÍ (id=2)

✓✓✓ FILA VÁLIDA → Guardar

---

FILA 2: María López, ESPECIAL, "Cardiología, Psicología"

Validaciones realizadas:
├─ ✓ ¿Empresa "Regency" existe? → SÍ (id=6)
├─ ... (empresas, unidades, proyectos igual) ...
├─ ✓ ¿Cargo "Ingeniero" existe? → SÍ (id=3)
├─ ✓ ¿Tipo "ESPECIAL" es válido? → SÍ (en choices - NUEVO TIPO)
├─ ✓ ¿Examen "Cardiología" existe y está activo? → SÍ (id=5)
└─ ✓ ¿Examen "Psicología" existe y está activo? → SÍ (id=6)

✓✓✓ FILA VÁLIDA → Guardar

⚠️ DIFERENCIA CON ANTES:
   Antes: ✗ Validaba contra ExamenesCargo
          Si ESPECIAL+Cardiología no existe en config → RECHAZAR
   Ahora: ✓ Solo valida existencia en tabla Examen
          ESPECIAL+Cardiología → ACEPTAR aunque no esté en config
```

### 1.2 Resultado de validación:

```python
trabajadores_validos = [
    {
        'nombre': 'Juan Pérez',
        'documento': '12345678',
        'empresa': Epresa(id=6),
        'cargo': Cargo(id=3),
        'centro': Centroop(id=101),
        'tipo_examen': 'INGRESO',
        'examenes_bd': [Examen(id=1), Examen(id=2)]  # Objetos
    },
    {
        'nombre': 'María López',
        'documento': '87654321',
        'empresa': Epresa(id=6),
        'cargo': Cargo(id=3),
        'centro': Centroop(id=101),
        'tipo_examen': 'ESPECIAL',
        'examenes_bd': [Examen(id=5), Examen(id=6)]  # Objetos
    },
    {
        'nombre': 'Carlos Ruiz',
        'documento': '11111111',
        'empresa': Epresa(id=6),
        'cargo': Cargo(id=3),
        'centro': Centroop(id=101),
        'tipo_examen': 'POST_INCAPACIDAD',
        'examenes_bd': [Examen(id=1), Examen(id=7)]  # Objetos
    }
]
```

---

## 💾 PASO 2: CREAR LOTE (CorreoExamenEnviado)

Sistema genera un ÚNICO registro para todo el envío:

```python
# Se crea 1 SOLO registro (lote)
lote = CorreoExamenEnviado.objects.create(
    uuid_correo="a3f7d2b5-20260105130045",  # Autogenerado
    enviado_por=usuario_autenticado,         # El que hace el request
    asunto="Convocatoria a exámenes médicos",
    cuerpo_correo="<html>...</html>",        # HTML
    correos_destino="practicante@regency.com.co",
    tipo_examen="MIXTO",  # Hay INGRESO, ESPECIAL, POST_INCAPACIDAD
    enviado_correctamente=False,
    fecha_envio=datetime.now()  # NOW = 2026-01-05 13:00:45
)

# BASE DE DATOS - TABLA CorreoExamenEnviado
┌────┬─────────────────────────┬──────────┬──────┬──────────────────┬──────────────┐
│ id │ uuid_correo             │ asunto   │ tipo │ enviado_por      │ fecha_envio  │
├────┼─────────────────────────┼──────────┼──────┼──────────────────┼──────────────┤
│ 1  │ a3f7d2b5-20260105130045 │ Convoca… │ MIXTO│ 1112039941       │ 2026-01-05…  │
└────┴─────────────────────────┴──────────┴──────┴──────────────────┴──────────────┘

Resultado: lote.id = 1
```

---

## 👥 PASO 3: CREAR RegistroExamenes (1 POR TRABAJADOR)

Para CADA trabajador validado, se crea UN registro:

```python
# TRABAJADOR 1: Juan Pérez
registro_juan = RegistroExamenes.objects.create(
    uuid_trabajador="f8e2c1a9-4d7f-11eb-ae93-0242ac120002",  # UUID único
    correo_lote=lote,                                         # FK al lote
    nombre_trabajador="Juan Pérez",
    documento_trabajador="12345678",
    empresa_id=6,                                             # FK a Epresa
    cargo_id=3,                                               # FK a Cargo
    centro_id=101,                                            # FK a Centroop
    tipo_examen="INGRESO",                                    # Del CSV
    examenes_asignados=None,                                  # NO SE USA
    estado_trabajador=0,                                      # Pendiente
    fecha_registro=datetime.now()
)

# TRABAJADOR 2: María López
registro_maria = RegistroExamenes.objects.create(
    uuid_trabajador="g9f3d2b0-5e8g-12fc-bf94-1353bd231113",
    correo_lote=lote,
    nombre_trabajador="María López",
    documento_trabajador="87654321",
    empresa_id=6,
    cargo_id=3,
    centro_id=101,
    tipo_examen="ESPECIAL",                                   # ← NUEVO TIPO
    examenes_asignados=None,
    estado_trabajador=0,
    fecha_registro=datetime.now()
)

# TRABAJADOR 3: Carlos Ruiz
registro_carlos = RegistroExamenes.objects.create(
    uuid_trabajador="h0g4e3c1-6f9h-13gd-cg05-2464ce342224",
    correo_lote=lote,
    nombre_trabajador="Carlos Ruiz",
    documento_trabajador="11111111",
    empresa_id=6,
    cargo_id=3,
    centro_id=101,
    tipo_examen="POST_INCAPACIDAD",                           # ← NUEVO TIPO
    examenes_asignados=None,
    estado_trabajador=0,
    fecha_registro=datetime.now()
)

# BASE DE DATOS - TABLA RegistroExamenes
┌────┬──────────────────────┬──────────────┬───────────┬─────────────────┬──────┐
│ id │ uuid_trabajador      │ nombre       │ documento │ correo_lote_id  │ tipo │
├────┼──────────────────────┼──────────────┼───────────┼─────────────────┼──────┤
│ 1  │ f8e2c1a9-4d7f-11eb…  │ Juan Pérez   │ 12345678  │ 1               │ ING  │
│ 2  │ g9f3d2b0-5e8g-12fc…  │ María López  │ 87654321  │ 1               │ ESP  │
│ 3  │ h0g4e3c1-6f9h-13gd…  │ Carlos Ruiz  │ 11111111  │ 1               │ POST │
└────┴──────────────────────┴──────────────┴───────────┴─────────────────┴──────┘

Resultados:
├─ registro_juan.id = 1
├─ registro_maria.id = 2
└─ registro_carlos.id = 3
```

---

## 🆕 PASO 4: CREAR RegistroExamenesEnviados (NUEVA TABLA - LA CLAVE)

### ¿QUÉ ES ESTA TABLA?

Es una tabla INTERMEDIARIA que registra:
- **QUÉ examen** fue enviado
- **A QUIÉN** (trabajador)
- **CUÁNDO** fue enviado
- **QUÉ TIPO** de examen es
- **CUÁL ES EL ESTADO** (pendiente, completado, etc.)
- **CUÁL ES EL RESULTADO** (aprobado, no_aprobado, null)

### DEFINICIÓN DE LA TABLA:

```python
class RegistroExamenesEnviados(models.Model):
    """
    Tabla intermediaria que registra CADA EXAMEN enviado a CADA TRABAJADOR.
    Proporciona trazabilidad completa.
    """
    registro_examen = models.ForeignKey(
        RegistroExamenes,
        on_delete=models.CASCADE,
        related_name='examenes_enviados'  # ← Acceso inverso
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

### GUARDAR REGISTROS - PASO 4:

```python
# JUAN PÉREZ (INGRESO): Radiografía, Análisis de Sangre
RegistroExamenesEnviados.objects.create(
    registro_examen=registro_juan,          # FK a RegistroExamenes(id=1)
    examen=examen_radiografia,              # FK a Examen(id=1)
    tipo_examen="INGRESO",                  # Del RegistroExamenes
    estado="pendiente",                     # Inicial
    resultado=None,                         # Sin resultado aún
    fecha_envio=datetime.now()              # 2026-01-05 13:00:45
)
# → RegistroExamenesEnviados(id=1)

RegistroExamenesEnviados.objects.create(
    registro_examen=registro_juan,
    examen=examen_sangre,                   # FK a Examen(id=2)
    tipo_examen="INGRESO",
    estado="pendiente",
    resultado=None,
    fecha_envio=datetime.now()
)
# → RegistroExamenesEnviados(id=2)

---

# MARÍA LÓPEZ (ESPECIAL): Cardiología, Psicología
RegistroExamenesEnviados.objects.create(
    registro_examen=registro_maria,         # FK a RegistroExamenes(id=2)
    examen=examen_cardiologia,              # FK a Examen(id=5)
    tipo_examen="ESPECIAL",                 # ← NUEVO TIPO
    estado="pendiente",
    resultado=None,
    fecha_envio=datetime.now()
)
# → RegistroExamenesEnviados(id=3)

RegistroExamenesEnviados.objects.create(
    registro_examen=registro_maria,
    examen=examen_psicologia,               # FK a Examen(id=6)
    tipo_examen="ESPECIAL",
    estado="pendiente",
    resultado=None,
    fecha_envio=datetime.now()
)
# → RegistroExamenesEnviados(id=4)

---

# CARLOS RUIZ (POST_INCAPACIDAD): Radiografía, EKG
RegistroExamenesEnviados.objects.create(
    registro_examen=registro_carlos,        # FK a RegistroExamenes(id=3)
    examen=examen_radiografia,              # FK a Examen(id=1) - REUTILIZADO
    tipo_examen="POST_INCAPACIDAD",         # ← NUEVO TIPO
    estado="pendiente",
    resultado=None,
    fecha_envio=datetime.now()
)
# → RegistroExamenesEnviados(id=5)

RegistroExamenesEnviados.objects.create(
    registro_examen=registro_carlos,
    examen=examen_ekg,                      # FK a Examen(id=7)
    tipo_examen="POST_INCAPACIDAD",
    estado="pendiente",
    resultado=None,
    fecha_envio=datetime.now()
)
# → RegistroExamenesEnviados(id=6)
```

### TABLA EN BASE DE DATOS - RegistroExamenesEnviados:

```
┌────┬──────────────────┬───────────┬──────────────┬──────────┬──────────┬─────────────────┐
│ id │ registro_examen  │ examen_id │ tipo_examen  │ estado   │ resultado│ fecha_envio     │
├────┼──────────────────┼───────────┼──────────────┼──────────┼──────────┼─────────────────┤
│ 1  │ 1 (Juan-Perez)   │ 1 (Radio) │ INGRESO      │ pendiente│ NULL     │ 2026-01-05 13:0…│
│ 2  │ 1 (Juan-Perez)   │ 2 (Sangre)│ INGRESO      │ pendiente│ NULL     │ 2026-01-05 13:0…│
│ 3  │ 2 (María-López)  │ 5 (Cardio)│ ESPECIAL     │ pendiente│ NULL     │ 2026-01-05 13:0…│
│ 4  │ 2 (María-López)  │ 6 (Psico) │ ESPECIAL     │ pendiente│ NULL     │ 2026-01-05 13:0…│
│ 5  │ 3 (Carlos-Ruiz)  │ 1 (Radio) │ POST_INCAPAC │ pendiente│ NULL     │ 2026-01-05 13:0…│
│ 6  │ 3 (Carlos-Ruiz)  │ 7 (EKG)   │ POST_INCAPAC │ pendiente│ NULL     │ 2026-01-05 13:0…│
└────┴──────────────────┴───────────┴──────────────┴──────────┴──────────┴─────────────────┘

¡TRAZABILIDAD COMPLETA!
```

---

## 📧 PASO 5: ENVIAR CORREOS

Sistema genera correos con información del lote y trabaja:

```python
# Email 1 - Para Juan Pérez (INGRESO)
TO: juan.perez@company.com
SUBJECT: Convocatoria a exámenes médicos
BODY:
    Cordial Saludo Juan Pérez,
    
    UUID del lote: a3f7d2b5-20260105130045
    Tipo de examen: INGRESO
    
    Exámenes asignados:
    - Radiografía
    - Análisis de Sangre
    
    Debe completarlos en: https://link-portal.com/examen/...

---

# Email 2 - Para María López (ESPECIAL)
TO: maria.lopez@company.com
SUBJECT: Convocatoria a exámenes médicos
BODY:
    Cordial Saludo María López,
    
    UUID del lote: a3f7d2b5-20260105130045
    Tipo de examen: ESPECIAL
    
    Exámenes asignados:
    - Cardiología
    - Psicología
    
    Debe completarlos en: https://link-portal.com/examen/...

---

# Email 3 - Para Carlos Ruiz (POST_INCAPACIDAD)
TO: carlos.ruiz@company.com
SUBJECT: Convocatoria a exámenes médicos
BODY:
    Cordial Saludo Carlos Ruiz,
    
    UUID del lote: a3f7d2b5-20260105130045
    Tipo de examen: POST_INCAPACIDAD
    
    Exámenes asignados:
    - Radiografía
    - EKG
    
    Debe completarlos en: https://link-portal.com/examen/...
```

---

## 🔄 PASO 6: TRABAJADOR COMPLETA EXAMEN

Después, cuando trabajador realiza examen:

```python
# Trabajador accede a portal con UUID: f8e2c1a9-4d7f-11eb-ae93-0242ac120002 (Juan)
# Completa Radiografía con resultado APROBADO

PUT /examenes/trabajador/f8e2c1a9-4d7f-11eb-ae93-0242ac120002/examen-completado/
{
    "examen_id": 1,
    "resultado": "aprobado"
}

ACTUALIZAR RegistroExamenesEnviados:
registro_enviado = RegistroExamenesEnviados.objects.get(
    registro_examen__uuid_trabajador="f8e2c1a9-4d7f-11eb-ae93-0242ac120002",
    examen_id=1
)
registro_enviado.estado = "completado"
registro_enviado.resultado = "aprobado"
registro_enviado.fecha_completado = datetime.now()
registro_enviado.save()

---

TABLA RegistroExamenesEnviados DESPUÉS:
┌────┬──────────────────┬───────────┬──────────────┬──────────┬──────────┬─────────────────┬──────────────────┐
│ id │ registro_examen  │ examen_id │ tipo_examen  │ estado   │ resultado│ fecha_envio     │ fecha_completado │
├────┼──────────────────┼───────────┼──────────────┼──────────┼──────────┼─────────────────┼──────────────────┤
│ 1  │ 1 (Juan-Perez)   │ 1 (Radio) │ INGRESO      │ ✓COMPL   │ ✓APROB   │ 2026-01-05 13:0…│ 2026-01-05 14:30 │
│ 2  │ 1 (Juan-Perez)   │ 2 (Sangre)│ INGRESO      │ pendiente│ NULL     │ 2026-01-05 13:0…│ NULL             │
│ 3  │ 2 (María-López)  │ 5 (Cardio)│ ESPECIAL     │ pendiente│ NULL     │ 2026-01-05 13:0…│ NULL             │
│ 4  │ 2 (María-López)  │ 6 (Psico) │ ESPECIAL     │ pendiente│ NULL     │ 2026-01-05 13:0…│ NULL             │
│ 5  │ 3 (Carlos-Ruiz)  │ 1 (Radio) │ POST_INCAPAC │ pendiente│ NULL     │ 2026-01-05 13:0…│ NULL             │
│ 6  │ 3 (Carlos-Ruiz)  │ 7 (EKG)   │ POST_INCAPAC │ pendiente│ NULL     │ 2026-01-05 13:0…│ NULL             │
└────┴──────────────────┴───────────┴──────────────┴──────────┴──────────┴─────────────────┴──────────────────┘

✓ TRAZABILIDAD: Radiografía completada y aprobada
```

---

## 📊 ESTADO FINAL: TABLAS RELACIONADAS

```
CorreoExamenEnviado (1 lote)
│
├─ id=1
├─ uuid_correo=a3f7d2b5-20260105130045
├─ tipo_examen=MIXTO
└─ fecha_envio=2026-01-05 13:00:45
   │
   └─── RegistroExamenes (3 trabajadores)
       │
       ├─ id=1, uuid_trabajador=f8e2..., nombre=Juan, tipo=INGRESO
       │  └─ RegistroExamenesEnviados (2 exámenes)
       │     ├─ id=1, examen_id=1(Radiografía), estado=completado, resultado=aprobado
       │     └─ id=2, examen_id=2(Sangre), estado=pendiente, resultado=NULL
       │
       ├─ id=2, uuid_trabajador=g9f3..., nombre=María, tipo=ESPECIAL
       │  └─ RegistroExamenesEnviados (2 exámenes)
       │     ├─ id=3, examen_id=5(Cardiología), estado=pendiente
       │     └─ id=4, examen_id=6(Psicología), estado=pendiente
       │
       └─ id=3, uuid_trabajador=h0g4..., nombre=Carlos, tipo=POST_INCAPACIDAD
          └─ RegistroExamenesEnviados (2 exámenes)
             ├─ id=5, examen_id=1(Radiografía), estado=pendiente
             └─ id=6, examen_id=7(EKG), estado=pendiente
```

---

## 🎯 VENTAJAS DE ESTA ESTRUCTURA

### TRAZABILIDAD:
```python
# Fácil: ¿Qué exámenes tiene María López pendientes?
examenes_pendientes = RegistroExamenesEnviados.objects.filter(
    registro_examen__documento_trabajador='87654321',
    estado='pendiente'
).select_related('examen')

for env in examenes_pendientes:
    print(f"{env.examen.nombre} ({env.tipo_examen})")
# OUTPUT:
# Cardiología (ESPECIAL)
# Psicología (ESPECIAL)
```

### REPORTES:
```python
# ¿Cuántos exámenes ESPECIAL se han completado?
completados = RegistroExamenesEnviados.objects.filter(
    tipo_examen='ESPECIAL',
    estado='completado'
).count()
# OUTPUT: 0 (María aún no completa)
```

### AUDITORÍA:
```python
# ¿Cuándo se envió el examen a María y cuándo lo completó?
env = RegistroExamenesEnviados.objects.get(id=3)
print(f"Enviado: {env.fecha_envio}")
print(f"Completado: {env.fecha_completado}")
# OUTPUT:
# Enviado: 2026-01-05 13:00:45
# Completado: None (aún pendiente)
```

---

## 📋 RESUMEN: TABLAS MODIFICADAS

### RegistroExamenes (EXISTENTE - ACTUALIZADA)
```python
tipo_examen = [
    "INGRESO",
    "PERIODICO", 
    "RETIRO",
    "ESPECIAL",        # ← NUEVO
    "POST_INCAPACIDAD" # ← NUEVO
]
examenes_asignados = TextField  # Se deja NULL o sin usar
```

### CorreoExamenEnviado (EXISTENTE - ACTUALIZADA)
```python
tipo_examen = [
    "INGRESO",
    "PERIODICO",
    "RETIRO",
    "ESPECIAL",        # ← NUEVO
    "POST_INCAPACIDAD" # ← NUEVO
]
```

### RegistroExamenesEnviados (NUEVA TABLA - LA CLAVE)
```python
class RegistroExamenesEnviados(Model):
    registro_examen (FK)  → RegistroExamenes
    examen (FK)           → Examen
    tipo_examen           → CharField choices
    estado                → CharField (pendiente, completado, no_realizado)
    resultado             → CharField (aprobado, no_aprobado, null)
    fecha_envio           → DateTimeField (auto_now_add)
    fecha_completado      → DateTimeField (nullable)
```

---

## ✨ FLUJO FINAL RESUMIDO

```
CSV INGRESO
    ↓
VALIDAR (sin ExamenesCargo)
    ↓
CREAR CorreoExamenEnviado (1 lote)
    ↓
PARA CADA TRABAJADOR:
    ├─ Crear RegistroExamenes
    ├─ PARA CADA EXAMEN:
    │  └─ Crear RegistroExamenesEnviados ← LA CLAVE
    └─ Enviar Email
    ↓
TRABAJADOR COMPLETA EXAMEN
    ↓
ACTUALIZAR RegistroExamenesEnviados
    ├─ estado = "completado"
    ├─ resultado = "aprobado"
    └─ fecha_completado = NOW()
```

---

## 🔍 DIFERENCIAS CLAVE: ANTES vs DESPUÉS

### ANTES:
```
ExamenesCargo (validador) → Rechaza ESPECIAL porque no existe config
RegistroExamenes.examenes_asignados = "Cardiología, Psicología" (CSV text)
NO hay tabla intermediaria
→ Difícil rastrear: ¿Cuándo se envió? ¿Cuál es el resultado?
```

### DESPUÉS:
```
ExamenesCargo (solo info) → Acepta ESPECIAL, no valida
RegistroExamenes.examenes_asignados = NULL (no se usa)
RegistroExamenesEnviados (nuevos 6 registros) ← TRAZABILIDAD
→ Fácil rastrear: Fecha envío, estado, resultado, ID examen
```

