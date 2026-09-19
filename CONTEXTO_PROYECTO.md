# Contexto del proyecto

> Documento de continuidad para retomar el trabajo en otra conversación o cuenta.
> No contiene secretos, tokens ni valores sensibles.

## 1. Proyecto

Este repositorio contiene un ecommerce y un CRM omnicanal para gestionar clientes,
pedidos, visitas técnicas, conversaciones y canales de mensajería.

La integración pendiente/prioritaria es la administración completa de Meta:

- Facebook Messenger/Pages.
- Instagram Professional/Business.
- WhatsApp Business mediante el modelo oficial de **WhatsApp Coexistence**.

La empresa y su cuenta de Meta Business ya se encuentran verificadas por Meta.
Por lo tanto, el trabajo no parte de una verificación empresarial pendiente; debe
concentrarse en implementar y validar correctamente la conexión técnica de
WhatsApp Coexistence dentro de la arquitectura existente.

Para WhatsApp, la solución debe contemplar la coexistencia entre la aplicación
WhatsApp Business y la integración del CRM mediante Cloud API, respetando los
requisitos, identificadores, permisos, webhooks, proceso de vinculación y
limitaciones oficiales de Meta.

Requisito funcional obligatorio para WhatsApp:

- Crear o vincular el `WhatsApp Business Account (WABA)` requerido por Meta
  durante el onboarding oficial de Coexistence.
- Conectar el número existente de WhatsApp Business únicamente mediante
  **WhatsApp Coexistence**.
- Mantener el uso de WhatsApp Business en el celular con el mismo número.
- Conservar las conversaciones y el historial que ya existen en WhatsApp
  Business, en la medida permitida por el flujo oficial de Meta.
- Vincular el WABA, Phone Number ID, Business ID y teléfono correctos con la
  integración del CRM.
- No reemplazar automáticamente la cuenta móvil por una conexión aislada de
  Cloud API.
- No implementar una migración tradicional, una desvinculación destructiva ni un
  flujo alternativo que pueda sacar el número de WhatsApp Business del celular.

El flujo exacto de creación o vinculación del WABA debe seguir exclusivamente el
onboarding oficial que Meta habilite para Coexistence y debe documentarse si
algún paso requiere realizarse manualmente en Meta Business Manager o Meta
Developers.

El objetivo es permitir conectar, validar, utilizar, desconectar y volver a
conectar otra cuenta sin reutilizar credenciales o identificadores de una cuenta
anterior y sin eliminar el historial del CRM. En WhatsApp Coexistence también se
debe garantizar que los mensajes enviados desde la aplicación WhatsApp Business y
los mensajes enviados desde el CRM mantengan una sincronización coherente según
las capacidades oficiales disponibles para la cuenta.

## 2. Arquitectura detectada

### Backend

- Django 5.
- Django REST Framework.
- Código en `BACKEND/`.
- Aplicación principal de chat en `BACKEND/crmChat/`.
- Celery para procesamiento asíncrono.
- Redis para colas, resultados, cache y Channels.
- Daphne/ASGI para el backend y WebSockets.
- PostgreSQL o MySQL según el entorno configurado.
- Cifrado de credenciales mediante el servicio existente de Meta.

### Frontend

- React.
- TypeScript.
- Vite.
- Material UI.
- React Query.
- Código en `frontend_U/`.
- Pantalla de integraciones Meta:
  `frontend_U/src/admin/pages/MetaIntegrationsPage.tsx`.
- Cliente administrativo de API:
  `frontend_U/src/admin/services/admin_chat.ts`.

### Ejecución

- Desarrollo mediante `docker-compose.dev.yml`.
- Producción mediante `docker-compose.prod.yml` y archivos relacionados.
- Nginx funciona como proxy para frontend y backend.
- El proyecto utiliza volúmenes persistentes para datos y media.

No ejecutar comandos destructivos como `docker compose down -v`, `docker system
prune`, `docker volume prune`, `flush`, `DROP DATABASE`, `DROP TABLE` ni borrar
volúmenes persistentes.

## 3. Integración Meta existente

La funcionalidad Meta está distribuida principalmente en:

- `BACKEND/crmChat/apps/meta/`.
- `BACKEND/crmChat/apps/facebook/`.
- `BACKEND/crmChat/apps/instagram/`.
- `BACKEND/crmChat/apps/whatsapp/`.

Componentes relevantes de Meta:

- `meta/oauth.py`: inicio OAuth, consumo del state, intercambio de código,
  validación y descubrimiento de páginas/cuentas.
- `meta/services.py`: Graph API, credenciales, validaciones, webhook y envío
  unificado.
- `meta/views.py`: endpoints administrativos, callback OAuth y webhook.
- `meta/webhooks.py`: detección de canal, normalización y resolución inicial.
- `meta/serializers.py`: contratos de API y ocultamiento de secretos.
- `whatsapp/services.py`: envío de mensajes por WhatsApp Cloud API.
- `whatsapp/webhooks.py`: parser de mensajes y estados de WhatsApp.

## 4. Rutas Meta detectadas

Las rutas principales existentes son:

- `GET /api/meta/connect/`
- `GET /api/meta/callback/`
- `GET /api/meta/webhook/`
- `POST /api/meta/webhook/`
- `GET /api/meta/connections/`
- `GET /api/meta/connections/<id>/`
- `DELETE /api/meta/connections/<id>/`
- `GET /api/meta/connections/<id>/accounts/`
- `POST /api/meta/connections/<id>/accounts/`
- `GET /api/meta/integrations/`
- `POST /api/meta/integrations/`
- `PATCH /api/meta/integrations/<id>/`
- `DELETE /api/meta/integrations/<id>/`
- `POST /api/meta/integrations/<id>/validate/`

También existe una ruta de inicio OAuth de Instagram referenciada por el
frontend. Debe verificarse en el enrutamiento real antes de modificarla:

- `POST /api/meta/instagram/integrations/<id>/oauth/start/`

## 5. Modelos importantes

### `MetaConnection`

Representa una autorización OAuth de Facebook asociada a un usuario del CRM.
Conserva el token de usuario cifrado, permisos, expiración, estado de validación y
si la conexión está activa.

### `MetaFacebookPage`

Representa una página descubierta mediante OAuth. Conserva Page ID, nombre,
Page Access Token cifrado, permisos/tareas y estados de selección/actividad.

### `MetaInstagramAccount`

Representa una cuenta Instagram Professional/Business relacionada con una página
de Facebook. Conserva Instagram Account ID, username, nombre y estado.

### `ChannelIntegration`

Es la integración externa que utiliza el CRM para recibir y enviar mensajes.
Admite los canales:

- `ecommerce`
- `whatsapp`
- `facebook`
- `instagram`

Incluye, entre otros:

- `external_account_id`
- `phone_number_id`
- `page_id`
- `instagram_account_id`
- `graph_api_version`
- credenciales cifradas
- estado `active`
- vencimiento del token
- configuración JSON
- referencias a `MetaConnection`, página e Instagram

### Mensajería e historial

- `CRMContact`: contacto normalizado.
- `ChannelIdentity`: identidad del contacto por integración y canal.
- `ChatSession`: conversación unificada.
- `ChatMessage`: mensajes entrantes, salientes y del bot.
- `WebhookEvent`: evento Meta idempotente y procesable por Celery.
- `ChatAuditEvent`: trazabilidad administrativa.

Las conversaciones y mensajes históricos deben conservarse al desconectar una
cuenta.

## 6. Flujo actual de OAuth Facebook/Instagram

El flujo existente, a alto nivel, es:

1. Un administrador solicita `/api/meta/connect/`.
2. El backend genera una URL OAuth con `state` firmado y de un solo uso.
3. Meta redirige a `/api/meta/callback/`.
4. El backend consume y valida el `state`.
5. Se intercambia el código por un token.
6. Se valida el token.
7. Se descubren páginas y cuentas de Instagram disponibles.
8. El administrador selecciona páginas/cuentas.
9. Se crean o actualizan las integraciones de Facebook e Instagram.

No se debe eliminar la validación de `state`, la expiración ni el uso único del
callback.

## 7. Flujo actual de WhatsApp

WhatsApp utiliza `ChannelIntegration` y servicios específicos para Cloud API,
pero el objetivo funcional es integrarlo mediante WhatsApp Coexistence, es decir,
crear o vincular el WABA necesario y mantener la aplicación WhatsApp Business y
el CRM conectados al mismo número, sin abandonar el uso móvil ni perder el
historial existente.
El envío se realiza utilizando el `phone_number_id` de la integración activa.

No se acepta como solución:

- Conectar el número únicamente como Cloud API independiente.
- Eliminar o desvincular WhatsApp Business del celular.
- Crear un WABA separado que no corresponda al número existente.
- Solicitar al usuario borrar conversaciones o reinstalar la aplicación para
  completar la integración.
- Marcar como exitosa una conexión si Meta no confirma el WABA y el Phone Number
  ID resultantes del onboarding de Coexistence.

El parser de webhook obtiene actualmente datos como:

- WABA ID desde `entry.id`.
- Phone Number ID desde `value.metadata.phone_number_id`.
- Identidad del remitente.
- ID externo del mensaje.
- Tipo y contenido del mensaje.
- Estados de entrega.

Antes de ampliar el flujo de conexión de WhatsApp se debe determinar si el
proyecto usa configuración manual, OAuth de Meta o una combinación de ambos.
No asumir que WhatsApp utiliza el mismo callback de Facebook/Instagram.

## 8. Webhook Meta

El webhook unificado está implementado en `MetaWebhookView`.

Características actuales importantes:

- Utiliza `AllowAny`.
- No usa autenticación JWT para Meta.
- Tiene un GET de verificación mediante `hub.verify_token` y `hub.challenge`.
- Tiene un POST para eventos.
- Valida la firma `X-Hub-Signature-256` mediante el servicio Meta.
- Detecta los canales `whatsapp`, `instagram` y `facebook` mediante el objeto del
  payload.
- Puede forzar el canal desde un alias tipado de WhatsApp.
- Crea eventos idempotentes.
- Envía los eventos nuevos a `process_meta_webhook_task`.

Debe investigarse cualquier `401 Unauthorized` distinguiendo entre:

- GET de verificación de Meta.
- POST firmado de eventos.
- Endpoints administrativos internos protegidos con JWT.

No resolver un 401 eliminando validaciones de seguridad.

## 9. Objetivo funcional de Meta

Cada canal debe poder:

1. Conectar.
2. Autenticar.
3. Obtener los identificadores reales.
4. Intercambiar o validar tokens cuando corresponda.
5. Validar la conexión contra Graph API.
6. Recibir mensajes.
7. Enviar mensajes permitidos.
8. Desconectar.
9. Invalidar o desactivar la conexión anterior.
10. Limpiar relaciones temporales y cache.
11. Conectar otra cuenta.

La interfaz no debe mostrar “Conectado” solamente porque Meta redirigió al
callback. La conexión se considera válida únicamente después de una prueba real
contra la API y de comprobar los identificadores del recurso.

## 10. Reglas de desconexión y reconexión

Al desconectar una integración:

- Desactivar la integración.
- Dejar inutilizable el token anterior.
- Limpiar la asociación activa de la cuenta externa.
- Limpiar IDs temporales o de selección.
- Limpiar sesiones OAuth pendientes.
- Invalidar cache relacionado.
- Registrar auditoría.
- Mantener contactos, conversaciones, mensajes, órdenes y trazabilidad.

Al conectar otra cuenta, el sistema debe usar exclusivamente los datos nuevos.
No puede utilizar por error:

- Tokens antiguos.
- Page IDs antiguos.
- Instagram Account IDs antiguos.
- WABA IDs antiguos.
- Phone Number IDs antiguos.
- Business IDs antiguos.

Para WhatsApp, la resolución de eventos debe basarse en los identificadores
recibidos por Meta, especialmente `Phone Number ID` y `WABA ID`, no en “el único
token disponible”.

## 11. Seguridad

Los secretos deben permanecer en backend y cifrados usando el mecanismo
existente.

Nunca:

- Guardar tokens en el frontend o `localStorage`.
- Mostrar tokens completos en respuestas o logs.
- Exponer App Secret o Verify Token.
- Guardar secretos en Git.
- Aceptar callbacks sin `state` válido.
- Aceptar cualquier webhook sin verificar firma y estructura.
- Usar credenciales de otra cuenta.

El frontend puede mostrar indicadores como:

- `has_access_token`
- `has_app_secret`
- `has_verify_token`
- `token_status`
- fecha de expiración

## 12. Frontend actual

La pantalla `MetaIntegrationsPage.tsx` ya permite gestionar parcialmente:

- Conexión OAuth de Facebook/Instagram.
- Selección de páginas.
- Selección de cuentas Instagram relacionadas.
- Integraciones manuales.
- Rotación de credenciales.
- Validación.
- Activación/desactivación.
- Desconexión de conexiones Meta.

Debe ampliarse para presentar separadamente Facebook, Instagram y WhatsApp, sin
mostrar credenciales sensibles y actualizando el estado después de conectar o
desconectar.

## 13. Variables de entorno relevantes

Los nombres conocidos están documentados en `.env.example`:

- `META_GRAPH_API_URL`
- `META_GRAPH_API_VERSION`
- `META_APP_ID`
- `META_APP_SECRET`
- `META_HTTP_TIMEOUT`
- `META_WEBHOOK_MAX_BYTES`
- `META_WEBHOOK_VERIFY_TOKEN`
- `META_CREDENTIALS_ENCRYPTION_KEY`
- `META_TOKEN_WARNING_DAYS`
- `META_REDIRECT_URI`
- `META_OAUTH_AUTHORIZE_URL`
- `META_OAUTH_STATE_MAX_AGE`
- `META_OAUTH_SCOPES`
- `META_OAUTH_FRONTEND_REDIRECT`
- `INSTAGRAM_OAUTH_REDIRECT_URI`
- `INSTAGRAM_OAUTH_AUTHORIZE_URL`
- `INSTAGRAM_OAUTH_TOKEN_URL`
- `INSTAGRAM_GRAPH_API_URL`
- `INSTAGRAM_OAUTH_SCOPES`
- `INSTAGRAM_OAUTH_STATE_MAX_AGE`
- `THROTTLE_META_WEBHOOK_RATE`
- `THROTTLE_META_ADMIN_RATE`

No escribir valores reales de estas variables en este documento.

## 14. Pruebas requeridas

Antes de considerar terminado el trabajo, probar como mínimo:

### Facebook

- Conectar cuenta A.
- Validar token y página.
- Recibir un mensaje.
- Responder.
- Desconectar.
- Conectar cuenta B.
- Verificar que no se utilicen credenciales ni Page ID de A.

### Instagram

- Conectar cuenta profesional A.
- Validar cuenta y página asociada.
- Recibir y responder mensajes.
- Desconectar.
- Conectar cuenta B.
- Verificar que B sea la única conexión activa.

### WhatsApp

- Conectar número A.
- Validar WABA y Phone Number ID.
- Validar token.
- Verificar GET del webhook.
- Verificar POST firmado.
- Recibir y guardar un mensaje.
- Responder desde el CRM.
- Desconectar A.
- Conectar número B.
- Confirmar que los eventos de B se resuelven por sus identificadores reales.
- Confirmar que A no se utiliza para enviar ni recibir mensajes nuevos.

### Seguridad y regresión

- Probar `state` OAuth inválido, expirado y reutilizado.
- Probar firma de webhook inválida.
- Probar payload de canal incorrecto.
- Probar endpoints administrativos sin JWT.
- Confirmar que los secretos no aparecen en responses ni logs.
- Ejecutar las pruebas dentro de Docker.

## 15. Pendientes prioritarios

1. Auditar el estado real de Facebook e Instagram.
2. Auditar el flujo actual de WhatsApp y determinar si es manual u OAuth.
3. Confirmar todas las rutas registradas en Django.
4. Confirmar cómo se resuelve actualmente una integración desde un webhook.
5. Investigar la causa exacta de cualquier 401.
6. Validar que la desconexión inutilice efectivamente las credenciales antiguas.
7. Permitir reconexión con otra cuenta sin borrar datos históricos.
8. Revisar si el modelo necesita campos adicionales para Business ID, WABA ID,
   estado de conexión, última validación y último error.
9. Crear migraciones solamente si son necesarias y siempre de forma aditiva.
10. Ampliar frontend y pruebas.
11. Documentar la configuración manual necesaria en Meta Developers.

## 16. Criterio de finalización

El trabajo no está terminado porque la interfaz muestre “Conectado”.

Debe comprobarse que:

- El token es válido.
- La cuenta externa es la correcta.
- Los IDs corresponden a la cuenta conectada.
- Graph API responde.
- El webhook se verifica correctamente.
- Los eventos entrantes se procesan.
- Los mensajes salientes funcionan.
- La desconexión desactiva la cuenta anterior.
- La reconexión utiliza la nueva cuenta.
- La cuenta anterior no interfiere.
- El historial del CRM se conserva.

## 17. Restricciones de trabajo

- Auditar antes de implementar.
- Mantener la arquitectura existente cuando sea adecuada.
- No hacer búsquedas web extensivas.
- Si se necesita verificar una característica de Meta, usar documentación oficial.
- No inventar capacidades que Meta no soporte.
- No incluir secretos en informes, commits ni documentación.
- No ejecutar comandos destructivos.

## 18. Inventario completo del backend

### 18.1 `core`: configuración y arranque del proyecto

Ruta: `BACKEND/core/`

Es el proyecto Django y concentra la configuración global de HTTP, ASGI,
Celery, base de datos, seguridad, cache, correo, Wompi, Firebase, Ollama y
Meta.

Archivos principales:

- `core/settings.py`: configuración base usada por `manage.py`, Daphne y Celery.
- `core/config/base.py`: configuración compartida adicional.
- `core/config/dev.py`: ajustes de desarrollo.
- `core/settings_production.py`: ajustes de producción.
- `core/urls.py`: enrutamiento raíz.
- `core/asgi.py`: HTTP Django y WebSocket mediante Channels.
- `core/wsgi.py`: entrada WSGI tradicional.
- `core/celery.py`: instancia Celery y autodetección de tareas.
- `core/health.py`: health check.

Aplicaciones activas en `INSTALLED_APPS`:

- `usuarios`
- `ecommerce`
- `gestion`
- `crmChat`
- `AppVisits`
- aplicaciones estándar de Django, DRF, Channels y CORS.

Configuración global relevante:

- `AUTH_USER_MODEL = 'usuarios.Credenciales'`.
- JWT con access token de 12 horas y refresh token de 1 día.
- Autenticación DRF con JWT con versión de contraseña, token DRF y sesión.
- Throttling para login, chat, pagos, Wompi y Meta.
- Cache en Redis cuando existe `REDIS_URL`; cache local durante pruebas.
- Channels con Redis en `CHANNEL_REDIS_URL`.
- Celery con Redis como broker y backend.
- Zona horaria de Celery: `America/Bogota`.
- Tareas programadas para cerrar sesiones inactivas y auditar conexiones Meta.

Rutas globales:

- `/admin/`: administración Django.
- `/auth/token/` y `/auth/token`: emisión de JWT.
- `/auth/token/refresh/` y `/auth/token/refresh`: renovación de JWT.
- `/user/`: usuarios, perfiles, términos y contraseñas.
- `/ecommerce/` y `/`: catálogo, carrito, pedidos, pagos y notificaciones.
- `/gestion/`: inventario por sede, cotizaciones y facturas.
- `/crm-chat/`: conversaciones, bot y colas.
- `/meta/` y `/api/meta/`: integración Meta.
- `/visits/`: visitas técnicas.

El prefijo `/api/meta/` funciona como compatibilidad para proxies que entregan el
prefijo API directamente a Django. Las rutas `/meta/` sin `/api/` también están
registradas.

### 18.2 `auth`: autenticación JWT

Ruta: `BACKEND/auth/`

No es una aplicación Django registrada con modelos propios; es un módulo de
autenticación utilizado por el proyecto.

Archivos:

- `authentication.py`: autenticación JWT personalizada que tiene en cuenta la
  versión de contraseña.
- `serializers.py`: serializers asociados al login/token.
- `views.py`: `TokenLMSView` y `PasswordVersionRefreshView`.

Responsabilidades:

- Emitir access y refresh tokens.
- Rechazar tokens asociados a una versión de contraseña antigua.
- Permitir invalidar las sesiones de un usuario aumentando `password_version`.
- Mantener alias con y sin barra final para evitar problemas con proxies.

### 18.3 `usuarios`: cuentas, roles y administración de usuarios

Ruta: `BACKEND/usuarios/`

Es la aplicación de usuarios y el origen del modelo de autenticación del
proyecto.

Modelos:

- `Cargo`: cargos o roles laborales.
- `Niveles`: niveles organizacionales.
- `Regional`: regionales.
- `Usuario`: información personal y laboral vinculada a cargo, nivel y regional.
- `Credenciales`: usuario autenticable, contraseña, estado, rol, sede y versión
  de contraseña.
- `Colaboradores`: colaboradores operativos.
- `Usuarios`: estructura heredada adicional relacionada con colaboradores.

Archivos principales:

- `models.py`: modelos y relaciones.
- `views.py`: registro, perfil, listados, roles, estados, cargos, niveles,
  regionales, importación masiva y reporte de usuarios.
- `account_views.py`: cambio y restablecimiento de contraseña.
- `serializers.py`: representación de usuarios y perfiles.
- `permissions.py`: permisos de usuario y administración.
- `api.py`: `UsuariosViewSet` heredado.
- `terms.py`: términos y versión vigente.
- `admin.py`: configuración de administración.

Rutas principales bajo `/user/`:

- `password/change`, `password/reset/request` y `password/reset/confirm`.
- `terms` y `terms/accept`.
- `registerUsers`, `register`, `register-public` y `register-temporal`.
- `registrar-masivo`.
- `perfil` y `perfil/<id>`.
- `lista-usuarios`, `filtrar-usuarios` y `reporte-usuarios`.
- `cargos`, `niveles`, `regiones` y `cargo-nivel-regional`.
- `cambiar-estado-usuario` y `actualizar-rol-usuario/<id>`.

Reglas importantes:

- El usuario autenticado del proyecto es `Credenciales`.
- Los roles administrativos se distinguen mediante `tipo_usuario`.
- El frontend público y el panel administrativo tienen contextos de sesión
  separados.
- El registro público debe aceptar explícitamente los términos vigentes.
- Cambiar la contraseña debe invalidar los JWT anteriores del usuario.

Pruebas relevantes:

- `usuarios/tests.py`
- `usuarios/test_account.py`
- `usuarios/test_terms.py`

### 18.4 `ecommerce`: catálogo, compras, pagos y notificaciones

Ruta: `BACKEND/ecommerce/`

Es el núcleo del ecommerce y sus endpoints se publican tanto bajo `/` como bajo
`/ecommerce/` por compatibilidad.

Modelos:

- `Brand`, `Location`, `Category` y `SpecAttribute`.
- `Product`, `ProductImage`, `ProductStock` y `ProductSpec`.
- `Review`, `CartItem`, `Order`, `OrderItem` y `TrackingEvent`.
- `WompiPaymentIntent`.
- `UserAddress`, `Favorite`, `FCMDeviceToken` y `Notification`.

Archivos auxiliares:

- `views.py`: catálogo, carrito, pedidos, Wompi, direcciones, favoritos y
  notificaciones.
- `serializers.py`: respuestas de productos, órdenes y recursos relacionados.
- `firebase_service.py`: inicialización de Firebase Admin y envío de push.
- `email_service.py`: correo de confirmación de pago.
- `admin.py`: administración Django.

Endpoints agrupados:

- `/cart` y `/cart/<product_id>`: carrito.
- `/brands`, `/locations`, `/categories` y `/spec-attributes`.
- `/products`: catálogo, detalle, slug, imágenes, stock y especificaciones.
- `/products/<id>/reviews`: reseñas.
- `/orders`: creación y consulta de pedidos.
- `/orders/status` y `/orders/tracking/<tracking_code>`.
- `/admin/orders`: operaciones administrativas de pedidos.
- `/webhooks/wompi` y `/payments/wompi/status`.
- `/user/addresses`, `/user/favorites` y `/user/notifications`.
- `/user/fcm-tokens` y `/push-notifications/send`.

Reglas de negocio importantes:

- Los productos y reseñas pueden consultarse públicamente según el endpoint.
- El carrito, pedidos, direcciones, favoritos y notificaciones requieren sesión.
- El checkout valida términos y disponibilidad.
- Wompi usa firma, intención de pago e idempotencia para evitar pedidos
  duplicados.
- El pedido aprobado se crea o actualiza después de validar el evento de pago.
- El correo de confirmación debe enviarse como operación idempotente.

Pruebas relevantes: `ecommerce/tests.py` y scripts de flujo en
`BACKEND/scripts/`.

### 18.5 `gestion`: operación interna, inventario, cotizaciones y facturas

Ruta: `BACKEND/gestion/`

Modelos:

- `Cotizacion` y `CotizacionItem`.
- `Factura` y `FacturaItem`.

Responsabilidades:

- Resolver la sede del usuario.
- Consultar y modificar stock por sede.
- Crear y editar cotizaciones.
- Convertir cotizaciones en facturas.
- Crear, editar y anular facturas.
- Restaurar stock cuando corresponde.
- Filtrar recursos por sede y tipo de usuario.

Rutas bajo `/gestion/`:

- `mi-sede` y `asignar-sede`.
- `stock` y `stock/<product_id>`.
- `cotizaciones`, `cotizaciones/<id>` y `cotizaciones/<id>/convertir`.
- `facturas`, `facturas/<id>` y `facturas/<id>/anular`.

Archivos principales: `models.py`, `views.py`, `serializers.py`, `admin.py` y
`tests.py`.

### 18.6 `AppVisits`: visitas técnicas y reportes

Ruta: `BACKEND/AppVisits/`

Modelos:

- `ClienteVisita`: cliente, identificación, contacto y dirección.
- `VisitaTecnica`: técnico, cliente, tarea, fecha, hora, estado y valor.
- `ReporteVisita`: reporte final, equipo, diagnóstico, solución, pago y firma.
- `EvidenciaFotografica`: fotos y evidencias ordenadas.
- `VisitSyncReceipt`: idempotencia de sincronizaciones offline.

Rutas bajo `/visits/`:

- `<id>/sincronizar/`.
- `tecnicos/`.
- `/` y `<id>/` para CRUD.
- `<id>/iniciar/` y `<id>/finalizar/`.
- `<id>/fotos/` y `<id>/fotos/<foto_id>/`.
- `calendario/`.
- `<id>/pdf/`.

Archivos principales:

- `views.py`: CRUD, estados, agenda, fotos y PDF.
- `serializers.py`: visitas, reportes, clientes y evidencias.
- `permissions.py`: permisos por técnico, administrador y creador.
- `offline.py`: sincronización idempotente.
- `notifications.py`: correos y notificaciones de asignación/completado.
- `sync_version.py`: control de versión de sincronización.

Las visitas finalizadas no deben modificarse libremente. La finalización puede
generar reporte PDF, almacenar firma, enviar correo y crear notificación.

Pruebas relevantes: `AppVisits/tests.py` y `AppVisits/tests_offline.py`.

### 18.7 `crmChat`: CRM, chatbot y mensajería omnicanal

Ruta: `BACKEND/crmChat/`

Es el núcleo de conversaciones del sistema y sirve tanto al ecommerce público
como al panel de agentes.

Modelos:

- `CRMContact`, `ChannelIdentity`, `ChatSession`, `ChatMessage` y
  `ChatAttachment`.
- `MetaConnection`, `MetaFacebookPage`, `MetaInstagramAccount` y
  `ChannelIntegration`.
- `AssignmentQueue` y `QueueMember`.
- `WebhookEvent` y `ChatAuditEvent`.

Rutas bajo `/crm-chat/`:

- `sessions/`, `sessions/pending-count/`, `sessions/<id>/` y
  `sessions/<id>/messages/`.
- `bot/chat/` y `bot/sessions/<id>/messages/`.
- `queues/` y `queues/<id>/`.

Archivos principales:

- `views.py`: sesiones, mensajes, colas y bot.
- `tasks.py`: webhooks Meta, adjuntos, respuestas del bot, recibos y cierres.
- `ollama_service.py`: integración con Ollama.
- `assignment.py`: asignación automática.
- `realtime.py`: publicación de eventos.
- `consumers.py`: bandeja de agentes por WebSocket.
- `websocket_auth.py`: autenticación WebSocket mediante subprotocolo JWT.
- `routing.py`: ruta `/ws/crm-chat/`.

Reglas importantes:

- Las conversaciones pueden estar con bot, esperando agente, activas o cerradas.
- Las conversaciones externas se asocian a una integración y una identidad.
- Los mensajes externos usan `external_message_id` para idempotencia.
- La ventana de respuesta de WhatsApp y Facebook limita mensajes libres según la
  implementación actual.
- La desconexión de un canal conserva el historial.
- Las tareas Celery deben ser idempotentes y seguras ante reintentos.

### 18.8 `crmChat.apps.meta`

Ruta: `BACKEND/crmChat/apps/meta/`

Es la capa compartida de Meta.

- `oauth.py`: Facebook Login, state, intercambio de código, validación de token,
  descubrimiento de páginas/Instagram, selección y desconexión.
- `services.py`: Secret Store, Graph API, validación, firma, webhook,
  resolución de integración, normalización y salida.
- `views.py`: endpoints administrativos y webhook público.
- `webhooks.py`: `NormalizedMessage`, detección y normalización de canal.
- `serializers.py`: integraciones, páginas, Instagram y conexiones.
- `urls.py`: rutas unificadas.
- `models.py`: reexporta modelos Meta que viven en `crmChat.models`.

La autorización administrativa se limita a usuarios con `tipo_usuario` 1 o 4.
El webhook usa `AllowAny` y validaciones propias porque Meta no envía JWT del CRM.

### 18.9 `crmChat.apps.facebook`

Ruta: `BACKEND/crmChat/apps/facebook/`

Adaptador de Facebook Messenger/Pages.

- `services.py`: envío de texto, adjuntos y acciones del remitente.
- `webhooks.py`: parseo de eventos de Facebook.
- `serializers.py`: validación de mensajes de Messenger.
- `views.py`: alias `FacebookWebhookView` del webhook Meta.
- `urls.py`: `webhook/`.
- `models.py`: espacio de modelos específico, sin modelos principales propios.

La integración activa se identifica principalmente mediante `page_id` y se
relaciona con `MetaFacebookPage` y `MetaConnection`.

### 18.10 `crmChat.apps.instagram`

Ruta: `BACKEND/crmChat/apps/instagram/`

Adaptador de Instagram Professional/Business.

- `services.py`: OAuth Business Login, state, intercambio de código, envío de
  mensajes y acciones del remitente.
- `webhooks.py`: parseo de eventos Instagram.
- `serializers.py`: serializer Instagram basado en el contrato de Messenger.
- `views.py`: inicio OAuth, callback y webhook.
- `urls.py`: webhook, callback OAuth e inicio OAuth por integración.
- `models.py`: espacio de modelos específico, sin modelos principales propios.

Rutas específicas:

- `/meta/instagram/webhook/`.
- `/meta/instagram/oauth/callback/`.
- `/meta/instagram/integrations/<id>/oauth/start/`.

El frontend referencia las mismas rutas con prefijo `/api/meta/instagram/`.

### 18.11 `crmChat.apps.whatsapp`

Ruta: `BACKEND/crmChat/apps/whatsapp/`

Adaptador de WhatsApp Business Cloud API dentro del modelo de WhatsApp
Coexistence.

- `services.py`: texto, multimedia, interactivos y marcas de leído.
- `webhooks.py`: mensajes, estados, contactos, WABA ID y Phone Number ID.
- `serializers.py`: payloads interactivos de WhatsApp.
- `views.py`: alias `WhatsAppWebhookView` con canal forzado.
- `urls.py`: webhook específico.
- `models.py`: espacio de modelos específico, sin modelos principales propios.

Rutas específicas:

- `/meta/whatsapp/webhook/`.
- `/api/meta/whatsapp/webhook/`.

El servicio de salida utiliza `integration.phone_number_id` para construir la
ruta Graph API. La resolución entrante debe usar el Phone Number ID recibido en
`value.metadata.phone_number_id` y el WABA ID de `entry.id`. La implementación no
debe romper la operación del número desde WhatsApp Business ni asumir que todos
los mensajes se originan exclusivamente en el CRM. Además, la conexión debe
conservar la relación entre el número móvil existente, el WABA creado o vinculado
por Coexistence y la integración interna `ChannelIntegration`.

### 18.12 `administracion`: módulo heredado no activo

Ruta: `BACKEND/administracion/`

Contiene únicamente la estructura inicial de una aplicación Django:

- `models.py` sin modelos implementados.
- `views.py` sin vistas implementadas.
- `admin.py`, `apps.py` y migraciones iniciales.

No aparece en `INSTALLED_APPS` ni en las rutas principales actuales. Tratarlo como
módulo heredado hasta confirmar si existe código externo que lo importe.

### 18.13 `tienda`: módulo heredado no activo

Ruta: `BACKEND/tienda/`

Contiene una estructura inicial sin modelos ni vistas funcionales. No aparece en
`INSTALLED_APPS` ni en el enrutamiento actual. El ecommerce activo es
`ecommerce`, no `tienda`.

### 18.14 `scripts`: utilidades operativas y pruebas manuales

Ruta: `BACKEND/scripts/`

Incluye scripts para inspección de base de datos, diagnóstico de tokens,
migraciones puntuales, certificados, correo, Wompi, Ollama, chatbot, ecommerce,
permisos y autenticación.

No ejecutar scripts de diagnóstico o reparación en producción sin revisar sus
efectos. Algunos scripts son históricos y pueden asumir datos o endpoints que ya
no existan.

## 19. Catálogo de infraestructura backend

### HTTP y proxy

- Django atiende la API.
- Daphne atiende ASGI en Docker de desarrollo.
- Gunicorn aparece en dependencias/producción para WSGI según el despliegue.
- Nginx publica frontend, backend y media.
- El frontend utiliza normalmente `/api` como base URL.

### WebSocket

- Ruta: `/ws/crm-chat/`.
- Consumer: `CRMInboxConsumer`.
- Grupo: `crm_agents`.
- Solo usuarios autenticados con rol administrativo pueden conectar.
- El JWT se entrega en el subprotocolo WebSocket y no en la URL.
- Los eventos incluyen tipo, session ID y opcionalmente message ID.

### Celery y Redis

Colas y tareas relevantes:

- Procesamiento de eventos Meta.
- Descarga segura de adjuntos Meta.
- Recibos de lectura.
- Respuesta asíncrona del chatbot.
- Cierre de sesiones inactivas.
- Auditoría de vencimiento de tokens.
- Validación periódica de OAuth Meta.

### Servicios externos

- Meta Graph API.
- Instagram Graph/Business Login.
- Wompi.
- Firebase Cloud Messaging.
- Ollama.
- Cloudinary.
- SMTP/correo.
- Redis.

## 20. Inventario completo del frontend

### 20.1 Entrada y enrutamiento

Archivos:

- `frontend_U/src/main.tsx`: monta React, React Query, estilos globales y Leaflet.
- `frontend_U/src/App.tsx`: router principal, providers y separación tienda/admin.
- `frontend_U/src/index.css`: estilos globales del ecommerce.
- `frontend_U/src/admin/pages/styles/globals.css`: estilos del panel.

La aplicación usa `BrowserRouter` y carga muchas páginas con `lazy`/`Suspense`.
`PageBoundary` maneja errores y estados de carga.

Rutas públicas principales:

- `/`: inicio.
- `/productos`: catálogo.
- `/producto/:id`: detalle.
- `/carrito`: carrito protegido.
- `/checkout`: checkout con términos.
- `/checkout/resultado`: resultado del pago.
- `/orden-confirmada`: confirmación.
- `/seguimiento`: búsqueda de pedido.
- `/pedido/:trackingCode`: detalle por tracking.
- `/perfil` y `/perfil/editar`: perfil.
- `/mis-pedidos`: pedidos.
- `/favoritos`: favoritos.
- `/direcciones`: direcciones.
- `/notificaciones`: notificaciones.
- `/contacto`: contacto.
- `/login`: autenticación pública.
- `/restablecer-contrasena/:uid/:token`: restablecimiento.
- `/nosotros`: información corporativa.
- `/politica-tratamiento-datos`: política de datos.
- `/terminos-y-condiciones`: términos.

Rutas administrativas bajo `/admin/`:

- `/admin/login`, `/admin/dashboard`, `/admin/productos` y `/admin/categorias`.
- `/admin/marcas`, `/admin/ubicaciones`, `/admin/ordenes` y `/admin/usuarios`.
- `/admin/perfil`, `/admin/chat`, `/admin/chat/integraciones` y
  `/admin/visitas`.
- `/admin/gestion/cotizaciones` y `/admin/gestion/facturas`.

Existen redirecciones heredadas desde `/dashboard/*` hacia las rutas `/admin/*`.

### 20.2 Contextos públicos

#### `src/context/AuthContext.tsx`

Gestiona la sesión del ecommerce:

- Guarda `authToken`, `refreshToken` y usuario.
- Recupera el perfil al recargar.
- Renueva access tokens ante 401 mediante `src/services/api.ts`.
- Cierra sesión si falla la renovación.
- Expone `login`, `logout`, `updateUser` y estado de carga.

#### `src/context/CartContext.tsx`

Gestiona carrito persistente y sincronización con backend:

- Mantiene cache local por usuario.
- Carga el carrito del servidor.
- Importa el carrito local cuando el servidor está vacío.
- Maneja intención pendiente al pedir login.
- Agrega, elimina, actualiza y limpia productos.
- Valida cantidades y disponibilidad.

#### `src/context/FavoritesContext.tsx`

Gestiona favoritos: carga al autenticarse, agrega, elimina, comprueba si un
producto está marcado y expone `refresh`.

#### `src/context/pendingCartIntent.ts`

Guarda temporalmente el producto que el visitante intentó añadir antes de
autenticarse.

### 20.3 Protección y layout público

- `Layout.tsx`: estructura general, header y footer.
- `Header.tsx`: navegación, sesión y carrito.
- `Footer.tsx`: enlaces e información institucional.
- `StoreProtectedRoute.tsx`: exige sesión.
- `StoreTermsRoute.tsx`: exige aceptación de términos en checkout.
- `PageBoundary.tsx`: error boundary y carga.
- `ScrollToTop.tsx`: vuelve al inicio al cambiar de ruta.
- `GoogleMap.tsx`: mapa de ubicaciones.
- `ProductCard.tsx`: tarjeta de producto.
- `ProductReviews.tsx`: reseñas y calificaciones.
- `Chatbot.tsx`: chatbot de la tienda.
- `WompiCheckout.tsx`: widget de pago Wompi.

### 20.4 Páginas públicas

- `HomePage.tsx`: portada, categorías, destacados y ubicaciones.
- `ProductsPage.tsx`: listado y filtros.
- `ProductDetailPage.tsx`: detalle, imágenes, stock, especificaciones, reseñas y
  carrito.
- `CartPage.tsx`: cantidades, resumen y checkout.
- `CheckoutPage.tsx`: envío, método de pago y creación de orden/intento.
- `CheckoutResultPage.tsx`: resultado de Wompi.
- `OrderConfirmationPage.tsx`: confirmación de compra.
- `OrderTrackingPage.tsx`: consulta por código.
- `OrderDetailPage.tsx`: detalle y progreso.
- `ProfilePage.tsx` y `EditProfilePage.tsx`: perfil.
- `MyOrdersPage.tsx`: pedidos.
- `FavoritesPage.tsx`: favoritos.
- `AddressesPage.tsx`: direcciones.
- `NotificationsPage.tsx`: notificaciones.
- `LoginPage.tsx`: login y registro público.
- `ResetPasswordPage.tsx`: recuperación de contraseña.
- `ContactPage.tsx`: contacto.
- `NosotrosPage.tsx`: presentación corporativa.
- `DataPolicyPage.tsx`: tratamiento de datos.
- `TermsPage.tsx`: términos y condiciones.

### 20.5 Contexto administrativo

Ruta: `frontend_U/src/admin/`

#### `admin/context/AuthContext.tsx`

Gestiona la sesión administrativa separada del ecommerce:

- Usa `token`, `refresh` y `adminUser`.
- Valida expiración del JWT.
- Consulta el perfil administrativo.
- Exige usuario activo y rol `admin`.
- Escucha logout y cambios de almacenamiento.
- Cierra la sesión al expirar el token.

#### Componentes y tiempo real

- `AdminProtectedRoute.tsx`: protege rutas y roles.
- `DashboardLayout.tsx`: layout y navegación del panel.
- `ChannelBadge.tsx`: badge del canal de conversación.
- `useCRMWebSocket.ts`: conexión a `/ws/crm-chat/`, eventos y reconexión con
  backoff.

### 20.6 Páginas administrativas

- `LoginPage.tsx`: login.
- `RegisterPage.tsx`: registro administrativo.
- `DashboardPage.tsx`: resumen.
- `ProductsPage.tsx`: productos, imágenes, stock y especificaciones.
- `CategoriesPage.tsx`: categorías y árbol.
- `BrandsPage.tsx`: marcas y activación.
- `LocationsPage.tsx`: sedes y activación.
- `OrdersPage.tsx`: pedidos, estado y tracking.
- `UsersPage.tsx`: usuarios, estados, roles y cargos.
- `ProfilePage.tsx`: perfil administrativo.
- `GestionPage.tsx`: stock, cotizaciones y facturas.
- `VisitsPage.tsx`: agenda, visitas, fotos, reportes y calendario.
- `ChatPage.tsx`: bandeja, sesiones, mensajes, asignación, prioridad y cierre.
- `MetaIntegrationsPage.tsx`: OAuth, credenciales, validación, selección de
  páginas/Instagram y configuración de integraciones Meta.

### 20.7 Servicios administrativos

Todos usan `src/admin/services/admin_api.ts`, Axios y el JWT guardado como
`token`.

- `admin_api.ts`: Axios, base URL, timeout, Authorization y logout ante 401.
- `admin_auth.ts`: login, perfil, registro, logout y contraseña.
- `admin_products.ts`: productos, imágenes, especificaciones, stock y búsqueda.
- `admin_categories.ts`: categorías y árbol.
- `admin_brands.ts`: marcas.
- `admin_locations.ts`: sedes.
- `admin_orders.ts`: pedidos y tracking.
- `admin_users.ts`: usuarios, roles, estados, cargos y listados.
- `admin_gestion.ts`: stock, sede, cotizaciones y facturas.
- `admin_visits.ts`: técnicos, visitas, calendario, reportes y fotos.
- `admin_chat.ts`: sesiones, mensajes, colas y Meta.
- `admin_index.ts`: reexporta servicios y tipos.

Funciones de `admin_chat.ts`:

- Listar sesiones y contador pendiente.
- Cargar y enviar mensajes.
- Tomar, cerrar y priorizar conversaciones.
- Listar colas y asignar sesiones.
- Crear, modificar, validar y eliminar integraciones Meta.
- Iniciar OAuth de Instagram y Facebook/Instagram.
- Listar conexiones Meta y seleccionar páginas/cuentas.
- Desconectar conexiones.

### 20.8 Servicios públicos de API

- `services/api.ts`: cliente `fetch`, base URL `VITE_API_URL` o `/api`, JWT,
  refresh automático, deduplicación de GET y normalización de errores.
- `services/auth.ts`: login, registro, perfil, logout y actualización.
- `services/products.ts`: catálogo, detalle, slug, filtros y cache.
- `services/orders.ts`: pedidos, checkout, consulta y tracking.
- `services/payments.ts`: estado Wompi.
- `services/wompiCheckout.ts`: widget y opciones Wompi.
- `services/addresses.ts`: CRUD de direcciones.
- `services/favorites.ts`: favoritos.
- `services/locations.ts`: ubicaciones activas.
- `services/notifications.ts`: notificaciones.
- `services/reviews.ts`: reseñas.
- `services/chat.ts`: chat autenticado.
- `services/chatbotService.ts`: bot, historial y polling.
- `services/index.ts`: reexporta servicios comunes.

### 20.9 Tipos, utilidades y componentes UI

- `src/types/index.ts`: tipos públicos.
- `src/admin/types/index.ts`: tipos administrativos, roles y auth.
- `src/lib/utils.ts` y `src/admin/lib/utils.ts`: utilidades.
- `src/hooks/useMobileDrawer.ts`: drawer móvil.
- `src/components/ui/`: componentes locales actuales: badge, button, card,
  dialog, input, label, select, table y textarea.
- `components/ui/`: colección adicional heredada/generada; verificar antes de
  importarla porque no toda está dentro de `src/`.

### 20.10 Dependencias y comandos frontend

El frontend está definido en `frontend_U/package.json`.

Dependencias principales:

- React 19, React DOM y React Router DOM.
- Axios y TanStack React Query.
- Material UI y Emotion.
- React Hook Form y Zod.
- Leaflet y React Leaflet.
- Lucide React.
- Tailwind utilities y Radix UI.
- Vite y TypeScript.

Comandos:

- `npm run dev`: servidor Vite.
- `npm run build`: TypeScript y build Vite.
- `npm run preview`: previsualización.
- `npm run lint`: ESLint, si está configurado.

Docker monta `frontend_U` en `/app`, expone el puerto 3000 y usa
`VITE_API_URL=/api` en desarrollo.

## 21. Flujo completo de datos

### Compra pública

```text
Navegador -> React StoreRoutes -> services de catálogo/carrito/pedidos
-> API Django ecommerce -> Product/CartItem/Order/WompiPaymentIntent
-> Wompi cuando aplica -> webhook o consulta de estado -> pedido/notificación
```

### Chatbot del ecommerce

```text
Chatbot.tsx -> chatbotService.ts -> /crm-chat/bot/chat/
-> BotChatView -> OllamaService y contexto comercial
-> ChatSession y ChatMessage
```

### Bandeja de agentes

```text
ChatPage.tsx -> admin_chat.ts -> /crm-chat/sessions/
-> SessionListCreateView/MessageListCreateView -> ChatSession/ChatMessage
-> /ws/crm-chat/ -> useCRMWebSocket
```

### Meta entrante

```text
Meta -> webhook -> MetaWebhookView -> firma y estructura -> WebhookEvent
-> Celery -> parser del canal -> ChannelIntegration
-> CRMContact/ChannelIdentity -> ChatSession/ChatMessage -> bot o asesor
```

### Meta saliente

```text
ChatMessage -> dispatch_outbound_message
-> servicio Facebook/Instagram/WhatsApp -> Graph API
-> actualización del mensaje y estados
```

## 22. Puntos de integración que deben verificarse

- El frontend administrativo usa `token`, mientras el frontend público usa
  `authToken`/`refreshToken`; no mezclarlos.
- La ruta de cambio de contraseña de `admin_auth.ts` debe compararse con las
  rutas reales de `usuarios/account_views.py`.
- La operación de tracking de `admin_orders.ts` debe verificarse contra las rutas
  reales de `ecommerce/urls.py`.
- `admin_chat.ts` debe coincidir con el contrato actual de serializers Meta,
  especialmente estado, validación, errores y desconexión.
- La ruta OAuth de Instagram debe coincidir exactamente entre `.env`, Meta
  Developers, backend, Nginx y frontend.
- La duplicación `/meta/` y `/api/meta/` debe conservarse solo si el proxy la
  necesita.
- `administracion` y `tienda` no están activas actualmente; no deben confundirse
  con `ecommerce` o `gestion`.
- Las pruebas usan SQLite cuando detectan `test`; esto no sustituye validar
  migraciones contra MySQL/PostgreSQL.

## 23. Documentación y archivos de referencia

Documentos existentes que contienen decisiones previas:

- `README_WOMPI.md`
- `GUIA_RAPIDA_WOMPI.md`
- `SOLUCION_ERROR_422_WOMPI.md`
- `PRUEBAS_WOMPI.md`
- `CHATBOT_INTEGRATION.md`
- `GUIA_PRUEBAS_CHATBOT.md`
- `CONFIGURACION_CHATBOT_PRODUCCION.md`
- `apis_grapApiMetea.md`
- `docs/URLS_Y_CONFIGURACION_ENTORNOS.md`
- `DEPLOY_PRODUCTION.md`
- `CORRECCIONES_SEGURIDAD_APP.md`
- `ARQUITECTURA_VISUAL.md`
- `documentacion.md`

Antes de duplicar una decisión técnica, revisar si ya está documentada en uno de
estos archivos. Si una implementación cambia el comportamiento, actualizar el
documento correspondiente y este contexto.

## 24. Procedimiento recomendado para retomar el proyecto

1. Leer este archivo completo.
2. Revisar `git status` antes de modificar archivos.
3. Confirmar el entorno y las variables disponibles sin imprimir secretos.
4. Revisar rutas y modelos relacionados con el módulo a cambiar.
5. Ejecutar pruebas específicas antes de implementar.
6. Cambiar primero backend y migraciones cuando el contrato de datos lo exija.
7. Actualizar frontend y tipos después de confirmar el contrato de API.
8. Ejecutar pruebas backend dentro de Docker.
9. Ejecutar `npm run build` y `npm run lint` cuando aplique.
10. Revisar diff y migraciones antes de entregar.
11. Actualizar este archivo si cambia la arquitectura, las rutas o los flujos.

## 25. Regla obligatoria de ejecución Docker

Todo el proyecto se ejecuta dentro de Docker. No ejecutar directamente en el
host comandos del frontend o backend, incluyendo:

- `npm run dev`
- `npm run build`
- `npm run lint`
- `python manage.py ...`
- `pytest`
- `celery`
- `daphne`
- `pip install`
- `npm install`

Las comprobaciones, pruebas, migraciones, instalaciones y comandos operativos
deben ejecutarse dentro del contenedor correspondiente usando Docker Compose y
la configuración existente del proyecto.

Antes de ejecutar cualquier comando:

1. Identificar el servicio correcto en el archivo Compose activo.
2. Usar `docker compose exec` o `docker compose run` según corresponda.
3. No ejecutar el frontend ni el backend directamente desde Windows/PowerShell.
4. No levantar servicios adicionales fuera de Docker.
5. No modificar volúmenes, bases de datos ni contenedores de forma destructiva.

Si Docker no está disponible o el contenedor requerido no está iniciado, detener
la ejecución y reportar la limitación en lugar de ejecutar una alternativa local.
