# Correos transaccionales Brevo

Validación local: 19 de octubre de 2026, rama `dev`, base `e46de09c`.
Producción no se ha modificado ni desplegado en esta tarea. Se conservaron los
cambios previos del árbol de trabajo; no se creó ningún commit ni push.

## Configuración y causa del fallo

La configuración mezclaba `RELAYHOST`, `SMTP_USER`, `SMTP_PASSWORD` y
`EMAIL_HOST_USER`. Django utiliza ahora exclusivamente `EMAIL_*`; el usuario
SMTP y la clave SMTP suministrados se normalizaron en el archivo privado `.env`,
sin copiarlos a código ni ejemplos. `.env` está excluido por Git.

Variables normalizadas: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`DEFAULT_FROM_EMAIL`, `SERVER_EMAIL`, `EMAIL_TIMEOUT`. Se añadieron
`TRANSACTIONAL_REPLY_TO`, `TRANSACTIONAL_EMAIL_ENABLED`,
`TRANSACTIONAL_EMAIL_ALLOWED_RECIPIENTS` y `PUBLIC_API_URL`.

En desarrollo Compose pasa estos valores al backend y los workers. El backend
es la fuente de las URLs; `FRONTEND_PUBLIC_URL` define el sitio y `PUBLIC_API_URL`
la API. En producción el Compose existente carga su archivo privado de entorno.
Las plantillas no contienen hosts de Docker ni dominios de entorno fijos.
No quedan variables SMTP duplicadas. Se detectaron duplicados previos de
`META_GRAPH_API_VERSION` y `META_WEBHOOK_VERIFY_TOKEN`, ajenos al correo; se
conservaron sus valores y orden para no alterar la integración Meta.

El primer bloqueo fue la sustitución del certificado SMTP por Norton. Tras
desactivar esa inspección apareció otro problema reproducible: el endpoint
`smtp-relay.brevo.com` presentó un certificado válido de Let's Encrypt cuyo SAN
incluía `smtp-relay.sendinblue.com`, pero no `smtp-relay.brevo.com`.

Se comprobó el alias histórico de Brevo, también documentado en la
[integración SMTP de GitLab](https://github.com/gitlabhq/omnibus-gitlab/blob/master/doc/settings/smtp.md).
La configuración privada local usa `EMAIL_HOST=smtp-relay.sendinblue.com`, puerto
587, STARTTLS y validación completa de cadena y nombre. Pasaron la autenticación,
MAIL FROM, los dos envíos y la recepción confirmada por el usuario. No se
desactivó TLS ni se añadió una autoridad de certificación ajena.

La documentación actual de [Brevo SMTP](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP)
indica `smtp-relay.brevo.com`. Al preparar producción, comprobar el certificado
del host seleccionado con `check_transactional_smtp` desde el contenedor de ese
entorno. El alias local no implica que producción presente el mismo fallo.

## Eventos y persistencia

- Compra: aprobación Wompi validada por el backend y materialización del pedido.
  El frontend no decide si se envía. Estados pendientes o rechazados no generan
  confirmación.
- Visita: finalización y generación/persistencia del PDF existente. Si falla el
  documento se conserva el evento para reintento, sin enviar enlaces rotos.
- `transactional_mail.Delivery` conserva un evento único por tipo y objeto,
  destinatario, estados, intentos acumulados, fechas, error sanitizado y
  Message-ID estable. Los indicadores de correo existentes de pedidos/visitas
  siguen actualizándose para compatibilidad.
- Celery envía fuera de la transacción de negocio; un fallo SMTP no revierte un
  pago ni una visita. Si Redis está caído, el evento queda pendiente; Beat lo
  recupera cada dos minutos.
- Máximo inicial de tres intentos, espera de 5 minutos por número de intento.
  Un administrador puede habilitar tres intentos adicionales de un fallido,
  conservando el contador histórico. Enviados y cancelados no se reenvían.
- Una desconexión, timeout durante envío o interrupción del worker puede dejar
  la aceptación SMTP incierta. Se marca `uncertain` y requiere revisión manual;
  no se reintenta automáticamente. SMTP no garantiza exactamente una entrega
  si se pierde la confirmación del servidor.
- Django SMTP no devuelve el identificador interno Brevo: `provider_id` queda
  vacío; se conserva Message-ID para correlacionar con el historial del proveedor.

## Plantillas y documentos

`message.html` y `message.txt` comparten datos, importes COP, fechas de Colombia,
encabezado, logo PNG incrustado mediante CID y contacto de respuesta. El HTML
escapa datos del usuario y no carga JavaScript ni CSS externo.

La compra incluye productos, cantidades, precios, envío separado, descuentos,
impuestos, total pagado, dirección, estado, enlace del pedido y guía TCC cuando
existe. El PDF nuevo se llama **comprobante de compra**, sin atribuirle validez
de factura electrónica. La visita utiliza el PDF final existente y muestra
servicio, técnico, resumen y valor final.

Los documentos usan UUID y firma Django con vencimiento de siete días. El token
de visita incluye la versión revocable existente del PDF. Cambiar el UUID,
alterar la firma o usar un enlace vencido devuelve 403. Un pago que deja de estar
aprobado no permite descargar ni renovar el comprobante. Los PDFs de visita
se verifican contra su hash y tamaño antes de ofrecerlos.

Rutas públicas, con el prefijo Nginx `/api`:

- `GET /api/mail/documents/<uuid>/?token=...` (opcional `download=1`).
- `POST /api/mail/documents/<uuid>/renew/`: dueño del pedido o administrador;
  para visitas y compras invitadas, administrador.
- `GET /api/mail/deliveries/`: auditoría exclusiva de administrador.
- `POST /api/mail/deliveries/<uuid>/retry/`: reintento administrativo de fallidos.

Las respuestas del PDF incluyen `private, no-store`, `noindex` y
`Referrer-Policy: no-referrer`. No se regenera un PDF desde una descarga GET.
Nginx de aplicación y de multimedia, tanto dev como prod, bloquean
`/media/private_receipts/`. Las carpetas privadas de visitas ya estaban
bloqueadas y se conservaron. Los logs de acceso del proxy omiten los parámetros
de consulta; las vistas y tareas no imprimen firmas, credenciales ni contenidos.

## Archivos de esta tarea

- Nueva app `BACKEND/transactional_mail/`: modelos, servicio, tareas, plantillas,
  documentos, endpoints, administración, comandos de diagnóstico/QA y pruebas.
- `BACKEND/core/settings.py`, `BACKEND/core/urls.py`: registro de app, Beat,
  configuración y rutas protegidas.
- `BACKEND/ecommerce/email_service.py`, `views.py`, `tests.py`: envío asíncrono
  después de aprobación de pago y pruebas adaptadas.
- `BACKEND/AppVisits/views.py`, `tests.py`: evento de visita finalizada y pruebas
  del informe persistido.
- `docker-compose.dev.yml`, `.env.example`, `.env.prod.example`: configuración
  sin credenciales reales.
- `nginx/media.conf`, `nginx/nginx.dev.conf`, `nginxprod/media.conf`,
  `nginxprod/nginx.conf`: bloqueo de los comprobantes privados.

Migraciones aplicadas solo en desarrollo:

1. `transactional_mail.0001_initial`: nueva tabla de auditoría, archivos de
   comprobantes y restricción única por evento. No modifica pedidos ni visitas.
2. `transactional_mail.0002_delivery_max_attempts_alter_delivery_state`: presupuesto
   de reintentos y estado cancelado. No borra ni transforma registros históricos.

## Respaldo y datos sintéticos

Antes de migrar se crearon y verificaron:

- `.artifacts/before-mail-20261019.dump` (`pg_dump -Fc`, listado con `pg_restore`).
- `.artifacts/before-mail-media-20261019.tar.gz` (listado del archivo tar).

Son archivos privados locales ignorados por Git; no deben publicarse.

Prueba real autorizada: un pedido sintético `QA-MAIL-20261019` y la visita 1014,
ambos al destinatario autorizado en el entorno privado. No hubo cobro, despacho,
consumo de inventario ni mensajes a clientes reales. Ambos eventos quedaron
`sent`, y el usuario confirmó la recepción y apertura de los dos PDF.

Un primer generador QA creó por error una segunda visita sintética (1015) debido
a la numeración automática del modelo. Se corrigió la búsqueda estable de la
fixture y se canceló su evento de correo; se preservaron su visita y PDF. Ese
intento falló antes del envío por TLS y no produjo un tercer correo.

El worker aislado `mail-qa` se detuvo tras los dos envíos. El entorno de
desarrollo queda habilitado con lista de destinatarios autorizados; no admite
correos reales de pruebas a otras direcciones. Los ejemplos mantienen el envío
deshabilitado por defecto para requerir configuración explícita del entorno.

## Pruebas y comandos Docker

```sh
docker compose -f docker-compose.dev.yml exec -T backend python manage.py check_transactional_smtp
docker compose -f docker-compose.dev.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 -e TCC_SHIPPING_ENABLED=False backend python manage.py test transactional_mail ecommerce shipping AppVisits --noinput
docker compose -f docker-compose.dev.yml exec -T nginx nginx -t
```

Resultados: 120 pruebas de backend aprobadas; después se repitieron las 10 de
correo tras reforzar el bloqueo de URLs internas en producción, también OK.
Sin migraciones faltantes. Se verificaron acceso y descarga de PDFs a través de
Nginx, token inválido, vencido y para otro objeto, permisos, webhook repetido,
idempotencia, broker caído, credenciales ausentes, rechazo SMTP, presupuesto y
reintento, incertidumbre, falta de PDF, persistencia y posterior envío.
También pasaron la sintaxis del proxy y multimedia de producción ejecutada en
contenedores temporales, el diagnóstico TLS/autenticación posterior al reinicio,
la respuesta de ambos workers Celery y Redis, y el bloqueo directo de los
comprobantes en Nginx y en el servicio multimedia local. Se comprobó que la clave
SMTP no aparece en los archivos versionables, sin imprimir su valor.

Playwright en Docker verificó las dos plantillas a 390 y 800 px sin scroll
horizontal; se inspeccionó el logo en color y el comprobante PDF renderizado.
No se accedió a correos de otros usuarios. Evidencia sintética y logs sanitizados
en `.artifacts/mail-*.log` y vistas previas `.artifacts/*-email-*.png`.

## Brevo, DNS y producción pendientes

El usuario confirmó que `ventas@imporgasjj.com` recibe respuestas. El remitente
fue aceptado por SMTP y los mensajes llegaron al destinatario de prueba.
DNS público muestra los CNAME DKIM `brevo1` y `brevo2`, DMARC y correo Zoho.
No se cambiaron registros DNS. El SPF existente corresponde a Zoho: no crear un
segundo SPF ni sustituirlo sin revisar la configuración de envío del dominio.

La pantalla de autenticación del dominio y remitente en Brevo no se inspeccionó
desde esta sesión. Revisar allí los indicadores de verificación y los registros
exactos suministrados por Brevo; no inventar valores. Véase
[autenticación del dominio en Brevo](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC).

Para desplegar una versión revisada: respaldar PostgreSQL y multimedia, cargar
credenciales SMTP mediante el mecanismo privado de producción, configurar
`FRONTEND_PUBLIC_URL=https://www.imporgasjj.com` y
`PUBLIC_API_URL=https://www.imporgasjj.com/api`, reconstruir backend/workers,
aplicar las dos migraciones dentro del backend y cargar los dos archivos Nginx.
Probar TLS con el comando de diagnóstico antes de activar
`TRANSACTIONAL_EMAIL_ENABLED=True`. Comprobar Beat y el worker de cola `celery`.

Los enlaces locales fueron abiertos por el usuario desde su PC con Docker. El
acceso desde dispositivos externos y los enlaces reales de producción requieren
ese despliegue y su validación HTTPS; no se declaran probados en esta entrega.
Si hay rollback, desactivar primero el envío, desplegar el código revisado
anterior y conservar tabla, archivos y respaldos. No deshacer migraciones ni
restaurar datos de producción automáticamente.
