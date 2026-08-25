
## 1) Ejecutar Ollama en Docker

Comando:

```
docker run -d --name ollama-qwen -p 11434:11434 -v ollama-qwen:/root/.ollama ollama/ollama
```

Qué hace:
- `docker run -d`: ejecuta el contenedor en segundo plano.
- `--name ollama-qwen`: asigna el nombre `ollama-qwen` al contenedor.
- `-p 11434:11434`: mapea el puerto 11434 del host al contenedor.
- `-v ollama-qwen:/root/.ollama`: monta el volumen `ollama-qwen` para persistencia de datos en `/root/.ollama` dentro del contenedor.
- `ollama/ollama`: imagen de Docker que se ejecuta.

## 2) Descargar el modelo qwen2.5:1.5b dentro del contenedor

Descargar el modelo usando `docker exec`:

```
docker exec -it ollama-qwen ollama pull qwen2.5:1.5b
```

Qué hace:
- `ollama pull qwen2.5:1.5b`: descarga el modelo `qwen2.5:1.5b` en el servicio Ollama del contenedor.

Nota: El modelo estará disponible automáticamente vía API después de descargarlo.

## 3) Petición HTTP al endpoint de chat

Endpoint (local):

```
http://localhost:11434/api/chat
```

Ejemplo de petición en formato JSON (body) que debe enviarse como `application/json`:

```json
{
	"messages": [
		{
			"role": "system",
			"content": "Eres un asistente de la empresa Gasoductos JJ. Solo responde usando la información proporcionada. Si no encuentras la respuesta, di 'No tengo esa información'."
		},
		{
			"role": "system",
			"content": "Información de la empresa:\nHorario: Lunes a Viernes de 8:00 a 18:00.\nTeléfono: 555-1234.\nDirección: Calle 123.\n\nResponde únicamente con esta información."
		},
		{
			"role": "user",
			"content": "¿Cuál es el horario?"
		}
	],
	"model": "qwen2.5:1.5b",
	"stream": false
}
```

Ejemplo de petición con PowerShell:

```powershell
$body = @{
    model = 'qwen2.5:1.5b'
    stream = $false
    messages = @(
        @{role='system'; content='Eres un asistente de la empresa Gasoductos JJ. Solo responde usando la información proporcionada. Si no encuentras la respuesta, di ''No tengo esa información''.'},
        @{role='system'; content='Información de la empresa:\nHorario: Lunes a Viernes de 8:00 a 18:00.\nTeléfono: 555-1234.\nDirección: Calle 123.\n\nResponde únicamente con esta información.'},
        @{role='user'; content='¿Cuál es el horario?'}
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'http://localhost:11434/api/chat' -Method Post -Body $body -ContentType 'application/json'
```

Ejemplo de petición curl (Linux/Mac):

```bash
curl -s -X POST http://localhost:11434/api/chat \
	-H "Content-Type: application/json" \
	-d '{"messages":[{"role":"system","content":"Eres un asistente de la empresa Gasoductos JJ. Solo responde usando la información proporcionada. Si no encuentras la respuesta, di '\''No tengo esa información'\''."},{"role":"system","content":"Información de la empresa:\nHorario: Lunes a Viernes de 8:00 a 18:00.\nTeléfono: 555-1234.\nDirección: Calle 123.\n\nResponde únicamente con esta información."},{"role":"user","content":"¿Cuál es el horario?"}],"model":"qwen2.5:1.5b","stream":false}'
```

Respuesta esperada (según la instrucción del sistema):

```
"Lunes a Viernes de 8:00 a 18:00."
```


