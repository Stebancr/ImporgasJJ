# Implementación: Reporte de Usuarios en Excel

## Descripción
Se ha implementado un nuevo endpoint y funcionalidad para descargar un reporte completo de todos los colaboradores en formato Excel (.xlsx).

## Cambios Realizados

### Backend (Django)

#### 1. **Vista: ReporteUsuariosView** (`backend/usuarios/views.py`)
- **Método GET**: Genera un archivo Excel con todos los colaboradores
- **Permisos**: Requiere autenticación y permisos de SuperAdmin o AdminUser
- **Funcionalidad**:
  - Obtiene todos los colaboradores (activos e inactivos)
  - Incluye relaciones con empresa, unidad, proyecto, centro OP, cargo, nivel y región
  - Genera estilos visuales en el Excel (headers azules, bordes, ancho de columnas)

#### 2. **Columnas del Reporte Excel**
1. Cédula
2. Empresa
3. Unidad
4. Proyecto
5. Centro OP
6. Nombre
7. Apellido
8. Correo
9. Celular
10. Región
11. Nivel
12. Cargo
13. Estado Usuario (Activado/Desactivado)

#### 3. **Importaciones Agregadas** (`backend/usuarios/views.py`)
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from django.http import FileResponse
```

#### 4. **Ruta URL**
```python
path("reporte-usuarios/", views.ReporteUsuariosView.as_view(), name="reporte-usuarios")
```
- Ubicación: `backend/usuarios/urls.py` (ya estaba definida)

### Frontend (React/TypeScript)

#### 1. **Función en perfil.js** (`frontend/src/services/perfil.js`)
```javascript
const descargarReporteUsuarios = async () => {
  // Realiza petición GET al endpoint
  // Descarga automáticamente el archivo Excel
  // Limpia recursos temporales (blob, URLs)
}
```

#### 2. **Declaración TypeScript** (`frontend/src/services/perfil.ts`)
```typescript
descargarReporteUsuarios(): Promise<any>;
```

#### 3. **Botón en Usuarios.tsx** (`frontend/src/pages/Usuarios.tsx`)
- **Ubicación**: En el header junto a "Registrar Masivo" y "Desactivar Usuarios"
- **Estilo**: Botón azul (#2196F3) con icono 📊
- **Título**: "Descargar Reporte"
- **Funcionalidad**: Llama a `handleDescargarReporte()`

#### 4. **Manejador de evento** (`frontend/src/pages/Usuarios.tsx`)
```typescript
const handleDescargarReporte = async () => {
  try {
    setLoading(true);
    await (Perfil as any).descargarReporteUsuarios();
    setSuccess("Reporte descargado correctamente");
    setTimeout(() => setSuccess(null), 3000);
  } catch (err: any) {
    setError(err?.response?.data?.error || "Error al descargar el reporte");
    setTimeout(() => setError(null), 3000);
  } finally {
    setLoading(false);
  }
};
```

## Flujo de Uso

1. **Usuario Admin accede a la página de Usuarios**
2. **Hace clic en el botón "📊 Descargar Reporte"**
3. **Se realiza petición GET a `/usuarios/reporte-usuarios/`**
4. **Backend genera Excel con todos los colaboradores**
5. **Navegador descarga automáticamente `Reporte_Usuarios.xlsx`**
6. **Mensaje de éxito se muestra durante 3 segundos**

## Características del Excel Generado

- **Encabezados**: Fondo azul (#4472C4) con texto blanco y negrita
- **Bordes**: Todas las celdas tienen bordes finos
- **Alineación**: Contenido alineado a la izquierda y verticalmente centrado
- **Ajuste de Texto**: Los encabezados tienen ajuste de texto automático
- **Ancho de Columnas**: Optimizado para cada tipo de datos
- **Datos**: Todos los colaboradores (sin filtrar por estado)

## Dependencias Requeridas

### Backend
- `openpyxl` (ya incluido en `requirements.txt`)

### Frontend
- `axios` (ya está disponible)

## Permisos Requeridos

- **SuperAdmin** (tipousuario = 4) ✅
- **AdminUser** (tipousuario = 1) ✅

## Posibles Mejoras Futuras

1. Filtros adicionales (por fecha, región, estado)
2. Múltiples formatos de exportación (PDF, CSV)
3. Campos personalizables en el reporte
4. Gráficos en el Excel
5. Validación de datos antes de exportar
