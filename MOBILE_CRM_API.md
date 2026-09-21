# API móvil y dominio oficial

## Entornos

| Entorno | `API_BASE_URL` / `API_PUBLIC_URL` |
|---|---|
| Producción | `https://www.imporgasjj.com/api/` |
| Desarrollo web local | `http://localhost/api/` |
| Dispositivo físico | URL HTTPS del túnel de desarrollo terminada en `/api/` |

La aplicación móvil debe inyectar estas variables durante su compilación. No debe
guardar el dominio de producción en el código. `localhost` desde un teléfono
apunta al propio teléfono, por lo que las pruebas físicas requieren un túnel
HTTPS que termine en Nginx.

## Autenticación y recursos

- `POST /api/auth/token/`: obtiene JWT.
- `POST /api/auth/token/refresh/`: renueva JWT.
- `GET /api/crm-chat/sessions/`: conversaciones visibles para el agente.
- `GET /api/crm-chat/contacts/`: contactos, con filtro opcional `?search=`.
- `GET /api/crm-chat/sessions/{id}/messages/`: historial cronológico.
- `GET /api/crm-chat/sessions/{id}/messages/?after={message_id}`: actualización incremental.
- `POST /api/crm-chat/sessions/{id}/messages/`: texto o archivo.
- `GET /api/crm-chat/attachments/{id}/`: descarga autenticada.
- `GET wss://www.imporgasjj.com/ws/crm-chat/`: eventos de actualización.

El JWT se envía como `Authorization: Bearer <token>`. El WebSocket usa los
subprotocolos `crm-chat` y `jwt.<token>`, igual que el CRM web.

## Enviar desde la aplicación móvil

El endpoint admite `multipart/form-data`:

- `text`: opcional cuando existe `file`.
- `file`: un JPG, JPEG, PNG, WEBP, GIF, PDF, DOC, DOCX, XLS o XLSX.
- `origin=mobile`: identifica el origen. Solo se acepta para agentes.
- `client_message_id`: UUID estable generado antes del primer intento.

La aplicación debe reutilizar el mismo `client_message_id` al reintentar. El
backend devuelve el mensaje existente y no crea duplicados. Los mensajes de un
agente móvil se guardan como `agent/outbound`, actualizan la conversación y
publican `message.created` por WebSocket.

## Adjuntos

El backend valida tamaño, extensión, MIME y firma básica del archivo. El máximo
predeterminado es 25 MiB y se configura con `CRM_ATTACHMENT_MAX_BYTES`. Los
archivos del chat nunca se enlazan directamente desde `/media/`; la aplicación
los descarga por el endpoint autenticado. Para entregar un archivo a Meta o al
gateway se genera una URL firmada temporal de cinco minutos, configurable con
`CRM_ATTACHMENT_DELIVERY_TTL`.

El CRM invalida las consultas de sesiones y mensajes al recibir el evento en
tiempo real, ordena por marca temporal e ID y deduplica por ID persistido.

## Meta en producción

- OAuth: `https://www.imporgasjj.com/api/meta/callback/`
- Facebook webhook: `https://www.imporgasjj.com/api/meta/facebook/webhook/`
- Instagram webhook: `https://www.imporgasjj.com/api/meta/instagram/webhook/`
- WhatsApp webhook: `https://www.imporgasjj.com/api/meta/whatsapp/webhook/`
- WhatsApp coexistence config: `https://www.imporgasjj.com/api/meta/whatsapp/coexistence/config/`
- WhatsApp coexistence complete: `https://www.imporgasjj.com/api/meta/whatsapp/coexistence/complete/`
- Instagram OAuth callback: `https://www.imporgasjj.com/api/meta/instagram/oauth/callback/`

En Meta Developers deben actualizarse App Domains, Valid OAuth Redirect URIs y
las URLs de webhook. El token de verificación y la firma
`X-Hub-Signature-256` continúan siendo obligatorios. Estos valores se configuran
fuera de Git y nunca se escriben en logs.
