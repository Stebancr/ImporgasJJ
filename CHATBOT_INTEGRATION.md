# Integración del Chatbot con Ollama - Gasoductos JJ

## Descripción General

Sistema de chatbot inteligente integrado con Ollama (modelo qwen2.5:1.5b) que atiende automáticamente consultas simples de clientes y deriva a un agente humano cuando detecta intenciones de compra o servicio.

## Arquitectura

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│    Nginx    │─────▶│   Backend   │─────▶│   Ollama    │
│  (Ecommerce)│      │  (Puerto 81)│      │   Django    │      │   qwen2.5   │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │  PostgreSQL │
                                           │  (Sesiones) │
                                           └─────────────┘
```

## Componentes

### 1. Backend Django (Puerto 8000)

**Archivos creados/modificados:**

- `BACKEND/crmChat/ollama_service.py` - Servicio de integración con Ollama
- `BACKEND/crmChat/views.py` - Vistas del bot (BotChatView, BotSessionMessagesView)
- `BACKEND/crmChat/urls.py` - URLs del bot
- `BACKEND/core/settings.py` - Configuración de Ollama

**Endpoints del Chatbot:**

#### POST `/api/crm-chat/bot/chat/`
Endpoint público para chatear con el bot.

**Request:**
```json
{
  "message": "¿Cuál es el horario de atención?",
  "session_id": null,           // Opcional: ID de sesión existente
  "user_name": "Juan Pérez",    // Opcional: nombre del usuario
  "user_email": "juan@email.com" // Opcional: email del usuario
}
```

**Response:**
```json
{
  "session_id": 4,
  "message": "Los horarios de atención son de lunes a viernes, desde las 8:00 AM hasta las 6:00 PM.",
  "sender_type": "bot",
  "status": "bot",              // bot | waiting | active | closed
  "needs_agent": false,
  "user_message_id": 16,
  "bot_message_id": 17
}
```

#### GET `/api/crm-chat/bot/sessions/{session_id}/messages/`
Obtener todos los mensajes de una sesión.

**Query Params:**
- `after`: ID del último mensaje recibido (para polling)

**Response:**
```json
{
  "session_id": 4,
  "status": "bot",
  "messages": [
    {
      "id": 16,
      "text": "¿Cuál es el horario?",
      "sender_type": "user",
      "sender_name": "Juan Pérez",
      "created_at": "2026-07-23T12:00:00Z"
    },
    {
      "id": 17,
      "text": "Los horarios son...",
      "sender_type": "bot",
      "sender_name": "",
      "created_at": "2026-07-23T12:00:01Z"
    }
  ],
  "agent_name": null
}
```

### 2. Ollama Service (Puerto 11434)

**Modelo:** `qwen2.5:1.5b`

**Características:**
- Responde preguntas informativas sobre productos, servicios, horarios
- Detecta palabras clave de intención de compra/servicio
- Deriva automáticamente a agente humano cuando es necesario

**Palabras clave que activan derivación a agente:**
- comprar, cotizar, cotización, precio especial, descuento
- hablar con, asesor, representante, vendedor, atención
- servicio técnico, instalación, reparación, mantenimiento
- contrato, factura, pago, financiamiento, crédito
- urgente, emergencia, problema grave, queja, reclamo

### 3. Estados de Sesión

| Estado    | Descripción                          | Quién atiende |
|-----------|--------------------------------------|---------------|
| `bot`     | Conversación con el bot             | Bot Ollama    |
| `waiting` | Esperando asignación de agente      | Nadie         |
| `active`  | Conversación con agente humano      | Agente        |
| `closed`  | Sesión cerrada                      | Nadie         |

## Ejemplo de Integración Frontend

### React/TypeScript (Ecommerce)

```typescript
// src/services/chatbotService.ts
const API_URL = '/api/crm-chat/bot';

export interface ChatMessage {
  id?: number;
  text: string;
  sender_type: 'user' | 'bot' | 'agent';
  sender_name?: string;
  created_at?: string;
}

export interface ChatResponse {
  session_id: number;
  message: string;
  sender_type: string;
  status: 'bot' | 'waiting' | 'active' | 'closed';
  needs_agent: boolean;
  user_message_id: number;
  bot_message_id: number;
}

export const sendMessage = async (
  message: string,
  sessionId?: number | null,
  userName?: string,
  userEmail?: string
): Promise<ChatResponse> => {
  const response = await fetch(`${API_URL}/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_name: userName,
      user_email: userEmail,
    }),
  });

  if (!response.ok) {
    throw new Error('Error al enviar mensaje');
  }

  return response.json();
};

export const getSessionMessages = async (
  sessionId: number,
  afterMessageId?: number
): Promise<{ messages: ChatMessage[]; status: string; agent_name?: string }> => {
  const url = afterMessageId
    ? `${API_URL}/sessions/${sessionId}/messages/?after=${afterMessageId}`
    : `${API_URL}/sessions/${sessionId}/messages/`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error('Error al obtener mensajes');
  }

  return response.json();
};
```

### Componente React Simple

```tsx
// src/components/Chatbot.tsx
import React, { useState, useEffect } from 'react';
import { sendMessage, ChatMessage } from '../services/chatbotService';

export const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>('bot');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      text: input,
      sender_type: 'user',
      sender_name: 'Tú',
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendMessage(
        input,
        sessionId,
        'Usuario Anónimo',
        ''
      );

      setSessionId(response.session_id);
      setStatus(response.status);

      const botMessage: ChatMessage = {
        id: response.bot_message_id,
        text: response.message,
        sender_type: response.sender_type as 'bot',
        sender_name: 'Asistente',
      };

      setMessages((prev) => [...prev, botMessage]);

      // Si necesita agente, mostrar alerta
      if (response.needs_agent) {
        alert('Te estamos conectando con un asesor humano...');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al enviar mensaje');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h3>Chat de Soporte</h3>
        <span className={`status-${status}`}>
          {status === 'bot' && '🤖 Bot'}
          {status === 'waiting' && '⏳ Esperando asesor'}
          {status === 'active' && '👤 Con asesor'}
        </span>
      </div>

      <div className="chatbot-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.sender_type}`}>
            <strong>{msg.sender_name}:</strong> {msg.text}
          </div>
        ))}
        {isLoading && <div className="message bot">Escribiendo...</div>}
      </div>

      <div className="chatbot-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Escribe tu mensaje..."
          disabled={isLoading || status === 'closed'}
        />
        <button onClick={handleSend} disabled={isLoading || status === 'closed'}>
          Enviar
        </button>
      </div>
    </div>
  );
};
```

## Ejemplo de Uso con PowerShell

### Pregunta Simple
```powershell
$body = '{"message":"Cual es el horario de atencion?"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json
```

### Intención de Compra (Deriva a Agente)
```powershell
$body = '{"message":"Quiero comprar tuberia de gas"}';
$result = Invoke-RestMethod `
  -Uri 'http://localhost/api/crm-chat/bot/chat/' `
  -Method Post `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json; charset=utf-8';
$result | ConvertTo-Json
```

## Configuración de Ollama en Docker

### Docker Compose (docker-compose.dev.yml)

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: ollama
  restart: unless-stopped
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  networks:
    - shared_net
  healthcheck:
    test: ["CMD", "ollama", "list"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Descargar el Modelo

```bash
docker exec ollama ollama pull qwen2.5:1.5b
```

### Verificar Modelos Instalados

```bash
docker exec ollama ollama list
```

## Variables de Entorno (.env)

```bash
# Ollama Configuration
OLLAMA_API_URL=http://ollama:11434/api/chat
OLLAMA_MODEL=qwen2.5:1.5b
```

## Comandos Útiles

### Verificar Logs del Backend
```bash
docker logs -f backend
```

### Verificar Logs de Ollama
```bash
docker logs -f ollama
```

### Probar Ollama Directamente
```bash
docker exec -it ollama ollama run qwen2.5:1.5b
```

### Reiniciar Servicios
```bash
docker-compose -f docker-compose.dev.yml restart backend ollama
```

## Flujo de Conversación

### 1. Usuario hace una pregunta simple
```
Usuario: "¿Cuál es el horario de atención?"
Bot: "Los horarios son de lunes a viernes, de 8:00 AM a 6:00 PM."
Estado: bot
```

### 2. Usuario pregunta sobre productos
```
Usuario: "¿Qué productos de tuberías tienen?"
Bot: "Tenemos tuberías de gas de diferentes diámetros, válvulas, conexiones..."
Estado: bot
```

### 3. Usuario quiere comprar
```
Usuario: "Quiero comprar tubería de gas"
Bot: "Te voy a conectar con un asesor especializado..."
Estado: waiting → Un agente debe tomar la conversación
```

### 4. Agente toma la conversación
```
Agente: "Hola, soy Juan. ¿En qué puedo ayudarte con tu compra?"
Estado: active
```

## Monitoreo para Agentes

Los agentes pueden ver las sesiones pendientes en:
- **Endpoint:** `GET /api/crm-chat/sessions/?status=waiting`
- Solo accesible para usuarios con `tipo_usuario` en [1, 4]

## Próximos Pasos

1. **Frontend:**
   - Implementar componente de chat en el ecommerce (puerto 81)
   - Agregar widget flotante de chat
   - Implementar notificaciones en tiempo real

2. **Backend:**
   - Agregar WebSockets para mensajes en tiempo real
   - Implementar sistema de notificaciones para agentes
   - Agregar métricas de satisfacción del bot

3. **Bot:**
   - Personalizar respuestas según historial de compras del usuario
   - Integrar con catálogo de productos real
   - Agregar soporte multiidioma

## Troubleshooting

### El bot no responde
1. Verificar que Ollama esté corriendo: `docker ps | grep ollama`
2. Verificar logs: `docker logs ollama`
3. Verificar que el modelo esté descargado: `docker exec ollama ollama list`

### Error 404 en el endpoint
- Asegurarse de usar el prefijo `/api/`: `http://localhost/api/crm-chat/bot/chat/`

### Error de encoding en las respuestas
- Usar UTF-8 en las peticiones: `Content-Type: application/json; charset=utf-8`

### El bot no deriva a agente
- Verificar logs del backend para ver si detecta las palabras clave
- Las palabras clave están en `ollama_service.py` → `NEEDS_AGENT_KEYWORDS`
