# Configuración de Permisos basados en tipousuario

## Resumen

Se han actualizado todos los permisos del sistema para usar el campo **`tipousuario`** del modelo Usuarios en lugar de `is_staff`. Esto proporciona un control de acceso más granular y alineado con la estructura de la base de datos.

## Tipos de Usuario (tipousuario)

| Valor | Tipo | Descripción | Acceso |
|-------|------|-------------|--------|
| **0** | Usuario Normal | Colaborador estándar | Acceso básico |
| **1** | Administrador | Admin completo | Acceso completo (GET, POST, PUT, DELETE) |
| **2** | Lectura Admin | Admin con permisos de lectura | Solo GET |
| **3** | Usuario Especial | Permisos especiales personalizados | Según configuración |
| **4** | Super Admin | Administrador supremo | Acceso total sin restricciones |

## Clases de Permisos Actualizadas

### 1. IsAdminUser
**Permite acceso a**: Administradores (1) y Super Admin (4)
```python
permission_classes = [IsAdminUser]
```
- ✅ tipousuario = 1 (Admin)
- ✅ tipousuario = 4 (Super Admin)
- ❌ Todos los demás

**Uso**: Endpoints que solo admins pueden usar (crear, editar, eliminar)

### 2. IsLecturaAdmin
**Permite acceso a**: Admin de Lectura (2), Admin (1) y Super Admin (4)
```python
permission_classes = [IsLecturaAdmin]
```
- ✅ GET: tipousuario = 1, 2, 4
- ✅ POST/PUT/DELETE: tipousuario = 1, 4
- ❌ Usuarios normales (0)

**Uso**: Endpoints donde usuarios de lectura pueden ver pero no modificar

### 3. IsUsuarioEspecial
**Permite acceso a**: Usuarios Especiales (3) y Super Admin (4)
```python
permission_classes = [IsUsuarioEspecial]
```
- ✅ tipousuario = 3 (Usuario Especial)
- ✅ tipousuario = 4 (Super Admin)
- ❌ Todos los demás

**Uso**: Funcionalidades específicas para usuarios con permisos especiales

### 4. IsAdminOrLecturaAdmin
**Permite acceso a**: Admin (1), Lectura Admin (2) y Super Admin (4)
```python
permission_classes = [IsAdminOrLecturaAdmin]
```
- ✅ GET: tipousuario = 1, 2, 4
- ✅ POST/PUT/DELETE: tipousuario = 1, 4
- ❌ Usuarios normales (0)

**Uso**: Endpoints administrativos con diferentes permisos por método HTTP

### 5. IsNormalUserOrAdmin
**Permite acceso a**: Usuarios normales (0), Admin (1) y Super Admin (4)
```python
permission_classes = [IsNormalUserOrAdmin]
```
- ✅ tipousuario = 0, 1, 4
- ❌ Solo usuarios especiales sin admin

**Uso**: Endpoints accesibles para colaboradores y administradores

### 6. IsSuperUserOrAdmin
**Permite acceso a**: Admin (1) y Super Admin (4)
```python
permission_classes = [IsSuperUserOrAdmin]
```
- ✅ tipousuario = 1, 4
- ❌ Todos los demás

**Uso**: Similar a IsAdminUser, enfoque en super privilegios

### 7. IsAuthenticatedUser (NUEVO)
**Permite acceso a**: Cualquier usuario autenticado
```python
permission_classes = [IsAuthenticatedUser]
```
- ✅ Todos los usuarios autenticados
- ❌ Usuarios no autenticados

**Uso**: Endpoints que solo requieren estar logueado

### 8. IsSuperAdmin (NUEVO)
**Permite acceso a**: Solo Super Admin (4)
```python
permission_classes = [IsSuperAdmin]
```
- ✅ tipousuario = 4
- ❌ Todos los demás (incluido admin=1)

**Uso**: Endpoints críticos del sistema solo para super administradores

## Propiedades Agregadas al Modelo Usuarios

Para compatibilidad con Django Admin y el sistema de autenticación:

```python
@property
def is_staff(self):
    """Retorna True si es admin o super admin"""
    return self.tipousuario in [1, 4]

@property
def is_superuser(self):
    """Retorna True si es super admin"""
    return self.tipousuario == 4

@property
def is_active(self):
    """Retorna True si el usuario está activo"""
    return self.estadousuario == 1

def has_perm(self, perm, obj=None):
    """Permisos para admin de Django"""
    return self.tipousuario in [1, 4]

def has_module_perms(self, app_label):
    """Permisos de módulos para admin de Django"""
    return self.tipousuario in [1, 4]
```

## Ejemplo de Uso en Views

### Endpoint Solo para Admin
```python
from usuarios.permissions import IsAdminUser

class CapacitacionesView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Solo usuarios con tipousuario=1 o 4 pueden acceder
        ...
```

### Endpoint con Diferentes Permisos por Método
```python
from usuarios.permissions import IsAdminOrLecturaAdmin

class ReportesView(APIView):
    permission_classes = [IsAdminOrLecturaAdmin]
    
    def get(self, request):
        # tipousuario 1, 2, 4 pueden ver
        ...
    
    def post(self, request):
        # Solo tipousuario 1, 4 pueden crear
        ...
```

### Endpoint Accesible para Usuarios Normales
```python
from usuarios.permissions import IsNormalUserOrAdmin

class MisCapacitacionesView(APIView):
    permission_classes = [IsNormalUserOrAdmin]
    
    def get(self, request):
        # tipousuario 0, 1, 4 pueden acceder
        ...
```

## Archivos Modificados

1. ✅ **usuarios/permissions.py** - Todas las clases actualizadas para usar `tipousuario`
2. ✅ **usuarios/models.py** - Agregadas propiedades `is_staff`, `is_superuser`, `is_active`, etc.
3. ✅ **create_test_tokens.py** - Script actualizado para crear usuarios de prueba

## Testing con Postman

### Crear Usuarios de Prueba
```bash
python create_test_tokens.py
```

Este script crea:
- **admin_test** (tipousuario=1)
- **superadmin_test** (tipousuario=4)
- **user_test** (tipousuario=0)
- **lectura_admin_test** (tipousuario=2)

### Obtener Token
```bash
POST http://localhost:8000/auth/get-token/
Body: {
    "username": "admin_test",
    "password": "admin123"
}
```

### Usar Token
```bash
GET http://localhost:8000/capacitaciones/capacitaciones/
Headers:
  Authorization: Bearer <token>
```

## Matriz de Permisos por Endpoint

| Endpoint | Normal (0) | Admin (1) | Lectura (2) | Especial (3) | Super (4) |
|----------|------------|-----------|-------------|--------------|-----------|
| GET /capacitaciones/ | ❌ | ✅ | ❌ | ❌ | ✅ |
| POST /crear-capacitacion/ | ❌ | ✅ | ❌ | ❌ | ✅ |
| GET /capacitacion/{id}/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GET /mis-capacitaciones/ | ✅ | ✅ | ✅ | ✅ | ✅ |
| POST /progreso/registrar/ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Mensajes de Error por Permiso

| Clase | Mensaje |
|-------|---------|
| IsAdminUser | "Solo administradores pueden acceder a este recurso." |
| IsLecturaAdmin | "No tiene permiso para realizar esta acción." |
| IsUsuarioEspecial | "Este usuario no tiene permisos suficientes." |
| IsSuperAdmin | "Solo super administradores pueden acceder a este recurso." |
| IsAuthenticatedUser | "Debe estar autenticado para acceder a este recurso." |

## Migración de Código Existente

### Antes (usando is_staff)
```python
if request.user.is_staff == 1:
    # hacer algo
```

### Después (usando tipousuario)
```python
if request.user.tipousuario == 1:
    # hacer algo
```

### Compatibilidad
Las propiedades `is_staff` y `is_superuser` siguen disponibles para compatibilidad con Django Admin:
```python
if request.user.is_staff:  # True si tipousuario in [1, 4]
    # hacer algo
```

---

**Estado**: ✅ CONFIGURACIÓN COMPLETA
**Fecha**: 2025-01-04
**Sistema**: Permisos basados en tipousuario
**Compatibilidad**: Django Admin ✅ | REST Framework ✅
