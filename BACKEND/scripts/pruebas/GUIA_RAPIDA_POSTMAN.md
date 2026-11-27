# Guía Rápida: Cómo Usar Bearer Token en Postman

## Paso 1: Obtener el Token

### Endpoint: POST /auth/token/

**URL**: `http://localhost:8000/auth/token/`

**Método**: POST

**Headers**:
```
Content-Type: application/json
```

**Body (raw JSON)**:
```json
{
    "username": "admin",
    "password": "tu_contraseña"
}
```

**Respuesta Exitosa**:
```json
{
    "token": "<TOKEN_DE_PRUEBA_DESDE_ENTORNO>"
}
```

## Paso 2: Usar el Token en Postman

### Opción A: Pestaña Authorization (RECOMENDADO)

1. Abre tu request en Postman
2. Ve a la pestaña **Authorization**
3. En "Type" selecciona: **Bearer Token**
4. Pega el token que obtuviste en el campo "Token"
5. Envía el request

### Opción B: Header Manual

1. Ve a la pestaña **Headers**
2. Agrega un nuevo header:
   - **Key**: `Authorization`
   - **Value**: `Bearer abc123def456ghi789...` (reemplaza con tu token)
3. Envía el request

## Paso 3: Probar el Endpoint

**URL**: `http://localhost:8000/capacitaciones/capacitaciones/`

**Método**: GET

**Headers**:
```
Authorization: Bearer abc123def456ghi789...
```

**Respuesta Exitosa (200 OK)**:
```json
[
  {
    "id": 48,
    "titulo": "Capacitación inicial",
    "descripcion": "...",
    ...
  }
]
```

## Notas Importantes

⚠️ **IMPORTANTE**: El token debe ir precedido de la palabra "Bearer " (con espacio)

✅ **Correcto**: `Bearer abc123def456...`
❌ **Incorrecto**: `abc123def456...`
❌ **Incorrecto**: `Token abc123def456...`

## Verificar Usuario con tipousuario

Para ver el endpoint `/capacitaciones/capacitaciones/` necesitas que tu usuario tenga:
- `tipousuario = 1` (Administrador) O
- `tipousuario = 4` (Super Admin)

Si tu usuario tiene `tipousuario = 0` (Usuario Normal), obtendrás:
```json
{
    "detail": "Solo administradores pueden acceder a este recurso."
}
```

## Ejemplo Completo en Postman

### 1. Obtener Token
```
POST http://localhost:8000/auth/token/
Headers:
  Content-Type: application/json
Body:
  {
    "username": "admin",
    "password": "admin123"
  }

Response:
  {
    "token": "<TOKEN_DE_PRUEBA_DESDE_ENTORNO>"
  }
```

### 2. Usar Token
```
GET http://localhost:8000/capacitaciones/capacitaciones/
Headers:
  Authorization: Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

Response:
  [capacitaciones...]
```

## Solución de Problemas

### Error: "Authentication credentials were not provided."
**Causa**: Falta el header Authorization
**Solución**: Agrega el header `Authorization: Bearer <token>`

### Error: "Invalid token."
**Causa**: Token incorrecto o expirado
**Solución**: Obtén un nuevo token con POST /auth/token/

### Error: "Solo administradores pueden acceder a este recurso."
**Causa**: Usuario no tiene tipousuario = 1 o 4
**Solución**: Usa un usuario con permisos de admin o cambia el tipousuario en la base de datos

## Verificar tipousuario de tu Usuario

Puedes verificar en Django shell:
```python
python manage.py shell

from usuarios.models import Usuarios
user = Usuarios.objects.get(usuario='admin')
print(f"tipousuario: {user.tipousuario}")

# Si necesitas cambiar el tipousuario:
user.tipousuario = 1  # 1 = Admin
user.save()
```

## Configurar Variable de Entorno en Postman

1. Clic en el icono del ojo (👁️) en la esquina superior derecha
2. Clic en "Add" para crear un nuevo environment
3. Nombre: `LMS Backend`
4. Agregar variable:
   - **Variable**: `token`
   - **Initial Value**: (vacío)
   - **Current Value**: `tu_token_aquí`
5. Selecciona el environment "LMS Backend"
6. En tus requests usa: `Bearer {{token}}`

Esto te permite cambiar el token en un solo lugar para todos tus requests.
