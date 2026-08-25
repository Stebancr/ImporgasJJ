# Quick Reference - AppVisits

## 📌 Endpoints Rápido

| Método | Endpoint | Rol | Descripción |
|--------|----------|-----|-------------|
| GET | `/visits/` | Técnico/Admin | Listar visitas |
| POST | `/visits/` | Admin | Crear visita |
| GET | `/visits/{id}/` | Técnico/Admin | Detalle visita |
| PATCH | `/visits/{id}/` | Admin | Actualizar visita |
| DELETE | `/visits/{id}/` | Admin | Eliminar visita |
| POST | `/visits/{id}/iniciar/` | Técnico/Admin | Iniciar visita |
| POST | `/visits/{id}/finalizar/` | Técnico/Admin | Finalizar + reporte |
| POST | `/visits/{id}/fotos/` | Técnico/Admin | Subir fotos |
| DELETE | `/visits/{id}/fotos/{foto_id}/` | Técnico/Admin | Eliminar foto |
| GET | `/visits/calendario/?mes=YYYY-MM` | Técnico/Admin | Calendario |
| GET | `/visits/{id}/pdf/` | Admin | Descargar PDF |
| GET | `/visits/tecnicos/` | Admin | Listar técnicos |

---

## 🔄 Estados de Visita

```
Pendiente ──────→ En Proceso ──────→ Finalizada
                                    ↑
                                    └─ Reporte enviado
                        ↓
                    Cancelada (opcional)
```

---

## 👥 Permisos por Rol

| Acción | tipo_usuario=0 (Técnico) | tipo_usuario≥1 (Admin) |
|--------|---|---|
| Ver sus visitas | ✅ | ✅ (todas) |
| Ver otras visitas | ❌ | ✅ |
| Crear visita | ❌ | ✅ |
| Editar visita | ❌ | ✅ |
| Eliminar visita | ❌ | ✅ |
| Iniciar visita | ✅ (propia) | ✅ (cualquiera) |
| Finalizar visita | ✅ (propia) | ✅ (cualquiera) |
| Subir fotos | ✅ (propia) | ✅ (cualquiera) |
| Descargar PDF | ❌ | ✅ |
| Ver técnicos | ❌ | ✅ |

---

## 📊 Modelos en BD

### ClienteVisita
```sql
SELECT * FROM visita_cliente;
-- nombre, identificacion, telefono, correo, direccion, fecha_creacion
```

### VisitaTecnica
```sql
SELECT * FROM visita_tecnica;
-- numero_tarea, tecnico_id, cliente_id, tipo_tarea, fecha, hora, estado...
```

### ReporteVisita
```sql
SELECT * FROM visita_reporte;
-- visita_id (OneToOne), persona_atiende, equipo, ubicacion, motivo, solucion...
```

### EvidenciaFotografica
```sql
SELECT * FROM visita_evidencia;
-- visita_id, imagen, descripcion, orden, subida_en
```

---

## 🎯 Casos de Uso Comunes

### Case 1: Admin Crea Visita para Técnico
```
POST /visits/
{
  "cliente_nombre": "Juan",
  "cliente_direccion": "Calle 5 #123",
  "tipo_tarea": "reparacion",
  "fecha": "2026-08-15",
  "hora": "10:30",
  "tecnico_id": 5
}
→ Estado: pendiente
```

### Case 2: Técnico Ve Su Visita
```
GET /visits/ (como técnico_id=5)
→ Solo visitas con tecnico_id=5
```

### Case 3: Técnico Inicia Visita
```
POST /visits/1/iniciar/
→ Estado: pendiente → en_proceso
→ Auto-crea ReporteVisita
→ Registra inicio_desplazamiento
```

### Case 4: Técnico Sube Fotos
```
POST /visits/1/fotos/
Form: fotos=[file1.jpg, file2.jpg, ...]
→ Máximo 20 fotos total
→ Se ordena automáticamente
```

### Case 5: Técnico Envía Reporte y Finaliza
```
POST /visits/1/finalizar/
{
  "persona_atiende": "Doña Rosa",
  "equipo": "estufa",
  "ubicacion_equipo": "cocina",
  "motivo_servicio": "Piloto no enciende",
  "solucion_realizada": "Se limpió y ajustó",
  "valor_servicio": 150000,
  "metodo_pago": "efectivo",
  "firma_base64": "data:image/png;base64,..."
}
→ Estado: en_proceso → finalizada
→ Crea/actualiza ReporteVisita
→ Guarda firma cliente
```

### Case 6: Admin Descarga PDF
```
GET /visits/1/pdf/
→ Descarga PDF con toda la info, fotos y firma
```

---

## 🔐 Headers Requeridos

```http
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

Para multipart (fotos):
```http
Authorization: Bearer {JWT_TOKEN}
Content-Type: multipart/form-data
```

---

## 📋 Tipos de Tarea

- `mantenimiento` → Mantenimiento Preventivo
- `instalacion` → Instalación
- `reparacion` → Reparación
- `revision` → Revisión Técnica
- `visita_tecnica` → Visita Técnica Perímetro Urbano
- `garantia` → Garantía

---

## 🛠️ Tipos de Equipo (en Reporte)

- `estufa` → Estufa
- `horno` → Horno
- `calentador` → Calentador
- `parrilla` → Parrilla
- `caldera` → Caldera
- `calefactor` → Calefactor
- `otro` → Otro (requiere `equipo_otro`)

---

## 📍 Ubicaciones de Equipo (en Reporte)

- `cocina` → Cocina
- `patio` → Patio
- `balcon` → Balcón
- `exterior` → Exterior
- `sotano` → Sótano
- `otro` → Otro (requiere `ubicacion_otro`)

---

## 💳 Métodos de Pago (en Reporte)

- `efectivo` → Efectivo
- `transferencia` → Transferencia
- `tarjeta` → Tarjeta
- `credito` → Crédito
- `otro` → Otro

---

## 🔍 Filtros en GET /visits/

```
?estado=pendiente           # Filtrar por estado
?estado=en_proceso
?estado=finalizada
?estado=cancelada

?tecnico_id=5              # Visitas de técnico específico

?fecha=2026-08-15          # Día específico

?mes=2026-08               # Mes completo

?search=Juan               # Busca en: cliente.nombre, cliente.direccion, numero_tarea

# Combinables:
?estado=pendiente&tecnico_id=5&mes=2026-08&search=Carlos
```

---

## 🐛 Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| 401 Unauthorized | Sin token | Incluir `Authorization: Bearer {token}` |
| 403 Forbidden | Permisos insuficientes | Admin solo para crear/editar |
| 404 Not Found | Visita no existe | Verificar ID |
| 400 Bad Request | Datos inválidos | Ver response.data para detalles |
| 400 "Solo se puede iniciar una visita pendiente" | Estado incorrecto | Visita ya está en_proceso/finalizada |
| 400 "Máximo 20 fotografías" | Demasiadas fotos | Eliminar algunas antes de subir |

---

## 📱 Flujo Técnico en App Móvil

```
1. Técnico abre la app
   ├─ GET /visits/        ← Ve su lista
   └─ Elige una visita

2. Ve detalles
   ├─ GET /visits/{id}/
   └─ Si estado = "pendiente" → botón "Iniciar Visita"

3. Inicia visita
   ├─ POST /visits/{id}/iniciar/
   ├─ Estado cambia a "en_proceso"
   └─ Abre cámara para fotos

4. Captura fotos
   ├─ POST /visits/{id}/fotos/
   └─ Repite hasta completar

5. Abre formulario de reporte
   ├─ Llena campos de equipo, motivo, solución
   ├─ Captura firma del cliente (SignaturePad)
   └─ Sube nuevamente si hay más fotos

6. Finaliza visita
   ├─ POST /visits/{id}/finalizar/
   ├─ Envía toda la data del reporte + firma
   └─ Estado cambia a "finalizada"

7. Confirma envío
   └─ ✅ Visita completada
```

---

## 📊 Flujo Admin en Panel

```
1. Accede a Panel Admin
   ├─ GET /visits/tecnicos/   ← Lista técnicos
   └─ GET /visits/            ← Ve todas las visitas

2. Crea nueva visita
   ├─ POST /visits/           ← Formulario
   ├─ Selecciona técnico
   └─ Se asigna automáticamente

3. Monitorea progreso
   ├─ GET /visits/calendario/?mes=YYYY-MM  ← Vista calendario
   └─ GET /visits/                         ← Filtra por estado

4. Revisa reportes
   ├─ GET /visits/{id}/       ← Ve todo (cliente, reporte, fotos)
   └─ GET /visits/{id}/pdf/   ← Descarga PDF formal

5. Generación de reportes
   ├─ Filtra visitas finalizadas
   └─ Genera PDFs en batch si es necesario
```

---

## 💾 Almacenamiento de Archivos

```
/media/
├── firmas/
│   └── firma_3847562.png      # Firmadas por cliente
└── evidencias/
    ├── 20260815_10_30_45.jpg  # Fotos de técnico
    ├── 20260815_10_31_00.jpg
    └── ...
```

---

## 🔄 Ciclo de Vida Completo

```
Visita Creada (Admin)
  ↓
  Pendiente
  ├─ Técnico ve en su lista
  ├─ Técnico abre detalle
  └─ Técnico hace POST /iniciar/
      ↓
      En Proceso
      ├─ Técnico trabaja (tiempo real)
      ├─ Sube fotos
      ├─ Llena reporte
      └─ Hace POST /finalizar/ con datos + firma
          ↓
          Finalizada
          ├─ Admin puede ver todo
          ├─ Admin descarga PDF
          └─ Se archiva para reportes
```

---

## 🎓 Para Desarrolladores

### Agregar Campo al Reporte
1. Editar `models.py` → `ReporteVisita`
2. Crear migración: `makemigrations`
3. Aplicar migración: `migrate`
4. Actualizar `serializers.py` → `ReporteCreateSerializer`
5. Actualizar frontend

### Agregar Nuevo Tipo de Tarea
1. En `models.py` → `TIPO_TAREA_CHOICES`
2. No requiere migración si usas choicefields
3. Actualizar opciones en frontend

### Cambiar Límite de Fotos
En `views.py` línea 276:
```python
if current_count + len(fotos) > 20:  # ← Cambiar este número
```

---

## 📞 Contacto con Backend

**Rutas:** `BACKEND/AppVisits/`
**Autor:** Stebancr
**Última actualización:** 2026-08-05
**Estado:** Producción
