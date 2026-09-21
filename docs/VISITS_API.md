# API de visitas técnicas

Este documento describe los endpoints que existen actualmente en `AppVisits`. Todas las rutas pasan por Nginx y requieren JWT:

```http
Authorization: Bearer <access_token>
```

## URLs base

| Entorno | API |
| --- | --- |
| Desarrollo Docker | `http://localhost/api` |
| Producción | `https://djsolutions.io/api` |

El token se obtiene con `POST /auth/token/` y se renueva con `POST /auth/token/refresh/`. Los ejemplos siguientes usan desarrollo; en producción solo cambia la URL base.

## Permisos

- Administrador (`tipo_usuario >= 2`): consulta todas las visitas y puede crear, editar, eliminar y listar técnicos.
- Técnico activo (`tipo_usuario == 1`): solo consulta y ejecuta sus visitas asignadas.
- Una visita finalizada no se puede editar. Para finalizar se usa la acción específica.

## Endpoints disponibles

| Método | Ruta | Uso |
| --- | --- | --- |
| `GET`, `POST` | `/visits/` | Listar o crear visitas |
| `GET`, `PATCH`, `DELETE` | `/visits/{id}/` | Detalle, edición parcial o eliminación |
| `POST` | `/visits/{id}/iniciar/` | Cambiar una visita pendiente a `en_proceso` |
| `POST` | `/visits/{id}/finalizar/` | Crear el reporte y finalizar |
| `POST` | `/visits/{id}/fotos/` | Subir evidencias |
| `DELETE` | `/visits/{id}/fotos/{foto_id}/` | Eliminar una evidencia |
| `GET` | `/visits/calendario/` | Visitas agrupadas por fecha |
| `GET` | `/visits/{id}/pdf/` | Descargar el reporte final |
| `POST` | `/visits/{id}/sincronizar/` | Finalización offline atómica e idempotente |
| `GET` | `/visits/tecnicos/` | Técnicos activos; solo administrador |

### Listar visitas

`GET /api/visits/` admite:

- `estado`: `pendiente`, `en_proceso`, `finalizada`, `cancelada` o `all`.
- `tecnico_id`: identificador numérico.
- `fecha`: fecha `YYYY-MM-DD`.
- `mes`: mes `YYYY-MM`.
- `search`: nombre, documento, teléfono, dirección o número de tarea.
- `search_field`: `all`, `document` o `phone`. Los dos últimos aceptan hasta 15 dígitos.

```bash
curl "http://localhost/api/visits/?mes=2026-09&estado=pendiente" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (la lista real contiene además los campos de visualización definidos por el serializador):

```json
[
  {
    "id": 42,
    "numero_tarea": "1041",
    "cliente_nombre": "Cliente de prueba",
    "estado": "pendiente",
    "fecha": "2026-09-25",
    "hora": "09:30:00",
    "tecnico_id": 12,
    "evidencias_count": 0
  }
]
```

### Crear una visita

`POST /api/visits/` es exclusivo de administradores. `fecha` no puede estar en el pasado y el técnico debe estar activo.

```json
{
  "cliente_nombre": "Cliente de prueba",
  "cliente_identificacion": "123456789",
  "cliente_telefono": "3001234567",
  "cliente_correo": "cliente@example.com",
  "cliente_direccion": "Calle 1 # 2-3",
  "tipo_tarea": "visita_urbana",
  "fecha": "2026-09-25",
  "hora": "09:30:00",
  "descripcion": "Revisión del equipo",
  "observaciones_iniciales": "Acceso por recepción",
  "valor_visita": "80000.00",
  "tecnico_id": 12
}
```

Una creación válida devuelve `201` con el detalle completo. Los errores de validación devuelven `400` y un objeto por campo, por ejemplo:

```json
{
  "fecha": ["La fecha de la visita no puede ser anterior al día actual."]
}
```

Valores actuales de `tipo_tarea`: `visita_urbana`, `instalacion_calentador`, `mantenimiento_calentador`, `instalacion_secadora`, `servicio_cancelado`, `visita_afueras`, `mantenimiento_estufa`, `revision_periodica`, `mantenimiento_acumulacion`, `programacion_doble` y `mantenimiento_turco`.

### Editar una visita

`PATCH /api/visits/{id}/` es exclusivo de administradores. Acepta `tipo_tarea`, `fecha`, `hora`, `descripcion`, `observaciones_iniciales`, `valor_visita`, `estado` y `tecnico`. El campo `tecnico` recibe la clave primaria del técnico. Para completar una visita no se envía `estado=finalizada`; se usa `/finalizar/` o `/sincronizar/`.

### Iniciar y finalizar

`POST /api/visits/{id}/iniciar/` no requiere cuerpo y solo funciona para una visita pendiente asignada al usuario o visible para el administrador.

`POST /api/visits/{id}/finalizar/` acepta JSON o `multipart/form-data` con los campos del reporte:

- Obligatorios: `persona_atiende`, `equipo`, `ubicacion_equipo`, `motivo_servicio`, `solucion_realizada`.
- Condicionales: `equipo_otro` si `equipo=otro`; `ubicacion_otro` si `ubicacion_equipo=otro`.
- Opcionales: `observaciones`, `recomendaciones`, `valor_servicio`, `metodo_pago`, `firma_base64`, `inicio_desplazamiento`, `duracion_desplazamiento`.
- `equipo`: `estufa`, `horno`, `calentador`, `parrilla`, `caldera`, `calefactor`, `otro`.
- `ubicacion_equipo`: `cocina`, `patio`, `balcon`, `exterior`, `sotano`, `otro`.
- `metodo_pago`: `efectivo`, `transferencia`, `tarjeta`, `credito`, `otro`.

### Evidencias

`POST /api/visits/{id}/fotos/` usa `multipart/form-data`; repita el campo `fotos` para varios archivos. Se aceptan JPEG, PNG y WebP, máximo 5 MB por imagen y 20 evidencias por visita.

```bash
curl -X POST "http://localhost/api/visits/42/fotos/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "fotos=@evidencia.jpg"
```

### Calendario y PDF

- `GET /api/visits/calendario/?mes=2026-09` devuelve un objeto cuyas claves son fechas.
- `GET /api/visits/{id}/pdf/` devuelve `application/pdf` cuando la visita ya tiene reporte.

El detalle `GET /api/visits/{id}/` devuelve `200` con la visita, el cliente embebido, el técnico, el reporte cuando existe, las evidencias y `sync_version`. Devuelve `404` si la visita no existe o no pertenece al técnico autenticado.

### Sincronización offline

`POST /api/visits/{id}/sincronizar/` usa `multipart/form-data` y los mismos campos del reporte, además de al menos una `fotos` y una `firma_base64` PNG/JPEG válida de máximo 1 MB.

Cabeceras obligatorias:

- `Idempotency-Key`: entre 16 y 100 caracteres alfanuméricos, guion o guion bajo. Repetir la misma operación con la misma clave devuelve la respuesta guardada.
- `If-Match`: versión `sync_version` entregada en el detalle actual de la visita.

Respuestas especiales: `409` para operación cerrada o clave reutilizada con otros datos, `412` si cambió la visita y `428` si falta `If-Match`.

## Clientes y ubicaciones

`AppVisits` no expone actualmente endpoints independientes para clientes ni ubicaciones. Los datos del cliente se crean embebidos en `POST /visits/` y la dirección está en `cliente_direccion`. No existe un recurso separado de ubicaciones de visita.

Si una aplicación externa necesita reutilizar clientes o direcciones, se propone una futura API versionada (`/api/v1/visit-clients/` y `/api/v1/visit-locations/`) con búsqueda, permisos y deduplicación definidos antes de implementarla. Esas rutas son una propuesta y no deben consumirse todavía.
