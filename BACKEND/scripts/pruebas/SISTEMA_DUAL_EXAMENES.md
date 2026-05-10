# Sistema Dual de Exámenes - Documentación Completa

## Resumen de la Implementación ✅

Se ha implementado un sistema completo que permite manejar **dos tipos de exámenes independientes**:
- **INGRESO**: Exámenes para nuevos colaboradores
- **PERIODICO**: Exámenes periódicos de SST

El sistema ahora es flexible y permite que cada trabajador tenga un conjunto diferente de exámenes según su tipo.

---

## Cambios Realizados

### 1. Modelo de Base de Datos

#### Nuevos Campos en `CorreoExamenEnviado`
```python
tipo_examen = CharField(
    choices=[("INGRESO", "Examen de Ingreso"), ("PERIODICO", "Examen Periódico")],
    default="INGRESO"
)
```

#### Nuevos Campos en `RegistroExamenes`
```python
tipo_examen = CharField(
    choices=[("INGRESO", "Examen de Ingreso"), ("PERIODICO", "Examen Periódico")],
    default="INGRESO"
)
examenes_asignados = TextField()  # Lista de exámenes separados por coma
```

#### Nuevo Modelo: `ExamenTrabajador`
Tabla de relación muchos-a-muchos entre `RegistroExamenes` y `Examen`:

```python
class ExamenTrabajador(models.Model):
    registro_examen = ForeignKey(RegistroExamenes)
    examen = ForeignKey(Examen)
    fecha_asignacion = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('registro_examen', 'examen')]
```

**Ventajas:**
- Flexibilidad total para asignar exámenes
- Relación uno-a-muchos sin depender de la configuración de cargo
- Posibilidad de auditar qué exámenes se asignaron y cuándo

---

## Formato CSV Actualizado

### Estructura de Columnas (requeridas todas)

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| Empresa | string | Nombre de empresa | CONSORCIO PEAJES 2526 |
| Unidad | string | Unidad operativa | PEAJES Y BASCULAS |
| Proyecto | string | Proyecto | CONSORCIO PEAJES 2526 |
| Centro | string | Centro de trabajo | ADMINISTRACION |
| Nombre | string | Nombre del trabajador | Juan Perez |
| CC | string | Cédula del trabajador | 123456789 |
| Ciudad | string | Ciudad | Bogota |
| Cargo | string | Cargo del trabajador | ASISTENTE ADMINISTRATIVO |
| **TipoExamen** | enum | INGRESO o PERIODICO | INGRESO |
| **Examenes** | string | Exámenes separados por coma | AUDIOMETRIA,OPTOMETRIA |

### Ejemplo de CSV Válido

```csv
Empresa;Unidad;Proyecto;Centro;Nombre;CC;Ciudad;Cargo;TipoExamen;Examenes
CONSORCIO PEAJES 2526;PEAJES Y BASCULAS;CONSORCIO PEAJES 2526;ADMINISTRACION;Juan Perez;123456789;Bogota;ASISTENTE ADMINISTRATIVO;INGRESO;AUDIOMETRIA,OPTOMETRIA
CONSORCIO PEAJES 2526;PEAJES Y BASCULAS;CONSORCIO PEAJES 2526;ADMINISTRACION;Maria Garcia;987654321;Medellin;ASISTENTE ADMINISTRATIVO;PERIODICO;ESPIROMETRIA,GLICEMIA
```

**Notas:**
- Delimitador: `;` (punto y coma) o `,` (coma) - **se detecta automáticamente**
- Encoding soportados: UTF-8, Latin-1, CP1252, ISO-8859-1
- Los exámenes deben existir y estar activos en la base de datos
- El tipo de examen debe ser exactamente `INGRESO` o `PERIODICO`

---

## Lógica de Procesamiento

### 1. Validación de CSV

```python
# En EnviarCorreoMasivoView.post()

# Paso 1: Detectar encoding automáticamente
encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
for enc in encodings:
    try:
        csv_content = archivo.read().decode(enc)
        break
    except UnicodeDecodeError:
        continue

# Paso 2: Detectar delimitador automáticamente
sniffer = csv.Sniffer()
delimiter = sniffer.sniff(csv_content[:1024]).delimiter

# Paso 3: Validar columnas requeridas
required_fields = [
    'empresa', 'unidad', 'proyecto', 'centro', 
    'nombre', 'cc', 'ciudad', 'cargo',
    'tipoexamen', 'examenes'  # Nuevas
]
```

### 2. Procesamiento de Líneas

Para cada línea del CSV:

```python
# Validar tipo de examen
if tipo_examen not in ['INGRESO', 'PERIODICO']:
    raise ValidationError(f"Tipo inválido: {tipo_examen}")

# Procesar exámenes
examenes = [e.strip() for e in examenes_str.split(',')]

# Validar que existan en BD
for exam_nombre in examenes:
    examen = Examen.objects.get(
        nombre=exam_nombre,
        estado_examen=True
    )
    # Si no existe → error 400

# Guardar información para procesamiento posterior
trabajadores_validos.append({
    'cc': cc,
    'nombre': nombre,
    'tipo_examen': tipo_examen,
    'examenes_nombres': examenes,
    # ... otros campos
})
```

### 3. Creación de Registros en BD

```python
# Paso 1: Crear RegistroExamenes
registros_creados = []
for trab in trabajadores_validos:
    reg = RegistroExamenes.objects.create(
        uuid_trabajador=uuid.uuid4(),
        uuid_lote=uuid_lote,
        nombre_trabajador=trab['nombre'],
        cc_trabajador=trab['cc'],
        tipo_examen=trab['tipo_examen'],  # NUEVO
        examenes_asignados=','.join(trab['examenes_nombres']),  # NUEVO
        # ... otros campos
    )
    registros_creados.append(reg)

# Paso 2: Crear relaciones ExamenTrabajador (muchos-a-muchos)
examen_trabajador_batch = []
for reg in registros_creados:
    for exam_nombre in trabajadores_validos[...]['examenes_nombres']:
        examen = Examen.objects.get(nombre=exam_nombre)
        examen_trabajador_batch.append(
            ExamenTrabajador(
                registro_examen=reg,
                examen=examen,
                fecha_asignacion=now()
            )
        )

# bulk_create con ignore_conflicts
ExamenTrabajador.objects.bulk_create(
    examen_trabajador_batch,
    ignore_conflicts=True
)
```

---

## Generación de Excel

### Método: `_generar_excel_por_tipo()`

Genera un Excel con **hojas separadas por tipo de examen**:

```python
def _generar_excel_por_tipo(self, trabajadores, examenes_por_lote):
    """
    Genera Excel con separación por tipo de examen (INGRESO vs PERIODICO)
    """
    
    # Agrupar trabajadores por tipo
    trabajadores_por_tipo = {}
    for trab in trabajadores:
        tipo = trab['tipo_examen']
        if tipo not in trabajadores_por_tipo:
            trabajadores_por_tipo[tipo] = []
        trabajadores_por_tipo[tipo].append(trab)
    
    # Crear workbook con hojas separadas
    wb = Workbook()
    wb.remove(wb.active)  # Eliminar hoja por defecto
    
    for tipo_examen in ['INGRESO', 'PERIODICO']:
        if tipo_examen not in trabajadores_por_tipo:
            continue
        
        ws = wb.create_sheet(title=tipo_examen)
        
        # Obtener exámenes solo del tipo actual
        examenes_tipo = [e for e in examenes_por_lote 
                         if e['tipo'] == tipo_examen]
        
        # Crear cabeceras (nombre + examenes del tipo)
        headers = ['Nombre', 'CC', 'Cargo', 'Centro'] + \
                  [e['nombre'] for e in examenes_tipo]
        
        # Agregar datos (trabajadores del tipo)
        trab_tipo = trabajadores_por_tipo[tipo_examen]
        # ... llenar filas ...
```

**Ejemplo de output:**

```
Excel "INGRESO":
  Nombre | CC | Cargo | Centro | AUDIOMETRIA | OPTOMETRIA
  Juan Perez | 123456789 | ASISTENTE | ADMIN | X | X

Excel "PERIODICO":
  Nombre | CC | Cargo | Centro | ESPIROMETRIA | GLICEMIA
  Maria Garcia | 987654321 | ASISTENTE | ADMIN | X | X
```

---

## Respuesta del Endpoint

### POST `/examenes/correo/enviar-masivo/`

**Request:**
```
Content-Type: multipart/form-data
archivo_csv: [archivo CSV con nuevas columnas]
```

**Response 201 OK:**
```json
{
  "estado": "success",
  "uuid_correo": "abc12345-20260104112147",
  "total_trabajadores": 2,
  "trabajadores_por_tipo": {
    "INGRESO": 1,
    "PERIODICO": 1
  },
  "examenes_asignados": {
    "AUDIOMETRIA": 1,
    "OPTOMETRIA": 1,
    "ESPIROMETRIA": 1,
    "GLICEMIA": 1
  },
  "mensaje": "Trabajadores procesados correctamente"
}
```

**Response 400 - Error de Validación:**
```json
{
  "error": "Línea 3: Tipo examen 'INVALIDO' no reconocido. Debe ser INGRESO o PERIODICO"
}
```

```json
{
  "error": "Línea 3: Examen 'RADIOGRAFIA' no encontrado o no está activo"
}
```

---

## Características Implementadas

✅ **Auto-detección de encoding**: Soporta UTF-8, Latin-1, CP1252, ISO-8859-1  
✅ **Auto-detección de delimitador**: Detecta automáticamente `;` o `,`  
✅ **Validación de tipos**: Verifica que tipo_examen sea INGRESO o PERIODICO  
✅ **Validación de exámenes**: Verifica que existan en BD y estén activos  
✅ **Relaciones flexibles**: ExamenTrabajador permite cualquier combinación  
✅ **Excel por tipo**: Genera hojas separadas para INGRESO y PERIODICO  
✅ **Logging detallado**: DEBUG logging del proceso de CSV  
✅ **Manejo de errores**: Retorna errores claros en línea específica  
✅ **Batch creation**: Optimizado con bulk_create  

---

## Errores Comunes

### Error: "Examen 'XXX' no encontrado"
**Causa**: El nombre del examen en el CSV no coincide exactamente con el de la BD.
**Solución**: 
- Verificar que el nombre sea exactamente igual (mayúsculas/minúsculas)
- Consultar exámenes disponibles:
  ```python
  Examen.objects.filter(estado_examen=True).values('nombre')
  ```

### Error: "Tipo examen 'XXX' no reconocido"
**Causa**: El valor de TipoExamen no es INGRESO ni PERIODICO.
**Solución**: Usar solo estos dos valores (case-insensitive internamente se convierte a mayúsculas).

### Error: "Columna 'tipoexamen' no encontrada"
**Causa**: El CSV no incluye las columnas TipoExamen y Examenes.
**Solución**: Actualizar el CSV a incluir ambas columnas.

---

## Testing

Se incluye `test_nuevo_formato_completo.py` que valida:

1. ✓ Creación de CSV con dos tipos
2. ✓ Parsing correcto del encoding/delimitador
3. ✓ Validación de tipos y exámenes
4. ✓ Creación de RegistroExamenes
5. ✓ Creación de relaciones ExamenTrabajador
6. ✓ Separación correcta en lote MIXTO
7. ✓ Generación de respuesta 201 con datos correctos

**Ejecutar test:**
```bash
python test_nuevo_formato_completo.py
```

---

## Migración de Datos (si aplica)

La migración `0006_examentrabajador_and_more.py`:
- ✅ Crea tabla `examenes_examentrabajador`
- ✅ Agrega campo `tipo_examen` a `CorreoExamenEnviado`
- ✅ Agrega campos `tipo_examen` y `examenes_asignados` a `RegistroExamenes`

**Aplicar:**
```bash
python manage.py migrate examenes 0006
```

---

## Notas Técnicas

- **Performance**: bulk_create optimiza inserciones de ExamenTrabajador
- **Constraint único**: Evita duplicados (registro_examen, examen)
- **Foreign Keys**: Mantiene integridad referencial con Examen y RegistroExamenes
- **índices**: tipo_examen tiene índice DB para búsquedas rápidas
- **Timestamp**: fecha_asignacion se establece automáticamente

---

## Próximas Mejoras (Opcionales)

- [ ] API endpoint para consultar exámenes disponibles por tipo
- [ ] Validación pre-carga de CSV (vista de preview)
- [ ] Reporte de exámenes asignados por trabajador
- [ ] Cambio de exámenes posterior a creación
- [ ] Auditoría de cambios en asignaciones

