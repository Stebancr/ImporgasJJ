# Remitente exclusivo del informe de visita técnica

Fecha de validación: 21 de octubre de 2026. Rama: `dev`.
Commit inicial: `e1dae2b76e96430acd7b4ec53031a6782dd6c039`.
El commit local que incorpora este informe contiene el cambio; consultar
`git log -1` para su identificador final. No hubo push, PR ni despliegue.
`main` permaneció en `d61725ab7463cd1bebae5368d97ef3788580d09a`.

## Cambio limitado al remitente

Antes, `transactional_mail.service.send()` construía todos los mensajes con
`settings.DEFAULT_FROM_EMAIL`. Ahora utiliza `configuration.sender_for(kind)`:

- `visit`: dirección de `SERVER_EMAIL_APLICACION` y nombre visible
  **Servicio Técnico ImporGas JJ**, codificado con `email.utils.formataddr` UTF-8.
- Los demás tipos: el mismo `DEFAULT_FROM_EMAIL` anterior.

Configuración no secreta:

```dotenv
SERVER_EMAIL_APLICACION=serviciotecnico@imporgasjj.com
```

La carga está centralizada en `core/settings.py`: admite ausencia sin impedir el
arranque y elimina un par de comillas exteriores, tanto para dotenv como para
valores recibidos mediante `env_file` con formato raw. El servicio valida que sea
una dirección simple válida y rechaza nombres incluidos, valores vacíos o
inyección de encabezados. No hay dirección de respaldo para visitas.

La variable existía en `.env`, pero el runtime de desarrollo recibía `.envdev`
y no la tenía. Se añadió su paso explícito en Compose para backend, los dos
workers y Beat, siguiendo el mecanismo ya utilizado para SMTP. No se modificó
ningún archivo privado de entorno ni la autenticación de Brevo.

## Evidencia del encabezado real

Dentro del backend Docker se construyó un `EmailMultiAlternatives` sin enviarlo,
se serializó a MIME y se volvió a interpretar con el parser estándar de email.
El resultado decodificado fue exactamente:

```text
From: Servicio Técnico ImporGas JJ <serviciotecnico@imporgasjj.com>
```

Se comprobó que Django recibe la dirección sin comillas y que el worker recibe
la misma variable. La inspección no utilizó destinatarios reales ni SMTP DATA.
Las pruebas del servicio completo usan locmem y destinatarios sintéticos.

## Contenido y flujos conservados

No se modificaron `message.html`, `message.txt`, el contexto del correo, logo,
documentos, generación/almacenamiento de PDF, enlaces protegidos ni las tareas.
La comparación del mismo evento antes/después verificó igualdad de:

- Asunto, texto plano, HTML y todas las partes MIME decodificadas.
- Logo, Content-ID, nombre y contenido de los adjuntos existentes.
- To, CC, BCC, Reply-To y Message-ID.
- Enlace protegido al PDF, nombre del archivo y hash de sus bytes.

El PDF de visita continúa disponible mediante el enlace protegido existente; no
se añadió ni retiró un adjunto PDF. Se conserva el mecanismo de envío después de
verificar el documento, las claves de idempotencia y el presupuesto de reintentos.
Un remitente ausente o inválido deja el evento fallido y la visita/PDF intactos.
El error persistido y registrado es únicamente:

```text
visit_sender_configuration_invalid_SERVER_EMAIL_APLICACION
```

No se registra el valor inválido ni información SMTP. El reintento manual
existente utiliza el mismo evento y nuevo remitente. Un envío enviado no se
duplica; si un worker se interrumpe durante SMTP se conserva la política existente
de estado incierto y revisión manual, sin reenvío ciego.

## Otros correos y SMTP

Se compararon huellas agregadas privadas de la configuración runtime antes,
con el Compose nuevo y después de recrear los servicios. Resultado: **idéntica**
para EMAIL_HOST, EMAIL_PORT, EMAIL_USE_SSL/TLS, EMAIL_HOST_USER,
EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL, SERVER_EMAIL y TRANSACTIONAL_REPLY_TO.
No se imprimieron ni versionaron valores de autenticación.

Las pruebas verifican que compra conserva el remitente general, recuperación de
contraseña usa el mismo DEFAULT_FROM_EMAIL y `mail_admins` conserva SERVER_EMAIL.
No se utiliza la nueva variable en esos flujos ni en CRM.

## Brevo y DNS: resultado y limitación

Comando Docker de diagnóstico, sin RCPT, DATA ni envío:

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps backend \
  python manage.py check_transactional_smtp --technical-visits
```

Resultado: configuración local válida; negociación STARTTLS bloqueada por
**error de certificado 19: self-signed certificate in certificate chain**.
La comprobación se detuvo **antes de AUTH y MAIL FROM**. No hay respuesta de Brevo
aceptando o rechazando al remitente que pueda reportarse. No se deshabilitó TLS,
no se cambió el SMTP y no se enviaron correos reales.

Consulta DNS pública de solo lectura ejecutada desde Docker:

| Registro | Resultado observado |
|---|---|
| TXT imporgasjj.com | Un SPF publicado |
| TXT _dmarc.imporgasjj.com | DMARC publicado |
| CNAME brevo1._domainkey.imporgasjj.com | Publicado, destino DKIM |
| CNAME brevo2._domainkey.imporgasjj.com | Publicado, destino DKIM |
| TXT mail._domainkey.imporgasjj.com | NXDOMAIN; selector alternativo no publicado |

El SPF consultado no incluye explícitamente los includes Brevo comprobados.
Eso **no demuestra un error**: Brevo puede utilizar su infraestructura para SPF
y Return-Path con IP compartida. No se inventaron registros ni se modificó DNS.
Los CNAME publicados no prueban por sí solos su asociación a esta cuenta SMTP.
No hay acceso API de Brevo configurado para consultar el estado privado del
remitente. Su autorización queda **pendiente de comprobación en el panel**.

### Acciones manuales pendientes

1. Revisar la cadena TLS que se presenta a Docker para `smtp-relay.brevo.com:587`.
   Si existe inspección SMTP local, corregir su confianza o excepción específica;
   conservar la verificación TLS activa. No desactivar todo el antivirus ni
   sustituir credenciales para resolver un error de certificado.
2. En Brevo: **Settings → Senders, Domains, IPs → Senders**, comprobar/crear el
   remitente técnico con el nombre y correo indicados. Si solicita verificación,
   completarla en el panel; no compartir el código por el chat.
3. En **Settings → Senders, Domains, IPs → Domains**, comprobar que
   `imporgasjj.com` esté autenticado para esta cuenta y contrastar sus registros
   exactos con los que proporcione Brevo. No se deducen ni sustituyen registros
   de otra cuenta. Un dominio autenticado puede verificar automáticamente sus
   remitentes, según el flujo del panel.
4. Repetir el comando sin envío después de resolver TLS. Incluso un MAIL FROM
   250 no prueba entrega ni verificación completa del remitente.
5. Si posteriormente se autoriza un envío controlado, revisar el correo recibido:
   From efectivo, Return-Path y Authentication-Results (SPF/DKIM/DMARC). Hasta
   entonces no se afirma que Brevo no reescriba From ni que el Return-Path final
   haya sido validado. No se envió ese correo durante esta tarea.

Referencias oficiales consultadas:

- [Crear un remitente en Brevo](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email).
- [Autenticar el dominio](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC).
- [Dominio, SPF y Return-Path](https://help.brevo.com/hc/en-us/articles/35852083084178-Domain-setup-for-better-email-deliverability).

## Pruebas y servicios

Pruebas ejecutadas en Docker con PostgreSQL aislado:

```sh
python manage.py test transactional_mail AppVisits usuarios ecommerce shipping --noinput
docker compose -f docker-compose.dev.yml config --quiet
```

La suite final cubre configuración presente/ausente/vacía/inválida, eliminación de
comillas, MIME real y contenido idéntico, PDF disponible/no disponible, guardados
repetidos, reintento manual, caída SMTP, remitente rechazado, worker interrumpido,
compra, recuperación de contraseña y alerta del servidor. Ninguna prueba envía
correo externo. Los errores de pruebas negativas son inyectados y sanitizados.

Resultado final: **284 pruebas descubiertas, ejecutadas y aprobadas; cero fallidas
y cero omitidas**.

Los servicios locales backend, frontend, PostgreSQL, Redis, workers, Beat, Nginx,
WhatsApp y Ollama quedaron running, con cero reinicios automáticos. PostgreSQL,
Redis, WhatsApp y Ollama tenían health check healthy. Workers respondieron
ping/pong y frontend respondió HTTP 200 a través de Nginx. Se recrearon solo los
cuatro servicios Django de desarrollo para recibir la variable, tras comprobar
que no existían eventos de correo pendientes, fallidos o enviándose.

Logs de esos cuatro servicios, ventana revisada de cinco minutos: cero
ERROR/CRITICAL/Traceback. Sin credenciales, tokens ni enlaces privados expuestos.
No hubo migraciones nuevas, cambios de base/media de producción ni eliminación
de volúmenes. `dist` y el script local ajeno permanecieron fuera del commit.

## Archivos del cambio

- `BACKEND/core/settings.py`: configuración específica y normalización.
- `BACKEND/transactional_mail/configuration.py`: helper único de remitente.
- `BACKEND/transactional_mail/service.py`: selección de From y error específico.
- `BACKEND/transactional_mail/management/commands/check_transactional_smtp.py`:
  opción de diagnóstico del remitente técnico, sin envío.
- `docker-compose.dev.yml`, `.env.example`: paso y ejemplo de la variable.
- `BACKEND/transactional_mail/test_visit_sender.py`: regresiones específicas.
- Configuración de pruebas existente en `transactional_mail/tests.py` y
  `AppVisits/tests.py`: remitente sintético, sin cambios en su comportamiento.
- Este informe. No se modificaron las plantillas, los documentos ni la cola.
