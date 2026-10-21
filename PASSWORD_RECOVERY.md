# Recuperación de contraseña del e-commerce

## Alcance y configuración

Implementado exclusivamente en `dev`, desde `341805d32b5b6e1211d0c0c98ce103b5129ceb33`.
Sin push, PR, cambios en main ni despliegue. Los archivos locales previos de `frontend_U/dist` y `verify_live_meta_handshakes.py` quedan fuera de estos commits.

Configuración del backend:

```dotenv
SERVER_EMAIL_NOREPLY=no-reply@example.com
# Solo pruebas SMTP de desarrollo: lista explícita separada por comas.
PASSWORD_RESET_ALLOWED_RECIPIENTS=
FRONTEND_PUBLIC_URL=http://localhost
```

En producción, `FRONTEND_PUBLIC_URL` debe ser el dominio HTTPS público autorizado. El servicio rechaza bases de URL inseguras en producción y nunca construye el enlace desde Host, Referer ni parámetros del cliente. La configuración existente de SMTP, compras, visitas técnicas, Reply-To comercial y alertas no se sustituye. Compose de desarrollo transmite las nuevas variables a los procesos Django; no se modificó el archivo privado `.env`.

`SERVER_EMAIL_NOREPLY` debe ser una dirección sin nombre visible. Django elimina un par de comillas externas cuando provienen de un `env_file` raw. El helper único añade el nombre **ImporGas JJ - No responder**. Ausente, vacía o inválida: el evento queda fallido, sin usar el remitente comercial como fallback.

Con DEBUG y SMTP real, una lista vacía de `PASSWORD_RESET_ALLOWED_RECIPIENTS` bloquea el envío. Para pruebas posteriores, el operador debe autorizar explícitamente el destinatario en su configuración privada y recrear backend/worker. No confundir esta protección con una verificación de remitente en Brevo. Con backend locmem no se envía correo externo. En producción no se aplica esta lista de pruebas.

## Rutas y flujo

Frontend público:

- `/recuperar-contrasena`: solicitud desde el enlace del login.
- `/restablecer-contrasena#uid=…&token=…`: validación y nueva contraseña.
- La ruta anterior con parámetros de ruta permanece reconocida, pero los enlaces nuevos usan exclusivamente fragmento. Los enlaces anteriores deben solicitarse nuevamente porque cambia el generador de seguridad.

API pública, métodos POST JSON:

- `/api/user/password/reset/request`: `{ "email": "cliente@example.com" }`.
- `/api/user/password/reset/validate`: identificador seguro y token, únicamente en el cuerpo.
- `/api/user/password/reset/confirm`: identificador, token, `new_password` y `confirm_password`, únicamente en el cuerpo.

Nginx elimina `/api/` al reenviar a Django. El fragmento del navegador no se transmite en solicitudes HTTP ni en Referer. No registrar los cuerpos de estas solicitudes en proxies/APM.

Una solicitud de correo con formato válido recibe la misma respuesta para cuenta existente, desconocida, inactiva, duplicada o fallo de envío. Una dirección ambigua entre cuentas no recibe correo. La cuenta debe ser cliente activo, con perfil activo y contraseña utilizable. La dirección solicitada debe coincidir con el correo del perfil; no se utiliza un alias para enviar a otra dirección.

La entrega se encola en Celery después del commit; los argumentos contienen solo el UUID del evento. El registro guarda referencia al usuario, HMAC del destinatario, versión, fecha y resultado. No guarda contraseña, token, correo en texto ni enlace. Los tokens se generan al entregar, en memoria. Una entrega encolada por más de la vigencia se descarta.

El enlace se valida antes de mostrar el formulario. El backend aplica los validadores configurados de Django, incluyendo similitud con correo y nombre del modelo personalizado. `set_password()` almacena el hash. Se incrementa `password_version`, se revocan tokens DRF y JWT previos y las sesiones Django dejan de coincidir con el hash de autenticación. No se inicia sesión automáticamente.

## Vigencia, uso único y límites

- Vigencia existente conservada: `PASSWORD_RESET_TIMEOUT=3600` segundos.
- El generador firmado de Django incluye contraseña, último login, versiones de seguridad, correo, estado y rol.
- Cada nueva solicitud aceptada incrementa `password_reset_version`: invalida los enlaces anteriores.
- La confirmación bloquea la fila de credenciales y vuelve a validar el token. El cambio invalida todos los enlaces previos, incluso ante reintentos.
- Por correo normalizado: una solicitud cada 60 segundos y máximo 3 por ventana de una hora. La respuesta sigue siendo neutral al suprimir envíos.
- Por IP: máximo 10 solicitudes por hora, incluso para correos inexistentes. Exceso: HTTP 429, independiente de existencia de cuenta.
- Validación y confirmación: límite existente `password_reset_confirm`, por defecto 10/minuto, además de límites globales DRF.
- Las claves por correo/IP usan HMAC. Producción utiliza Redis compartido. Los tests usan caché aislada y la limpian al terminar.
- Se confía únicamente en X-Real-IP sobrescrito por Nginx, con REMOTE_ADDR de respaldo; no en una cadena X-Forwarded-For aportada por el cliente. Mantener el backend detrás del proxy confiable; no exponerlo directamente a Internet.

No hay reenvío automático tras un resultado incierto de SMTP ni al repetir una tarea ya procesada. Los estados son pending/sending/sent/failed/skipped/uncertain. Un worker interrumpido mientras entrega requiere revisión; una solicitud nueva genera otra versión segura. Esto evita reenvíos ciegos. Definir retención operativa para esta auditoría antes del despliegue.

## Migración

`usuarios.0008_password_recovery_audit` añade `Credenciales.password_reset_version` y `PasswordResetDelivery`. Es aditiva; no modifica contraseñas, roles, datos históricos ni media. Probada primero en PostgreSQL aislado y luego aplicada solo a desarrollo. Antes de aplicar localmente se creó un dump de desarrollo y se inspeccionó con `pg_restore --list`: `.artifacts/password-recovery-before-dev.dump`, 428437 bytes, excluido de Git. No se restauró ninguna base ni se accedió a producción.

## Validación realizada, 2026-10-21

Todo el runtime y las pruebas se ejecutaron en Docker:

```powershell
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py test ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios --noinput
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py makemigrations --check
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py showmigrations
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py migrate --plan
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py migrate --noinput
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm frontend sh -c 'npx tsc --noEmit && npx vite build --outDir /tmp/password-recovery-final --configLoader runner'
```

El Compose QA es una herramienta local ignorada; para reproducir fuera de este PC debe crearse un Compose aislado equivalente con PostgreSQL, Redis, backend y frontend, sin credenciales reales ni volúmenes compartidos con producción.

Resultados:

- **489 tests descubiertos y ejecutados, 489 aprobados, 0 fallidos, 0 omitidos**: productos, TCC simulado, direcciones, checkout/Wompi simulado, usuarios/trabajadores, CRM, Meta/WhatsApp simulados, chats, adjuntos, plantillas, correos, visitas y PDFs.
- TypeScript y Vite: correctos, salida exclusivamente bajo `/tmp`; no se escribió dist.
- Navegador Playwright: login → solicitud neutral → correo locmem real → enlace → validación → coincidencia de contraseñas → cambio → login viejo rechazado/nuevo aceptado → enlace reutilizado rechazado. Escritorio y móvil, más error de red con datos conservados y protección contra doble envío.
- MIME generado: From correcto, único To, CC/BCC vacíos, asunto, HTML, texto plano, logo CID y enlace absoluto. No se probó una aplicación de correo real porque SMTP quedó bloqueado antes de aceptar el mensaje.
- WebSocket real Nginx/ASGI/JWT/Redis: handshake y ping/pong correctos con cuenta QA, sin mensajes externos.
- Celery real: tarea de recuperación encolada y procesada como skipped con evento sin destinatario; no pudo enviar correo.
- Comparación con la configuración previa: EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, TLS, puerto, remitente de compras, remitente técnico, SERVER_EMAIL y Reply-To sin cambios.
- Logs recientes de desarrollo: 0 coincidencias con credenciales conocidas, 0 enlaces de recuperación, 0 líneas ERROR/CRITICAL/Traceback y 0 respuestas HTTP 5xx en el periodo revisado. Los tests negativos incluyen errores de proveedor, timeout y respuestas 400/401/429 esperadas.

La fixture `python -m usuarios.recovery_e2e --isolated-password-test` exige `CRM_TEST_POSTGRES=1`, crea una base de test única y usa correo locmem. Su ruta interna `/__qa/mail` existe solo en esa fixture y contiene únicamente mensajes sintéticos; nunca está registrada en Django ni debe exponerse fuera de Docker QA. La prueba de navegador es `frontend_U/tests/password-recovery.cjs`, con `QA_RESET_API` apuntando a esa fixture.

## Prueba SMTP autorizada y bloqueo pendiente

- Cuenta de prueba: el destinatario expresamente autorizado por el solicitante (dirección omitida de la documentación versionada). No existía; se creó exclusivamente en desarrollo. Contraseña inicial aleatoria, almacenada solo con hash y nunca mostrada. No se duplicó una cuenta ni se sobrescribió una contraseña existente.
- Único intento real: **2026-10-21 13:47:43 America/Bogota**, evento `8a667df4-7738-4384-9a55-191d288a4f1d`.
- From configurado: **ImporGas JJ - No responder <noreply@imporgasjj.com>**. Único destinatario autorizado, sin CC/BCC; URL local de desarrollo, vigencia de una hora.
- Resultado: **failed / smtp_tls_certificate**. Diagnóstico sin otro envío: **TLS error 19, self-signed certificate in certificate chain**.
- La sesión falló antes de autenticar/enviar DATA. No existe aceptación de Brevo ni identificador de entrega del proveedor. No se envió un segundo correo. La recepción real sigue pendiente; no se afirma que el usuario haya recibido el mensaje.
- DNS consultado desde Docker: SPF presente; selectores CNAME `brevo1._domainkey` y `brevo2._domainkey` presentes; DMARC presente. Esto no confirma autorización privada de la cuenta, alineación SPF efectiva, firma DKIM de un mensaje ni Return-Path, que requieren una entrega real y sus cabeceras.

Acciones pendientes:

1. Revisar la inspección SMTP/TLS del equipo/red y la cadena de confianza del contenedor. Mantener validación TLS; no usar conexiones sin verificación como solución.
2. En Brevo, revisar **Configuración → Remitentes, dominios e IP dedicadas**, confirmar la dirección configurada y la autenticación del dominio. Usar los registros exactos que proporcione Brevo; no cambiar DNS automáticamente ni inventar valores.
3. Cuando TLS funcione, la sonda `python manage.py check_transactional_smtp --password-reset` verifica STARTTLS/autenticación/MAIL FROM sin RCPT ni DATA. Un MAIL FROM 250 por sí solo no acredita recepción ni verificación de remitente.
4. Antes de repetir el correo real, obtener autorización para ese nuevo intento y configurar el destinatario permitido. Solicitar un nuevo enlace; no reutilizar un token almacenado ni modificar la contraseña inicial manualmente.
5. Confirmar recepción, cabeceras reales From/Return-Path/SPF/DKIM y apertura del enlace en este PC con Docker activo. Los enlaces localhost no abren el entorno local desde otro dispositivo.

La orden `test_password_recovery_smtp --recipient <autorizado> --send` es exclusiva de desarrollo, requiere URL local y rechaza cuentas existentes sin modificarlas. Crea solo una cuenta nueva, limita internamente el destinatario y realiza una entrega explícita por el mismo servicio, sin imprimir enlaces ni contraseñas. No volver a ejecutarla para la cuenta ya creada: el reintento debe revisarse mediante el flujo normal cuando se autorice.

## Servicios

Todos los servicios de desarrollo revisados estaban running, con 0 reinicios. PostgreSQL, Redis, WhatsApp y Ollama tenían healthcheck healthy. Backend, frontend, worker, chatbot, beat y Nginx no definen healthcheck propio: no se los presenta como healthy por esa razón.

| Servicio | Validación funcional |
|---|---|
| Backend | API raíz HTTP 200, migración sin pendientes, generación MIME y endpoints probados |
| Frontend | Rutas de solicitud y cambio HTTP 200 por Nginx; Playwright y build correctos |
| PostgreSQL | SELECT 1 y migración aditiva aplicada |
| Redis | Escritura/lectura de caché; Celery y WebSocket reales |
| Celery worker / chatbot | Ambos responden inspect ping; nueva tarea procesada sin SMTP |
| Celery beat | Proceso activo, sin errores recientes; no se alteró su programación |
| Nginx | nginx -t correcto, rutas públicas y WebSocket verificados |
| WhatsApp | /health HTTP 200; no se enviaron mensajes |
| Ollama | /api/tags HTTP 200; no se generaron conversaciones |

Pendiente externo: entrega real y verificación del remitente en Brevo. La implementación y las pruebas locales no equivalen a confirmar esa entrega.

## Archivos y commits locales

- `19c5cd23`: backend, seguridad, remitente específico, migración y pruebas.
- `5054e140`: páginas públicas y pruebas integrales de navegador.
- La documentación se conserva en un tercer commit local. Consultar el HEAD final con `git log -3 --oneline`; ninguno se publicó.

Archivos de backend/configuración:

```text
.env.example
docker-compose.dev.yml
BACKEND/core/settings.py
BACKEND/usuarios/models.py
BACKEND/usuarios/account_views.py
BACKEND/usuarios/urls.py
BACKEND/usuarios/password_recovery.py
BACKEND/usuarios/tasks.py
BACKEND/usuarios/migrations/0008_password_recovery_audit.py
BACKEND/usuarios/management/__init__.py
BACKEND/usuarios/management/commands/__init__.py
BACKEND/usuarios/management/commands/test_password_recovery_smtp.py
BACKEND/usuarios/templates/usuarios/password_reset.html
BACKEND/usuarios/templates/usuarios/password_reset.txt
BACKEND/usuarios/test_account.py
BACKEND/usuarios/test_password_recovery.py
BACKEND/usuarios/recovery_e2e.py
BACKEND/transactional_mail/management/commands/check_transactional_smtp.py
BACKEND/transactional_mail/test_visit_sender.py
```

Archivos de interfaz/documentación:

```text
frontend_U/src/App.tsx
frontend_U/src/app/pages/LoginPage.tsx
frontend_U/src/app/pages/ForgotPasswordPage.tsx
frontend_U/src/app/pages/ResetPasswordPage.tsx
frontend_U/tests/password-recovery.cjs
PASSWORD_RECOVERY.md
```
