# CRM omnicanal con Meta

Esta implementación amplía los modelos existentes `ChatSession` y
`ChatMessage`; no reemplaza el chat del ecommerce. Todos los canales terminan
en la misma bandeja `/admin/chat` y los eventos se publican por WebSocket.

## Flujo

1. Meta envía un `POST` HTTPS al webhook.
2. Django limita el tamaño y valida `X-Hub-Signature-256` con el App Secret.
3. El payload se registra por hash en `WebhookEvent` para evitar duplicados.
4. Celery normaliza el mensaje, contacto, identidad, conversación y adjuntos.
5. Channels publica el evento a los asesores conectados mediante Redis.
6. La respuesta del asesor usa automáticamente WhatsApp, Messenger, Instagram
   o el chat ecommerce según `ChatSession.channel`.
7. Si `configuration.bot_enabled` está activo, la misma memoria estructurada
   de Ollama puede responder antes de transferir la conversación a un asesor.

## URLs públicas

Reemplace `<DOMINIO_HTTPS>` por el dominio real con un certificado válido:

- Unificado recomendado: `https://<DOMINIO_HTTPS>/api/meta/webhook/`
- WhatsApp: `https://<DOMINIO_HTTPS>/api/meta/whatsapp/webhook/`
- Facebook Messenger: `https://<DOMINIO_HTTPS>/api/meta/facebook/webhook/`
- Instagram: `https://<DOMINIO_HTTPS>/api/meta/instagram/webhook/`
- Inicio de sesión de empresa de Instagram:
  `https://<DOMINIO_HTTPS>/api/meta/instagram/oauth/callback/`

El endpoint unificado detecta `whatsapp_business_account`, `page` o
`instagram`. Los alias de canal rechazan un payload de otro producto.

## Credenciales necesarias

Los access tokens los entrega Meta después de crear la aplicación, vincular los
activos y autorizar permisos. No pueden generarse desde este repositorio.

Variables obligatorias o recomendadas en el backend:

- `META_CREDENTIALS_ENCRYPTION_KEY`: clave Fernet estable usada para cifrar
  tokens guardados. Debe conservarse en el gestor de secretos del despliegue.
- `META_WEBHOOK_VERIFY_TOKEN`: token aleatorio elegido por el administrador;
  puede configurarse globalmente o por integración desde el panel.
- `META_APP_SECRET`: App Secret de Meta para la firma; puede configurarse
  globalmente o cifrado por integración desde el panel.
- `META_GRAPH_API_URL=https://graph.facebook.com`.
- `META_GRAPH_API_VERSION`: respaldo opcional; cada integración activa exige su
  versión explícita para evitar usar silenciosamente una versión obsoleta.

Para crear una clave Fernet dentro de la imagen backend:

```bash
docker compose -f docker-compose.dev.yml run --rm --no-deps backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guarde el resultado como secreto. Si cambia la clave después de registrar
cuentas, los tokens cifrados existentes dejarán de poder descifrarse.

### WhatsApp Business Platform

Se requiere WABA ID, Phone Number ID, App ID, App Secret, verify token y un
access token de usuario del sistema con los permisos aprobados de WhatsApp. La
aplicación debe suscribirse a la WABA y al campo `messages`.

### Facebook Messenger

Se requiere Page ID, App ID, App Secret, verify token y Page Access Token. La
página debe estar vinculada a la aplicación y esta debe contar con
`pages_messaging`. Meta aplica su ventana y políticas de mensajería.

### Instagram

Se requiere Instagram Professional Account ID, App ID, App Secret, verify token
y token autorizado por la cuenta profesional. Para Instagram Login se requiere
al menos `instagram_business_basic` e
`instagram_business_manage_messages`. Las conversaciones las inicia el usuario.

Configure las cuentas en `/admin/chat/integraciones`. Los secretos son campos de
solo escritura: la API informa únicamente si están configurados.

En Meta, registre como URL de redirección exactamente el valor de
`INSTAGRAM_OAUTH_REDIRECT_URI`, incluyendo `https://` y la barra final. Después
cree una integración de Instagram con App ID y App Secret y pulse **Conectar
Instagram**. El backend firma un estado temporal de un solo uso, intercambia el
código, cifra el token de larga duración y regresa al panel sin exponer el
token en React ni en la URL.

## Endpoints internos

- `GET|POST /api/meta/integrations/`: listar o crear integraciones (admin).
- `GET|PATCH|DELETE /api/meta/integrations/<id>/`: consultar, rotar o desactivar.
- `POST /api/meta/integrations/<id>/validate/`: validar token contra Graph API.
- `POST /api/meta/instagram/integrations/<id>/oauth/start/`: iniciar el acceso
  de Instagram (solo administradores).
- `GET /api/meta/instagram/oauth/callback/`: callback público registrado en
  Meta.
- `GET /api/crm-chat/sessions/`: bandeja con filtros `channel`, `status`,
  `priority`, `search` y `unanswered`.
- `PATCH /api/crm-chat/sessions/<id>/`: tomar, asignar, cerrar o priorizar.
- `GET|POST /api/crm-chat/sessions/<id>/messages/`: historial y respuesta.
- `GET|POST /api/crm-chat/queues/`: colas y miembros.
- `PATCH /api/crm-chat/queues/<id>/`: actualizar o desactivar una cola.
- WebSocket: `ws(s)://<DOMINIO>/ws/crm-chat/`, autenticado mediante el
  subprotocolo `jwt.<access_token>`; el token no se coloca en la URL.

## Tokens y rotación

WhatsApp, Facebook e Instagram no comparten un endpoint universal de refresh.
La integración permite rotar el token con `PATCH` desde el panel y almacena
`token_expires_at`. Celery Beat ejecuta diariamente `audit_meta_tokens` y deja
un evento de auditoría al vencer o entrar en la ventana de siete días. Para
tokens temporales, realice el intercambio/renovación previsto por el producto
Meta correspondiente y pegue el nuevo valor en el panel.

## Seguridad y operación

- Nginx limita `/api/meta/` a 30 solicitudes por segundo, burst 60 y 2 MB.
- DRF aplica throttling adicional a webhooks y administración.
- Los POST verifican HMAC SHA-256 sobre el cuerpo crudo y comparan en tiempo
  constante; el GET valida el verify token y devuelve el challenge literal.
- Los payloads son idempotentes; los IDs externos de mensaje son únicos.
- Los adjuntos tienen límite de 25 MB, solo HTTPS, validación DNS por salto,
  máximo de redirecciones y lista de tipos permitidos.
- Tokens y App Secrets no se serializan, registran ni envían al frontend.
- Crear, actualizar, rotar y desactivar integraciones deja auditoría sin valores
  secretos. DELETE desactiva y nunca borra conversaciones.

## Ejecución segura

Los datos persistentes se levantan con su Compose independiente. No use
`down -v` ni `--remove-orphans`.

```bash
docker compose -f docker-compose.dev.yml build backend celery-worker celery-beat
docker compose -f docker-compose.dev.yml up -d --no-deps backend celery-worker celery-beat nginx
docker compose -f docker-compose.dev.yml logs --tail=100 backend celery-worker celery-beat nginx
```

Pruebas:

```bash
docker compose -f docker-compose.dev.yml run --rm --no-deps backend python manage.py test crmChat
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce npm run build
docker compose -f docker-compose.dev.yml run --rm --no-deps nginx nginx -t
```

Una prueba real contra Graph API requiere los activos y tokens de Meta. El
botón **Probar** de `/admin/chat/integraciones` valida esa conexión sin devolver
el token al navegador.

## Referencias oficiales

- Colección oficial de Meta para WhatsApp Cloud API:
  <https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api>
- Colección oficial de Meta para Messenger Platform:
  <https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api>
- Colección oficial de Meta para Instagram API:
  <https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api>
