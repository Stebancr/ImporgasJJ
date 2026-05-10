# Guía de Autenticación Bearer Token para Postman

## 1. Obtener el Token de Autenticación

### Endpoint: POST /auth/get-token/

**URL**: 
```
http://localhost:8000/auth/get-token/
```

**Método**: POST

**Headers**:
```
Content-Type: application/json
```

**Body (raw JSON)**:
```json
{
    "username": "tu_usuario",
    "password": "tu_contraseña"
}
```

**Respuesta Exitosa (200 OK)**:
```json
{
    "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
}
```

## 2. Usar el Token en las Pruebas

### En Postman:

1. **Copiar el token** de la respuesta anterior
2. **En cualquier request** que requiera autenticación:
   - Ir a la pestaña **Authorization**
   - Seleccionar tipo: **Bearer Token**
   - Pegar el token en el campo de texto

**O manualmente en Headers**:
```
Authorization: Bearer a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

## 3. Ejemplos de Requests Autenticados

### GET - Listar Capacitaciones (Solo Admin)

```
GET http://localhost:8000/capacitaciones/capacitaciones/

Headers:
Authorization: Bearer <tu_token>
```

**Respuesta (200 OK para admin)**:
```json
[
  {
    "id": 48,
    "titulo": "Capacitación inicial - Rutas del Valle",
    "descripcion": "...",
    "tipo": "CONOCIMIENTOS ORGANIZACIONALES",
    "estado": 1
  }
]
```

**Respuesta (403 Forbidden para usuario normal)**:
```json
{
  "detail": "Solo administradores pueden acceder a este recurso."
}
```

### POST - Crear Capacitación

```
POST http://localhost:8000/capacitaciones/crear-capacitacion/

Headers:
Authorization: Bearer <tu_token>
Content-Type: application/json

Body:
{
  "titulo": "Nueva Capacitación",
  "descripcion": "Descripción...",
  "tipo": "CONOCIMIENTOS",
  "fecha_inicio": "2025-01-20",
  "fecha_fin": "2025-02-20",
  "modulos": [],
  "colaboradores": []
}
```

### GET - Detalle de Capacitación

```
GET http://localhost:8000/capacitaciones/capacitacion/48/

Headers:
Authorization: Bearer <tu_token>
```

## 4. Usuarios de Prueba

### Crear usuarios de prueba en Django shell:

```bash
python manage.py shell
```

```python
from usuarios.models import Usuarios
from rest_framework.authtoken.models import Token

# Crear usuario admin
admin_user = Usuarios.objects.create_user(
    username='admin_test',
    email='admin@test.com',
    password='admin123',
    is_staff=1
)

# Crear token para admin
token_admin, _ = Token.objects.get_or_create(user=admin_user)
print(f"Token Admin: {token_admin.key}")

# Crear usuario normal
normal_user = Usuarios.objects.create_user(
    username='user_test',
    email='user@test.com',
    password='user123',
    is_staff=0
)

# Crear token para usuario normal
token_user, _ = Token.objects.get_or_create(user=normal_user)
print(f"Token Usuario: {token_user.key}")
```

## 5. Configuración en Postman

### Opción 1: Variable de Entorno

1. En Postman, ir a **Environments**
2. Crear nuevo environment: `LMS-Backend`
3. Agregar variable:
   ```
   Variable: token
   Value: <tu_token_aquí>
   ```

4. En los requests, usar:
   ```
   Authorization: Bearer {{token}}
   ```

### Opción 2: Pre-request Script

En la pestaña **Pre-request Script** del request o collection:

```javascript
// Script para obtener token automáticamente
const loginRequest = {
    url: 'http://localhost:8000/auth/get-token/',
    method: 'POST',
    header: {
        'Content-Type': 'application/json'
    },
    body: {
        mode: 'raw',
        raw: JSON.stringify({
            username: 'admin_test',
            password: 'admin123'
        })
    }
};

pm.sendRequest(loginRequest, function (err, response) {
    if (!err) {
        var jsonData = response.json();
        pm.environment.set('token', jsonData.token);
    }
});
```

## 6. Endpoints Protegidos por Autenticación

| Endpoint | Método | Autenticación | Permiso |
|----------|--------|---------------|---------|
| `/capacitaciones/capacitaciones/` | GET | Bearer Token | Solo Admin |
| `/capacitaciones/crear-capacitacion/` | POST | Bearer Token | Autenticado |
| `/capacitaciones/capacitacion/{id}/` | GET | Bearer Token | Autenticado |
| `/capacitaciones/progreso/registrar/` | POST | Bearer Token | Autenticado |
| `/capacitaciones/leccion/{id}/completar/` | POST | Bearer Token | Autenticado |
| `/capacitaciones/leccion/{id}/responder/` | POST | Bearer Token | Autenticado |
| `/capacitaciones/progreso/{colab_id}/` | GET | Bearer Token | Autenticado |
| `/capacitaciones/{id}/` | GET | Bearer Token | Autenticado |
| `/capacitaciones/mis-capacitaciones/` | GET | Bearer Token | Autenticado |
| `/capacitaciones/{id}/progreso/{colab_id}/` | GET | Bearer Token | Autenticado |
| `/capacitaciones/descargar-certificado/{id}/{cap_id}/` | GET | Bearer Token | Autenticado |

## 7. Solución de Problemas

### Error: "Authentication credentials were not provided"
- **Problema**: Falta el header Authorization
- **Solución**: Asegúrate de incluir `Authorization: Bearer <token>`

### Error: "Invalid token"
- **Problema**: Token inválido o expirado
- **Solución**: Obtén un nuevo token con POST /auth/get-token/

### Error: "Solo administradores pueden acceder a este recurso"
- **Problema**: Usuario no tiene permisos de admin
- **Solución**: Usa un usuario con is_staff=1

### Error: "User matching query does not exist"
- **Problema**: El usuario no existe
- **Solución**: Crea el usuario primero en Django shell

## 8. Configuración Completa en settings.py

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ]
}
```

## 9. URLs Disponibles

```
POST   http://localhost:8000/auth/get-token/        # Obtener token
GET    http://localhost:8000/capacitaciones/...      # API endpoints
```

---

**Nota**: Los tokens no expiran por defecto en TokenAuthentication. Para cambiar esto, configura `TOKEN_EXPIRE_TIMEDELTA` en settings.py si lo necesitas.
