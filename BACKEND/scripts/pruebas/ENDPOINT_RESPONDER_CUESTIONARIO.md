# Endpoint: Responder Cuestionario de Lección

## Implementación Completada ✅

### URL
```
POST /capacitaciones/leccion/<int:leccion_id>/responder/
```

### Características Implementadas

1. **Autenticación Automática**
   - Obtiene el colaborador desde el token JWT (`request.user.idcolaboradoru`)
   - No requiere enviar `colaborador_id` en el body
   - Valida que el usuario tenga un colaborador asociado

2. **Validación de Acceso**
   - Verifica que la lección existe
   - Valida que el colaborador esté inscrito en la capacitación correspondiente
   - Retorna 403 si no tiene acceso a la lección

3. **Procesamiento de Respuestas**
   - Recibe array de IDs de respuestas: `{"respuestas": [17, 19]}`
   - Obtiene todas las preguntas de la lección
   - Compara respuestas del usuario con respuestas correctas
   - Guarda las respuestas en `respuestas_colaboradores`
   - Elimina respuestas anteriores si existen (permite reintentos)

4. **Cálculo de Aprobación**
   - Calcula porcentaje de acierto: `(correctas / total) * 100`
   - Lección aprobada si acierto >= 60%
   - Si aprobada: progreso = 100%, completada = True
   - Si no aprobada: progreso = 0%, completada = False

5. **Actualización de Progreso en Cascada**
   - Usa `actualizar_progreso_leccion()` de utils
   - Actualiza progreso de lección
   - Recalcula progreso de módulo automáticamente
   - Recalcula progreso de capacitación automáticamente

### Request Body

```json
{
  "respuestas": [17, 19]
}
```

**Campo:**
- `respuestas` (array, required): IDs de las respuestas seleccionadas por el usuario

### Response (200 OK)

```json
{
  "mensaje": "Cuestionario respondido exitosamente",
  "leccion_id": 1,
  "total_preguntas": 2,
  "respuestas_correctas": 2,
  "porcentaje_acierto": 100.0,
  "aprobada": true,
  "progreso_leccion": 100,
  "progreso_modulo": 75.5,
  "progreso_capacitacion": 45.3
}
```

### Respuestas de Error

**400 Bad Request - Sin colaborador asociado**
```json
{
  "error": "El usuario no tiene un colaborador asociado"
}
```

**400 Bad Request - Sin respuestas**
```json
{
  "error": "Se requiere al menos una respuesta"
}
```

**403 Forbidden - No inscrito**
```json
{
  "error": "No tienes acceso a esta lección. No estás inscrito en la capacitación correspondiente."
}
```

**404 Not Found - Lección no existe**
```json
{
  "error": "No encontrado."
}
```

**400 Bad Request - Lección sin preguntas**
```json
{
  "error": "Esta lección no tiene preguntas asociadas"
}
```

**500 Internal Server Error**
```json
{
  "error": "Error al procesar cuestionario: <detalle del error>"
}
```

## Lógica de Negocio

### 1. Validación de Inscripción
```python
# Verifica: Lección -> Módulo -> Capacitación
# Valida: Existe inscripción en capacitaciones_colaboradores
inscripcion = progresoCapacitaciones.objects.filter(
    colaborador=colaborador,
    capacitacion=capacitacion
).first()
```

### 2. Cálculo de Aprobación
```python
# Obtiene respuestas correctas (escorrecto = 1)
respuestas_correctas = Respuestas.objects.filter(
    idpregunta__in=preguntas,
    escorrecto=1
).values_list('id', flat=True)

# Intersección de respuestas del usuario con correctas
respuestas_correctas_usuario = set(respuestas_ids) & set(respuestas_correctas)
total_correctas = len(respuestas_correctas_usuario)

# Porcentaje
porcentaje_acierto = (total_correctas / total_preguntas) * 100

# Aprobación
aprobada = porcentaje_acierto >= 60  # 60% mínimo
```

### 3. Registro de Respuestas
```python
# Elimina respuestas anteriores (permite reintentos)
RespuestasColaboradores.objects.filter(
    idcolaborador=colaborador,
    idpregunta__in=preguntas
).delete()

# Guarda nuevas respuestas
for respuesta in respuestas_validas:
    RespuestasColaboradores.objects.create(
        idcolaborador=colaborador,
        idpregunta=respuesta.idpregunta,
        idrespuesta=respuesta
    )
```

### 4. Actualización de Progreso
```python
progreso = 100 if aprobada else 0

# Actualiza en cascada: lección -> módulo -> capacitación
progreso_data = actualizar_progreso_leccion(
    colaborador_id=colaborador.idcolaborador,
    leccion=leccion,
    progreso=progreso,
    completada=aprobada
)
```

## Modelo Agregado

```python
class RespuestasColaboradores(models.Model):
    idcolaborador = models.ForeignKey('usuarios.Colaboradores', models.DO_NOTHING, db_column='idColaborador')
    idpregunta = models.ForeignKey(PreguntasLecciones, models.DO_NOTHING, db_column='idPregunta')
    idrespuesta = models.ForeignKey(Respuestas, models.DO_NOTHING, db_column='idRespuesta')

    class Meta:
        managed = False
        db_table = 'respuestas_colaboradores'
```

## Ejemplo de Uso con Postman

### 1. Configurar Header
```
Authorization: Bearer <tu_token_jwt>
Content-Type: application/json
```

### 2. Request Body
```json
{
  "respuestas": [17, 19]
}
```

### 3. Escenarios

**Caso 1: Aprobó la lección (100% correcto)**
- Usuario responde 2 preguntas correctamente
- Resultado: `aprobada: true`, `progreso_leccion: 100`

**Caso 2: Aprobó con 60-99%**
- Usuario responde 3 de 5 preguntas correctas (60%)
- Resultado: `aprobada: true`, `progreso_leccion: 100`

**Caso 3: No aprobó (<60%)**
- Usuario responde 1 de 3 preguntas correctas (33.33%)
- Resultado: `aprobada: false`, `progreso_leccion: 0`

**Caso 4: Preguntas múltiples**
- Pregunta 1: respuesta única (ID: 17)
- Pregunta 2: múltiple opción (IDs: 19, 20)
- Request: `{"respuestas": [17, 19, 20]}`

## Testing

Script de prueba creado: `test_responder_cuestionario.py`

Para ejecutar:
```bash
python test_responder_cuestionario.py
```

### Tests incluidos:
1. Responder cuestionario exitosamente
2. Validación sin respuestas
3. Validación de lección no autorizada

## Notas Importantes

1. **Reintentos**: El sistema permite reintentos eliminando respuestas anteriores
2. **Preguntas múltiples**: Soporta preguntas con múltiples respuestas correctas
3. **Progreso automático**: No necesita llamar a otro endpoint para actualizar progreso
4. **Seguridad**: El colaborador_id se obtiene del token, no puede ser falsificado
5. **60% mínimo**: El umbral de aprobación es 60% de respuestas correctas

## Cambios en el Código

### views.py
- Implementada lógica completa de `ResponderCuestionarioView`
- Importado modelo `RespuestasColaboradores`

### models.py
- Agregado modelo `RespuestasColaboradores`

## Próximos Pasos Sugeridos

1. Configurar datos de prueba en la base de datos
2. Ejecutar script de testing
3. Validar con diferentes escenarios (aprobado/reprobado)
4. Probar con preguntas múltiples
5. Verificar cálculo de progreso en cascada
