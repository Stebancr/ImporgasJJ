# 🧪 Guía de Pruebas - Chatbot Ollama Integrado

## Pruebas Básicas del Bot

### 1. Pregunta sobre Horarios

```powershell
$body = '{"message":"Cual es el horario de atencion?"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "bot"`
- `needs_agent: false`
- Respuesta con horarios de atención

### 2. Pregunta sobre Productos

```powershell
$body = '{"message":"Que productos de tuberias tienen disponibles?"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "bot"`
- `needs_agent: false`
- Lista de productos disponibles

### 3. Pregunta sobre Servicios

```powershell
$body = '{"message":"Que servicios ofrecen?"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "bot"`
- `needs_agent: false`
- Descripción de servicios (instalación, mantenimiento, etc.)

---

## Pruebas de Derivación a Agente

### 4. Intención de Compra

```powershell
$body = '{"message":"Quiero comprar tuberia de gas"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "waiting"`
- `needs_agent: true`
- Mensaje de transferencia a asesor

### 5. Solicitud de Cotización

```powershell
$body = '{"message":"Necesito una cotizacion para 50 metros de tuberia"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "waiting"`
- `needs_agent: true`

### 6. Solicitud de Servicio Técnico

```powershell
$body = '{"message":"Necesito instalar un calentador de gas"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "waiting"`
- `needs_agent: true`

### 7. Hablar con Asesor

```powershell
$body = '{"message":"Quiero hablar con un asesor"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- `status: "waiting"`
- `needs_agent: true`

---

## Pruebas de Continuación de Conversación

### 8. Mantener Contexto (Múltiples Mensajes)

**Mensaje 1:**
```powershell
$body = '{"message":"Hola, necesito informacion sobre tuberias"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';

# Guardar el session_id
$sessionId = $result.session_id
Write-Host "Session ID: $sessionId"
```

**Mensaje 2 (usando la misma sesión):**
```powershell
$body = "{`"message`":`"Que diametros tienen?`",`"session_id`":$sessionId}";
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Mensaje 3:**
```powershell
$body = "{`"message`":`"Y los precios?`",`"session_id`":$sessionId}";
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- El bot mantiene el contexto de la conversación
- Las respuestas son coherentes con los mensajes anteriores

---

## Pruebas de Historial de Mensajes

### 9. Obtener Todos los Mensajes de una Sesión

```powershell
# Usar el session_id de las pruebas anteriores
$sessionId = 5  # Reemplazar con un ID real

$result = Invoke-RestMethod `
  -Uri "http://localhost/api/crm-chat/bot/sessions/$sessionId/messages/" `
  -Method Get;

$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- Lista de todos los mensajes de la sesión
- Información del estado de la sesión
- Nombre del agente (si está activa)

### 10. Polling de Nuevos Mensajes

```powershell
# Obtener mensajes después del mensaje ID 20
$sessionId = 5  # Reemplazar con un ID real
$lastMessageId = 20

$result = Invoke-RestMethod `
  -Uri "http://localhost/api/crm-chat/bot/sessions/$sessionId/messages/?after=$lastMessageId" `
  -Method Get;

$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- Solo mensajes nuevos (ID > 20)
- Lista vacía si no hay mensajes nuevos

---

## Pruebas con Datos de Usuario

### 11. Enviar Mensaje con Nombre de Usuario

```powershell
$body = '{
  "message":"Hola, necesito ayuda",
  "user_name":"Juan Perez",
  "user_email":"juan@example.com"
}';

$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';

$result | ConvertTo-Json -Depth 5
```

**Resultado esperado:**
- Sesión creada con el nombre del usuario
- El nombre aparece en los mensajes

---

## Pruebas de Integración con Frontend

### 12. Probar desde el Navegador

1. Abrir el frontend del ecommerce: `http://localhost:81`
2. Buscar el botón flotante del chatbot (esquina inferior derecha)
3. Click para abrir el chat
4. Enviar mensaje de prueba: "¿Cuál es el horario?"
5. Verificar que el bot responde

### 13. Probar Escalamiento a Agente

1. En el chat del frontend, escribir: "Quiero comprar tubería"
2. Verificar que aparece mensaje de transferencia
3. Verificar que el indicador cambia de "🤖 Bot" a "⏳ Esperando asesor"

### 14. Probar desde DevTools del Navegador

```javascript
// Abrir consola del navegador (F12)
const response = await fetch('/api/crm-chat/bot/chat/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json; charset=utf-8'
  },
  body: JSON.stringify({
    message: 'Hola, necesito informacion',
    user_name: 'Test User'
  })
});

const data = await response.json();
console.log(data);
```

---

## Pruebas de Rendimiento

### 15. Enviar Múltiples Mensajes Rápidamente

```powershell
# Script para enviar 10 mensajes
for ($i=1; $i -le 10; $i++) {
  $body = "{`"message`":`"Mensaje de prueba $i`"}";
  $result = Invoke-RestMethod `
    -Uri 'http://localhost/api/crm-chat/bot/chat/' `
    -Method Post `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
    -ContentType 'application/json; charset=utf-8';
  
  Write-Host "Mensaje $i enviado - Session: $($result.session_id)"
  Start-Sleep -Seconds 1
}
```

**Verificar:**
- Todos los mensajes son procesados
- No hay errores
- El bot responde a todos

---

## Pruebas de Errores

### 16. Mensaje Vacío

```powershell
$body = '{"message":""}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
```

**Resultado esperado:**
- Error 400 Bad Request
- Mensaje: "El mensaje no puede estar vacío"

### 17. Sesión Inválida

```powershell
$body = '{"message":"Hola","session_id":99999}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
```

**Resultado esperado:**
- Crea una nueva sesión (ignora el ID inválido)
- Responde normalmente

---

## Verificación de Contenedores

### 18. Verificar Estado de Ollama

```powershell
# Ver si Ollama está corriendo
docker ps | Select-String "ollama"

# Ver logs de Ollama
docker logs ollama --tail 50

# Probar Ollama directamente
docker exec -it ollama ollama run qwen2.5:1.5b "Hola, como estas?"
```

### 19. Verificar Estado del Backend

```powershell
# Ver si el backend está corriendo
docker ps | Select-String "backend"

# Ver logs del backend
docker logs backend --tail 50

# Verificar conectividad entre contenedores
docker exec backend ping -c 3 ollama
```

### 20. Verificar Red de Docker

```powershell
# Ver contenedores en la red compartida
docker network inspect shared_net --format '{{range .Containers}}{{.Name}} {{end}}'
```

**Resultado esperado:**
- Deben aparecer: `backend`, `ollama`, `postgres`, `nginx`

---

## Script de Prueba Completo

```powershell
# Guardar como test-chatbot.ps1

Write-Host "=== Prueba 1: Pregunta Simple ===" -ForegroundColor Cyan
$body = '{"message":"Cual es el horario?"}';
$r1 = Invoke-RestMethod -Uri 'http://localhost/api/crm-chat/bot/chat/' -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8';
Write-Host "Status: $($r1.status) | Needs Agent: $($r1.needs_agent)"
Write-Host "Respuesta: $($r1.message)`n"

Write-Host "=== Prueba 2: Intencion de Compra ===" -ForegroundColor Cyan
$body = '{"message":"Quiero comprar tuberia"}';
$r2 = Invoke-RestMethod -Uri 'http://localhost/api/crm-chat/bot/chat/' -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8';
Write-Host "Status: $($r2.status) | Needs Agent: $($r2.needs_agent)"
Write-Host "Respuesta: $($r2.message)`n"

Write-Host "=== Prueba 3: Contexto de Conversacion ===" -ForegroundColor Cyan
$body = '{"message":"Hola"}';
$r3 = Invoke-RestMethod -Uri 'http://localhost/api/crm-chat/bot/chat/' -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8';
$sessionId = $r3.session_id
Write-Host "Session creada: $sessionId"

$body = "{`"message`":`"Que productos tienen?`",`"session_id`":$sessionId}";
$r4 = Invoke-RestMethod -Uri 'http://localhost/api/crm-chat/bot/chat/' -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8';
Write-Host "Respuesta con contexto: $($r4.message)`n"

Write-Host "=== Todas las pruebas completadas ===" -ForegroundColor Green
```

**Ejecutar:**
```powershell
.\test-chatbot.ps1
```

---

## Checklist de Verificación

- [ ] El bot responde a preguntas simples
- [ ] El bot mantiene el contexto de la conversación
- [ ] El bot detecta intenciones de compra y cambia a "waiting"
- [ ] Los mensajes se guardan correctamente en la base de datos
- [ ] El historial de mensajes se puede consultar
- [ ] El frontend muestra correctamente los mensajes
- [ ] Los contenedores de Docker se comunican correctamente
- [ ] No hay errores en los logs de backend o Ollama
- [ ] El encoding UTF-8 funciona correctamente (acentos, ñ, etc.)
- [ ] El polling de nuevos mensajes funciona

---

## Troubleshooting

### ❌ Error: "No se puede encontrar el archivo"
**Solución:** Verificar que Docker Desktop esté corriendo

### ❌ Error 404
**Solución:** Usar el prefijo `/api/` en la URL: `http://localhost/api/crm-chat/bot/chat/`

### ❌ El bot no responde
**Solución:**
```powershell
docker logs ollama --tail 50
docker restart ollama
```

### ❌ Error de encoding
**Solución:** Usar siempre `[System.Text.Encoding]::UTF8.GetBytes($body)`

### ❌ El frontend no muestra el chat
**Solución:** Verificar que el componente Chatbot esté importado en App.tsx

---

**Última actualización:** 2026-07-23
