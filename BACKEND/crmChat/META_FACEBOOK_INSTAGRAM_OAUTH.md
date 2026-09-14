# OAuth oficial de Facebook Pages e Instagram Professional

Esta conexión usa **Facebook Login** para descubrir las Facebook Pages que
administra el usuario y las cuentas Instagram Professional asociadas. No usa
WhatsApp Cloud API, no solicita permisos de WhatsApp y no modifica números.

## Versión y endpoints

La integración fue desarrollada y probada con la versión actual `v26.0`
(publicada por Meta el 29 de julio de 2026). La versión se configura y no está
fijada dentro del servicio:

```env
META_GRAPH_API_VERSION=v26.0
```

El backend construye estas operaciones oficiales:

- autorización: `https://www.facebook.com/{version}/dialog/oauth`;
- intercambio: `https://graph.facebook.com/{version}/oauth/access_token`;
- inspección del token: `https://graph.facebook.com/{version}/debug_token`;
- páginas administradas: `https://graph.facebook.com/{version}/me/accounts`.

Antes de actualizar de versión se debe revisar el changelog de Graph API y
ejecutar las pruebas mockeadas y una conexión con activos de prueba.

## Variables del backend

```env
META_APP_ID=
META_APP_SECRET=
META_REDIRECT_URI=https://crm.example.com/api/meta/callback/
META_GRAPH_API_URL=https://graph.facebook.com
META_GRAPH_API_VERSION=v26.0
META_OAUTH_AUTHORIZE_URL=https://www.facebook.com
META_OAUTH_STATE_MAX_AGE=600
META_OAUTH_SCOPES=pages_show_list,pages_read_engagement,pages_manage_metadata,pages_messaging,instagram_basic,instagram_manage_messages
META_OAUTH_FRONTEND_REDIRECT=/admin/chat/integraciones
META_WEBHOOK_VERIFY_TOKEN=
META_CREDENTIALS_ENCRYPTION_KEY=
```

`META_APP_SECRET`, `META_WEBHOOK_VERIFY_TOKEN` y la clave Fernet pertenecen
exclusivamente al backend. No deben existir variables `VITE_` equivalentes.
La clave Fernet debe permanecer estable; cambiarla vuelve ilegibles los tokens
ya cifrados.

La redirect URI debe coincidir carácter por carácter con la registrada en Meta,
incluida la barra final. En producción debe ser HTTPS. HTTP solo se acepta para
`localhost` cuando Django se ejecuta con `DEBUG=True`.

## Configuración en Meta for Developers

1. Crear o reutilizar una aplicación de tipo/uso empresarial compatible con
   Facebook Login for Business, Messenger Platform e Instagram API with
   Facebook Login.
2. No agregar el producto WhatsApp para este flujo.
3. Registrar `META_REDIRECT_URI` en **Valid OAuth Redirect URIs**.
4. Solicitar únicamente:
   - `pages_show_list`;
   - `pages_read_engagement`;
   - `pages_manage_metadata`;
   - `pages_messaging`;
   - `instagram_basic`;
   - `instagram_manage_messages`.
5. Configurar como callback del webhook:
   `https://<dominio>/api/meta/webhook/`.
6. Usar exactamente el valor de `META_WEBHOOK_VERIFY_TOKEN` como verify token.
7. Suscribir en el panel los objetos **Page** e **Instagram** y únicamente los
   eventos de mensajería que realmente procese el CRM. El endpoint reconoce
   `object=page` y `object=instagram`.

Meta cambia la organización de productos y casos de uso del dashboard sin
cambiar necesariamente Graph API. Si el dashboard no muestra un permiso, se
debe elegir el caso de uso Messenger/Instagram correspondiente; nunca se debe
sustituir por un permiso de WhatsApp.

## App Review y modos

- En Development Mode solo pueden autorizar usuarios con rol en la aplicación
  y activos de prueba que administren.
- Para conversar con personas sin rol en la aplicación se necesita Advanced
  Access y App Review para los permisos de Pages/Messenger/Instagram usados.
- Instagram Messaging requiere una aplicación perteneciente a una empresa
  verificada.
- La revisión debe demostrar login, selección de cuentas, recepción y respuesta
  de mensajes y eliminación/desconexión de datos.
- En Live Mode solo funcionarán permisos concedidos y aprobados. Una autorización
  puede ser revocada o perder permisos posteriormente.

## Flujo del CRM

1. React llama con JWT a `GET /api/meta/connect/`.
2. Django genera un nonce aleatorio, guarda su propietario en Redis y devuelve
   la URL de autorización. El App Secret nunca se incluye.
3. React navega a Meta.
4. Meta regresa a `GET /api/meta/callback/` con `code` y `state`.
5. Django consume el state una sola vez, intercambia el código y valida el token
   mediante `debug_token`.
6. Solo si el token es válido y contiene todos los permisos se consulta
   `/me/accounts`.
7. Los tokens de usuario y página se cifran. React recibe solo IDs, nombres,
   estado y fechas.
8. El administrador selecciona cuentas y el CRM crea/adapta sus
   `ChannelIntegration` de Facebook e Instagram.
9. Desconectar desactiva adaptadores y conserva conversaciones y auditoría.

La duración no se calcula con una constante de 60 días. `token_expires_at` se
obtiene de `debug_token` cuando Meta proporciona `expires_at`; puede ser nulo.
Celery Beat valida diariamente conexiones activas y desactiva adaptadores cuyo
token resulte inválido.

## Endpoints

```text
GET    /api/meta/connect/
GET    /api/meta/callback/
GET    /api/meta/connections/
GET    /api/meta/connections/{id}/accounts/
POST   /api/meta/connections/{id}/accounts/
DELETE /api/meta/connections/{id}/
GET    /api/meta/webhook/
POST   /api/meta/webhook/
```

Todos salvo callback y webhook requieren un administrador autenticado. Una
conexión solo puede consultarse, seleccionarse o desconectarse por el usuario
del CRM que la creó.

## Pruebas en desarrollo

Use una cuenta con rol en la aplicación Meta, una Facebook Page administrada y
una cuenta Business/Creator vinculada a esa página. Configure un túnel HTTPS
estable si Meta no puede acceder al host local. No copie tokens al frontend.

```bash
docker compose -f docker-compose.dev.yml exec -T backend python manage.py test crmChat.tests.MetaFacebookInstagramOAuthTests
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce npm run build
```

Referencias:

- <https://developers.facebook.com/docs/graph-api/changelog/versions/>
- <https://developers.facebook.com/docs/facebook-login/guides/access-tokens/>
- <https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api>
- <https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api>
- <https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api>
