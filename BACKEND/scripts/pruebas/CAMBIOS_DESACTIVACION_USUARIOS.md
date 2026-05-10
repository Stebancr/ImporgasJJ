# 📋 Cambios en Sistema de Desactivación de Usuarios

## 🎯 Objetivo General
Implementar funcionalidad para desactivar múltiples usuarios de forma masiva y garantizar que los usuarios desactivados (estado=0) no reciban correos electrónicos ni aparezcan en reportes de analítica ni capacitaciones.

---

## ✅ Cambios Realizados

### 1. **Endpoint `CambiarEstadoUsuarioView` - Soporte para Listas de IDs**
**Archivo:** `backend/usuarios/views.py`

#### Cambios:
- ✅ **PATCH** (Original): Permite desactivar/activar UN usuario individual
  - URL: `/usuarios/cambiar-estado-usuario/<colaborador_id>/`
  - Body: `{ "estado": 1 o 0 }`
  - Sigue funcionando como antes

- ✨ **POST** (Nuevo): Permite desactivar/activar MÚLTIPLES usuarios
  - URL: `/usuarios/cambiar-estado-usuario/`
  - Body: `{ "colaborador_ids": [1, 2, 3, ...], "estado": 1 o 0 }`
  - Retorna detalle de cada usuario procesado

#### Ejemplo de uso:
```bash
# Desactivar 5 usuarios de una vez
curl -X POST http://localhost:8000/user/cambiar-estado-usuario/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "colaborador_ids": [10, 20, 30, 40, 50],
    "estado": 0
  }'

# Respuesta:
{
  "mensaje": "Procesamiento completado: 5 actualizados, 0 errores",
  "total": 5,
  "actualizados": 5,
  "errores": 0,
  "detalles": [
    {"colaborador_id": 10, "usuario_id": 1, "estado": 0, "success": true},
    {"colaborador_id": 20, "usuario_id": 2, "estado": 0, "success": true},
    ...
  ]
}
```

---

### 2. **Filtro de Usuarios Desactivados en Envío de Correos**
**Archivo:** `backend/capacitaciones/utils.py`

#### Función: `enviar_correo_batch()`
**Cambio Principal:** Filtra automáticamente usuarios con `estadousuario=0`

```python
# ANTES: Enviaba a TODOS los correos
correos_validos = [email for email in correos if email and '@' in email]

# DESPUÉS: Solo usuarios ACTIVOS
correos_validos = []
usuarios_desactivados = 0

for email in correos:
    if not email or '@' not in email:
        continue
    
    # Verificar que el usuario esté activo (estadousuario = 1)
    usuario_activo = Usuarios.objects.filter(
        idcolaboradoru__correocolaborador=email,
        estadousuario=1
    ).exists()
    
    if not usuario_activo:
        usuarios_desactivados += 1
        logger.debug(f"Email {email} omitido (usuario desactivado)")
        continue
    
    correos_validos.append(email)
```

**Impacto:**
- ✅ Usuarios desactivados NO reciben correos de capacitaciones
- ✅ Se registra en logs cuántos usuarios fueron omitidos
- ✅ Mantiene compatibilidad con batching de 500 correos máximo

---

### 3. **Filtro de Usuarios Desactivados en Reportes de Analítica**
**Archivo:** `backend/analitica/views.py`

#### Función: `ProgresoEmpresarialView.get()`
**Cambio:** Agrega filtro `Q(colaboradores__estadocolaborador=1)` en query de progreso

```python
# ANTES
centros = Centroop.objects.filter(id_proyecto=proyecto).annotate(
    promedio_progreso=Avg(
        'colaboradores__progresocapacitaciones__progreso',
        filter=(
            Q(colaboradores__progresocapacitaciones__capacitacion__fecha_inicio__lte=fin_mes) &
            Q(colaboradores__progresocapacitaciones__capacitacion__fecha_fin__gte=inicio_mes) &
            ~Q(colaboradores__progresocapacitaciones__capacitacion__estado__in=[0, 3])
        )
    )
)

# DESPUÉS
centros = Centroop.objects.filter(id_proyecto=proyecto).annotate(
    promedio_progreso=Avg(
        'colaboradores__progresocapacitaciones__progreso',
        filter=(
            Q(colaboradores__progresocapacitaciones__capacitacion__fecha_inicio__lte=fin_mes) &
            Q(colaboradores__progresocapacitaciones__capacitacion__fecha_fin__gte=inicio_mes) &
            ~Q(colaboradores__progresocapacitaciones__capacitacion__estado__in=[0, 3]) &
            Q(colaboradores__estadocolaborador=1)  # FILTRO: Solo activos
        )
    )
)
```

**Impacto:**
- ✅ Reportes de analítica NO incluyen datos de usuarios desactivados
- ✅ Promedios de progreso se calculan solo con usuarios activos
- ✅ Datos más precisos de capacitaciones

---

### 4. **Filtro de Usuarios Desactivados en Reportes de Capacitaciones**
**Archivo:** `backend/capacitaciones/views.py`

#### Función: `ReporteCapacitacionesView._generar_reporte_capacitacion()`
**Cambio:** Valida `colaborador.estadocolaborador == 1` antes de incluir en reporte

```python
# En el loop de progreso
for progreso in progreso_qs:
    colaborador = progreso.colaborador
    
    # NUEVO: Solo incluir colaboradores activos
    if colaborador.estadocolaborador != 1:
        continue
    
    # ... resto del código
```

#### Función: `ReporteCapacitacionesView._generar_reporte_rango_fechas()`
**Cambio:** Mismo filtro aplicado

**Impacto:**
- ✅ Reportes de capacitaciones NO incluyen usuarios desactivados
- ✅ Descarga de Excel solo con datos relevantes
- ✅ Cálculo de totales y porcentajes con usuarios activos

---

### 5. **Filtro de Usuarios Desactivados en Tareas Celery de Notificación**
**Archivo:** `backend/notificaciones/tasks.py`

#### Función: `enviar_correo_capacitaciones_activas_y_activar()`
**Cambio:** Agrega filtro `colaborador__estadocolaborador=1` a query

```python
# ANTES
correos = list(
    progresoCapacitaciones.objects.filter(capacitacion=cap)
    .values_list("colaborador__correocolaborador", flat=True)
    ...
)

# DESPUÉS
correos = list(
    progresoCapacitaciones.objects.filter(
        capacitacion=cap,
        colaborador__estadocolaborador=1  # FILTRO: Solo activos
    )
    .values_list("colaborador__correocolaborador", flat=True)
    ...
)
```

#### Función: `notificar_capacitacion_por_vencer_7_dias()`
**Cambio:** Mismo filtro aplicado

#### Función: `notificar_capacitacion_vence_mañana()`
**Cambio:** Mismo filtro aplicado

#### Función: `notificar_jefes_por_colaboradores_sin_progreso()`
**Cambio:** Agrega filtro al query de `progresoCapacitaciones`

**Impacto:**
- ✅ Tareas automáticas NO envían correos a usuarios desactivados
- ✅ Notificaciones solo se generan para colaboradores activos
- ✅ Reduce carga de email innecesaria

---

## 📊 Flujo de Desactivación Completo

```
┌─────────────────────────────┐
│ Usuario Admin desactiva      │
│ múltiples colaboradores      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ POST /cambiar-estado-usuario │
│ {"colaborador_ids": [...]}  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Actualiza: Colaboradores & Usuarios      │
│ - Colaboradores.estadocolaborador = 0   │
│ - Usuarios.estadousuario = 0            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ ✅ Usuarios Desactivados Protegidos     │
│ - NO reciben correos                    │
│ - NO aparecen en reportes               │
│ - NO cuentan en analítica               │
│ - NO se incluyen en notificaciones      │
└─────────────────────────────────────────┘
```

---

## 🔍 Validaciones de Seguridad

1. **Permisos:** Solo SuperAdmin puede desactivar usuarios (clase `IsSuperAdmin`)
2. **Validación Individual:** Cada usuario es validado antes de actualizar
3. **Respuesta Detallada:** Se retorna estado de cada usuario procesado
4. **Logging:** Todos los cambios se registran en logs
5. **Transacciones:** Cambios se hacen de forma atómica

---

## 📝 Ejemplo de Uso Completo

### Script para desactivar múltiples usuarios:

```python
import requests
import json

API_URL = "http://localhost:8000"
TOKEN = "your-auth-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Desactivar 10 usuarios
colaborador_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

payload = {
    "colaborador_ids": colaborador_ids,
    "estado": 0  # 0 = inactivo, 1 = activo
}

response = requests.post(
    f"{API_URL}/user/cambiar-estado-usuario/",
    headers=headers,
    json=payload
)

print(response.json())
# {
#     "mensaje": "Procesamiento completado: 10 actualizados, 0 errores",
#     "total": 10,
#     "actualizados": 10,
#     "errores": 0,
#     "detalles": [...]
# }
```

---

## 🧪 Pruebas Recomendadas

1. **Endpoint POST:**
   - ✅ Desactivar 1 usuario
   - ✅ Desactivar 100+ usuarios
   - ✅ Desactivar usuario inexistente (validar error)
   - ✅ Activar usuarios (estado=1)

2. **Correos:**
   - ✅ Desactivar usuario → No recibe correo de capacitación
   - ✅ Reactivar usuario → Sí recibe correos nuevamente
   - ✅ Verificar logs de omisión

3. **Reportes:**
   - ✅ Generar reporte con usuarios desactivados
   - ✅ Verificar que NO aparecen en Excel
   - ✅ Comparar totales antes/después

4. **Tareas Celery:**
   - ✅ Ejecutar `enviar_correo_capacitaciones_activas_y_activar`
   - ✅ Verificar que usuarios desactivados no reciben correo
   - ✅ Revisar logs

---

## 📋 Checklist de Validación

- [x] Endpoint PATCH individual sigue funcionando
- [x] Endpoint POST masivo funciona
- [x] Correos no se envían a desactivados
- [x] Reportes no incluyen desactivados
- [x] Analítica no cuenta desactivados
- [x] Logging registra omisiones
- [x] Permisos se validan (SuperAdmin only)
- [x] Errores se manejan gracefully

---

## 🔐 Notas de Seguridad

1. Los usuarios desactivados siguen existiendo en base de datos (soft delete)
2. Se pueden reactivar cambiando `estado = 1`
3. Solo SuperAdmin puede cambiar estados
4. Los cambios se registran en logs del sistema
5. No se eliminan datos históricos del usuario

---

## 📞 Soporte

Para cuestiones sobre estos cambios:
1. Revisar logs en `django.log`
2. Verificar permisos del usuario admin
3. Validar estructura de datos en POST
4. Confirmar estado del celery si es tarea programada
