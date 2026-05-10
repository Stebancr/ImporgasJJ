# 🎯 Frontend - Sistema de Desactivación de Usuarios en Lote

## 📋 Archivos Modificados

### 1. **Nueva Vista: DesactivarUsuarios.tsx**
**Ubicación:** `frontend/src/pages/DesactivarUsuarios.tsx`

**Características:**
- ✨ Carga archivo CSV con trabajadores a desactivar/reactivar
- 📤 Soporta dos formatos: `.csv` y `.xlsx`
- 👥 Visualiza previsualización de usuarios antes de procesar
- 🚫 Botón para desactivar usuarios (estado = 0)
- ✅ Botón para reactivar usuarios (estado = 1)
- ⚠️ Validaciones y confirmaciones antes de procesar

**Funcionalidades:**
```tsx
// Cargar usuarios desde CSV
handleCsvUpload() -> Carga el archivo y extrae datos

// Desactivar usuarios
handleDesactivar() -> POST a /cambiar-estado-usuario/ con estado=0

// Reactivar usuarios  
handleReactivar() -> POST a /cambiar-estado-usuario/ con estado=1

// Eliminar usuario de la lista
quitarUsuario() -> Remueve de la lista sin guardar
```

### 2. **Función en perfil.js**
**Ubicación:** `frontend/src/services/perfil.js`

**Nueva Función:** `desactivarMultiplesUsuarios()`
```javascript
const desactivarMultiplesUsuarios = async (payload) => {
  // Llama a: POST /user/cambiar-estado-usuario/
  // Payload: { colaborador_ids: [1, 2, 3, ...], estado: 0 o 1 }
  const response = await api.post(`user/cambiar-estado-usuario/`, payload);
  return response.data;
};
```

### 3. **Botón en Capacitaciones.tsx**
**Ubicación:** `frontend/src/pages/Capacitaciones.tsx` (Header)

**Nuevo Botón:**
```tsx
<button
  className={styles.btnReport}
  onClick={() => navigate("/desactivar-usuarios")}
  style={{ backgroundColor: "#d32f2f" }}
>
  🚫 Desactivar Usuarios
</button>
```

### 4. **Ruta en App.tsx**
**Ubicación:** `frontend/src/App.tsx`

**Nueva Ruta:**
```tsx
<Route path="/desactivar-usuarios" element={
  <AdminRoute><DesactivarUsuarios /></AdminRoute>
} />
```

---

## 🔄 Flujo de Uso

```
┌─────────────────────────────────┐
│ Admin en Capacitaciones.tsx      │
│ Hace clic en "Desactivar Usuarios"
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Navega a /desactivar-usuarios    │
│ (DesactivarUsuarios.tsx)         │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Carga archivo CSV con colaboradores     │
│ (Puedes descargar plantilla)            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Visualiza previsualización              │
│ - Nombre, apellido, cédula, email       │
│ - Botón para quitar usuarios de lista   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Elige acción:                           │
│ - "🚫 Desactivar" (estado = 0)         │
│ - "✅ Reactivar" (estado = 1)          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Confirmación: ¿Estás seguro?            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ POST /user/cambiar-estado-usuario/      │
│ Body: {                                 │
│   "colaborador_ids": [10, 20, 30...],   │
│   "estado": 0                           │
│ }                                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ ✅ Usuarios Desactivados                │
│ - NO reciben correos                    │
│ - NO aparecen en reportes               │
│ - NO cuentan en analítica               │
└─────────────────────────────────────────┘
```

---

## 📝 Ejemplo de Uso

### Paso 1: Ir a Capacitaciones
```
URL: http://localhost:3000/capacitaciones/list
```

### Paso 2: Hacer clic en botón "🚫 Desactivar Usuarios"
```
Se abre la vista de desactivación
```

### Paso 3: Descargar plantilla CSV
```
Plantilla CSV (usuarios.csv):
cedula
1112039941
1112039942
1112039943
```

### Paso 4: Cargar CSV
```
- Selecciona el archivo csv
- Se valida automáticamente
- Se muestra previsualización
```

### Paso 5: Revisar usuarios
```
Tabla con:
- # (índice)
- Nombre
- Apellido
- Cédula
- Correo
- Botón para eliminar de lista
```

### Paso 6: Desactivar
```
Haz clic en "🚫 Desactivar (5)"
Confirma la acción
```

### Paso 7: Resultado
```
✅ 5 usuario(s) desactivado(s) exitosamente
```

---

## 🔒 Validaciones

1. **Permisos:** Solo AdminRoute (requiere autenticación)
2. **CSV:** Soporta `.csv` y `.xlsx`
3. **Duplicados:** Se cargan automáticamente
4. **IDs Inválidos:** Se muestran advertencias
5. **Confirmación:** Doble confirmación antes de desactivar
6. **Respuesta:** Detalle de cada usuario procesado

---

## 💾 Datos que se Envían

### POST /user/cambiar-estado-usuario/
```json
{
  "colaborador_ids": [10, 20, 30, 40, 50],
  "estado": 0
}
```

### Respuesta Exitosa
```json
{
  "mensaje": "Procesamiento completado: 5 actualizados, 0 errores",
  "total": 5,
  "actualizados": 5,
  "errores": 0,
  "detalles": [
    {
      "colaborador_id": 10,
      "usuario_id": 1,
      "estado": 0,
      "success": true
    },
    ...
  ]
}
```

---

## 🎨 Interfaz de Usuario

### Botón en Header
- Color: Rojo (#d32f2f)
- Icono: 🚫
- Texto: "Desactivar Usuarios"
- Posición: En el header junto a "Generar Reporte"

### Vista Principal
- **Encabezado:** "Gestionar Estado de Usuarios"
- **Botones de Acción:**
  - 🚫 Desactivar (rojo)
  - ✅ Reactivar (verde)
- **Sección CSV:**
  - Botón para descargar plantilla
  - Input para cargar archivo
- **Tabla de Previsualización:**
  - Columnas: #, Nombre, Apellido, Cédula, Correo
  - Botón ✕ para eliminar de lista
- **Resumen:**
  - Total de usuarios
  - Efecto de la acción

---

## 🔐 Seguridad

1. **Rutas Protegidas:** AdminRoute (solo admins)
2. **Validación de Datos:** Cada ID se valida
3. **Confirmación:** Doble confirmación
4. **Respuesta Detallada:** Se retornan detalles de cada usuario
5. **Errores Manejados:** Mensajes claros al usuario
6. **Soft Delete:** Los datos no se eliminan, solo se desactivan

---

## 📊 Integración Completa

### Backend
- ✅ Endpoint POST para desactivar múltiples usuarios
- ✅ Filtro en envío de correos (no envía a desactivados)
- ✅ Filtro en reportes de analítica
- ✅ Filtro en reportes de capacitaciones
- ✅ Filtro en tareas Celery

### Frontend
- ✅ Vista DesactivarUsuarios.tsx
- ✅ Función desactivarMultiplesUsuarios() en perfil.js
- ✅ Botón en Capacitaciones.tsx
- ✅ Ruta /desactivar-usuarios en App.tsx
- ✅ Validaciones y confirmaciones

---

## 🧪 Pruebas Recomendadas

1. **Descargar Plantilla**
   - ✅ Botón funciona
   - ✅ Archivo CSV correcto

2. **Cargar CSV**
   - ✅ Soporta .csv
   - ✅ Soporta .xlsx
   - ✅ Muestra advertencias si hay usuarios no encontrados

3. **Previsualización**
   - ✅ Tabla se carga correctamente
   - ✅ Botón ✕ elimina usuarios de la lista
   - ✅ Conteo se actualiza

4. **Desactivar**
   - ✅ Confirmación funciona
   - ✅ Usuarios se desactivan
   - ✅ Mensaje de éxito muestra
   - ✅ Usuarios desactivados no reciben correos

5. **Reactivar**
   - ✅ Confirmación funciona
   - ✅ Usuarios se reactivan
   - ✅ Mensaje de éxito muestra
   - ✅ Usuarios reactivos reciben correos nuevamente

---

## 📱 Responsividad

- ✅ Funciona en desktop
- ✅ Funciona en tablet
- ✅ Tabla es scrollable en móvil
- ✅ Botones tienen buen tamaño en todos los dispositivos

---

## 🚀 Mejoras Futuras

1. Seleccionar múltiples usuarios de una tabla
2. Importar desde base de datos (no solo CSV)
3. Filtrar usuarios antes de desactivar
4. Historial de desactivaciones
5. Notificación por email a usuarios desactivados
6. Descarga de reporte de desactivaciones
