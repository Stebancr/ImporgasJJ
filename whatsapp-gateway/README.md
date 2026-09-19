# WhatsApp Web Gateway (experimental)

Servicio independiente que enlaza una sesión de WhatsApp Web con el CRM Django mediante Baileys. Este canal se identifica como `whatsapp_web` y se mantiene separado de `whatsapp`, que corresponde a la integración oficial de Meta.

## Advertencia

Esta integración automatiza WhatsApp Web mediante una librería no oficial. Requiere escanear un QR, no utiliza WABA, WhatsApp Cloud API, Graph API ni Embedded Signup, y no representa WhatsApp Coexistence oficial. WhatsApp puede cerrar o bloquear la sesión y no garantiza recuperar todo el historial. No debe usarse para campañas, spam, mensajes proactivos, scraping ni mecanismos para evadir restricciones.

El gateway procesa una sola conexión autorizada. El CRM solo permite responder durante una conversación reactiva existente y mantiene Ollama desactivado hasta que un administrador habilita el bot para esa integración.

## Flujo

1. El administrador abre **WhatsApp Web experimental** en el panel del CRM.
2. Django entrega un token de Socket.IO firmado, de uso administrativo y con dos minutos de vigencia.
3. El administrador solicita un QR. El gateway lo genera en memoria y lo emite por el socket autenticado; no se guarda en la base de datos ni en el navegador.
4. Baileys conserva sus credenciales en el volumen del entorno.
5. Los mensajes del cliente, del celular vinculado y del CRM se normalizan y se envían a Django con Bearer, HMAC, timestamp e identificador anti-replay.
6. Django crea o reutiliza `CRMContact`, `ChannelIdentity`, `ChatSession` y `ChatMessage`. Node nunca escribe directamente en la base de datos.
7. Las respuestas autorizadas por el CRM llegan al endpoint interno del gateway y se envían a un único JID.

## Endpoints

Gateway Node, accesible únicamente desde la red Docker:

- `GET /health`
- `GET /internal/whatsapp/status/`
- `POST /internal/whatsapp/connect/`
- `POST /internal/whatsapp/logout/`
- `POST /internal/whatsapp/send/`

Django, accesible únicamente desde la red Docker; Nginx bloquea `/api/internal/`:

- `POST /internal/whatsapp/status/`
- `POST /internal/whatsapp/webhook/`
- `POST /internal/whatsapp/media/`

Todas las rutas internas exigen `Authorization: Bearer`, `X-WhatsApp-Gateway-Timestamp`, `X-WhatsApp-Gateway-Request-ID` y `X-WhatsApp-Gateway-Signature`. La firma es HMAC-SHA256 de `timestamp.request_id.cuerpo_json`.

## Evento entrante

```json
{
  "connection_id": "primary",
  "idempotency_key": "primary:MESSAGE_ID",
  "remote_jid": "573001234567@s.whatsapp.net",
  "reply_jid": "123456789012345@lid",
  "jid_aliases": ["573001234567@s.whatsapp.net", "123456789012345@lid"],
  "number": "573001234567",
  "push_name": "Cliente",
  "message_id": "MESSAGE_ID",
  "timestamp": 1760000000,
  "type": "text",
  "text": "Hola",
  "quoted_message_id": "",
  "origin": "customer",
  "event_source": "notify",
  "is_group": false
}
```

`origin` diferencia `customer`, `mobile` y `crm`. `event_source` diferencia
eventos en vivo (`notify`), anexados por Baileys (`append`) e historial
(`history`). La clave persistida en Django es `ww:<connection_id>:<message_id>`;
el JID no forma parte de ella porque un mismo mensaje puede llegar primero con
LID y después con el número telefónico.

Se procesan `messages.upsert` y `messaging-history.set`. Los eventos
`chats.upsert`, `chats.update`, `contacts.upsert` y `connection.update` producen
logs estructurados sin texto de mensajes ni credenciales. `syncFullHistory`
permanece desactivado para evitar reimportar conversaciones completas en cada
reconexión; cualquier bloque histórico que Baileys entregue se procesa de forma
idempotente y nunca activa Ollama.

Los medios se descargan con límite de tamaño, se guardan temporalmente con permisos restrictivos, se transfieren al almacenamiento protegido de Django y luego se eliminan del gateway.

## Mensaje saliente

```json
{
  "connection_id": "primary",
  "to": "573001234567",
  "type": "text",
  "text": "Respuesta autorizada por el CRM",
  "client_message_id": "99114326-37d2-5dc3-9cbb-24b76f224f0c"
}
```

El endpoint admite texto, imagen, audio, video y documento. Rechaza números inválidos, sesiones inactivas, archivos sin URL interna del CRM y solicitudes no firmadas. `client_message_id` evita reenvíos y el resultado se conserva en el volumen de autenticación.

Los JID `numero:dispositivo@s.whatsapp.net` se convierten a
`numero@s.whatsapp.net`. Los JID `@lid` se conservan para responder y se asocian
al JID telefónico cuando Baileys conoce ambos. Grupos, estados y broadcasts no
crean contactos ni conversaciones.

## Persistencia y reconexión

`useMultiFileAuthState` guarda las credenciales Signal en `WHATSAPP_AUTH_DIR/<connection_id>`, con directorio `0700` y archivos administrados dentro del volumen. Las credenciales se eliminan solo al solicitar un QR nuevo, cerrar sesión manualmente o cuando WhatsApp informa `loggedOut`/`badSession`.

Las caídas temporales usan backoff exponencial, desde un segundo hasta un minuto, con ocho intentos. Existe un solo administrador de socket por proceso. El cierre manual cancela temporizadores y evita que una reconexión pendiente reactive la sesión.

Baileys advierte que `useMultiFileAuthState` no es una solución de almacenamiento de alto rendimiento. Para una sola conexión experimental resulta simple y auditable; las credenciales deben tratarse como claves privadas y respaldarse con controles del volumen del servidor.

## Variables

Configurar valores diferentes en DEV y PROD:

- `WHATSAPP_GATEWAY_ENV`
- `WHATSAPP_GATEWAY_PORT`
- `CRM_API_URL`
- `CRM_INTERNAL_SERVICE_TOKEN`
- `WHATSAPP_GATEWAY_URL`
- `WHATSAPP_GATEWAY_CONNECTION_ID`
- `WHATSAPP_AUTH_DIR`
- `WHATSAPP_MEDIA_DIR`
- `WHATSAPP_GATEWAY_PUBLIC_URL`
- `WHATSAPP_QR_TTL_SECONDS`
- `WHATSAPP_MAX_MEDIA_BYTES`
- `WHATSAPP_GATEWAY_MAX_MEDIA_BYTES`
- `WHATSAPP_GATEWAY_REQUEST_MAX_AGE`
- `VITE_API_URL`

No reutilizar tokens, credenciales, URLs ni volúmenes entre entornos.

## Docker

```bash
docker compose -f docker-compose.data.yml up -d
docker compose -f docker-compose.dev.yml up -d --build backend whatsapp-gateway frontend-ecommerce nginx
docker compose -f docker-compose.dev.yml --profile test run --rm --build whatsapp-gateway-test
docker compose -f docker-compose.dev.yml exec backend python manage.py test crmChat --noinput
docker compose -f docker-compose.dev.yml exec frontend-ecommerce npm run build
```

No se requiere ni se debe ejecutar `down -v`, `system prune` o `volume prune`.
