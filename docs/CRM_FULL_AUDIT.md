# Auditoría del CRM — desarrollo, 13 de noviembre de 2026

## Alcance y aislamiento

Rama `codex/crm-full-audit`, creada desde `origin/dev` y `dev` en
`fc76b3838d1da6f6e1c69f71bac66b363d9d476d`, después de fetch sin poda.
El worktree está separado del trabajo de World Office. No se copiaron cambios
de inventario, dist, package-lock, documentos locales ni archivos .env.
No hubo push, PR, merge, despliegue ni cambios de ramas ajenas.

La auditoría usa `docker-compose.crm-audit.yml`: PostgreSQL y Redis nuevos,
sin montar sus volúmenes compartidos, y una red Docker `internal: true`.
No se suministran credenciales reales de Meta, WhatsApp, SMTP ni World Office.
El backend monta únicamente el código de esta rama. Se reutilizó la imagen
local `frontend-backend:latest`; para reproducirla puede construirse desde
BACKEND con las dependencias actuales. No se arrancó el gateway real en esta
red ni se conectó con las redes de otros proyectos.

Todos los datos creados por los smoke y benchmarks son sintéticos y existen
exclusivamente en `crm_audit`. Los adjuntos del smoke se almacenan en
`/tmp/crm-audit-media` del contenedor, no en media compartida. Las pruebas Django
usan su propia base temporal `test_crm_upgrade`. No se modificaron productos,
pedidos, conversaciones ni archivos de desarrollo compartidos o de producción.

## Estado inicial y correcciones

| Módulo | Hallazgo inicial | Corrección / evidencia | Clasificación |
|---|---|---|---|
| Transporte externo | No existía un interruptor común para pruebas | Frontera compartida para Graph, OAuth, permisos, gateway y descarga Meta; sockets externos prohibidos por el runner | Corregido |
| Envío manual | Esperaba al proveedor dentro de la petición HTTP | Encolado después del commit, tarea Celery, evento de actualización | Corregido |
| Broker y worker | El nuevo recorrido asíncrono necesitaba recuperación explícita | Fallo de cola conserva mensaje; reintento manual; recuperación acotada por Beat; confirmación tardía y protección de entrega incierta | Corregido |
| Historial | Respuesta sin límite | Ventana de hasta 100 mensajes y cursor temporal/id para anteriores | Corregido |
| Bandeja | Corte a 100 conversaciones, sin navegación | Páginas de 100 con offset y botones anterior/siguiente | Corregido |
| Contrato Graph | JSON inválido podía propagar una excepción técnica | Error controlado, sin cuerpo del proveedor, entrega potencialmente incierta | Corregido |
| Simulador | No existía resultado local inequívoco | ID `crm-simulated:...`, metadata, etiqueta Simulado; no modifica conexión del proveedor | Corregido |
| Plantillas | Vista y permisos existentes | CRUD, duplicado, variables, formatos, previsualización, errores y foco aprobados | Correcto en pruebas locales |
| Adjuntos | Validadores y acceso protegido existentes | Formatos, tamaño, MIME, SSRF, acceso, reintentos y vista previa aprobados | Correcto en pruebas locales |
| Tiempo real | Autenticación, revocación y reconexión existentes | Contratos ASGI, Redis real en smoke, pruebas de reconexión y fallback de polling | Correcto en pruebas locales |
| Bot | Leases por conversación, contexto y recuperación existentes | Concurrencia, aislamiento, orden, intervención humana y fallos del proveedor simulados | Funcional con limitaciones |
| Responsive | Contenedores con altura controlada existentes | Siete anchos, paginación e historial largo sin overflow horizontal | Correcto en escenarios comprobados |

El fixture de navegador de multimedia se corrigió para no escribir localStorage
en documentos sin el origen de la aplicación. El problema estaba en el script
de prueba inyectado en esos documentos, no en el almacenamiento de la aplicación.

## Configuración de seguridad

```env
CRM_EXTERNAL_SEND_ENABLED=false
CRM_TEST_MODE=true
CRM_ASYNC_OUTBOUND_ENABLED=true
```

`CRM_TEST_MODE` prevalece sobre el permiso de envío. La simulación se realiza
después de las validaciones locales de mensaje, conversación, integración y
ventana reactiva. Las llamadas directas a proveedores se rechazan incluso si
alguien configura simultáneamente `CRM_EXTERNAL_SEND_ENABLED=true`.

El Compose de desarrollo propaga las tres variables a backend, worker general,
worker del bot y Beat. Por defecto bloquea IO externo y no finge una entrega:
con `CRM_TEST_MODE=false` el mensaje falla de forma controlada. Para simular hay
que habilitar el modo explícitamente. El valor por defecto del setting general
conserva el comportamiento de los despliegues existentes; esta tarea no cambia
ni ejecuta la configuración productiva.

El runner `crmChat.audit_runner.AuditRunner` permite contratos con transportes
mockeados y bloquea `socket.connect` y `connect_ex` a cualquier dirección que no
sea loopback o la IP de PostgreSQL/Redis del Compose aislado. La protección cubre
threads. Las pruebas específicas comprueban que abrir un socket externo falla.
El runner no debe usarse contra una base compartida; espera los hosts aislados
`database` y `redis`.

## Flujo de salida

API -> validación -> transacción e idempotencia por client_message_id -> queued
-> on_commit -> broker -> `send_outbound_message` -> adaptador/simulador
-> persistencia del resultado -> evento WebSocket -> interfaz.

No se usa un envío síncrono como fallback si el broker cae. El mensaje permanece
almacenado y se marca fallido con un motivo seguro. El asesor puede reintentar
el mismo registro. No se duplica su operación lógica.

La tarea admite dos reintentos de transporte con espera progresiva cuando no
hay evidencia de entrega incierta. Los casos que podrían haber sido aceptados
por Meta no se repiten automáticamente. La recuperación de Beat existente se
ejecuta cada 60 segundos: revisa en lotes de 100 los queued con más de 180 segundos,
respeta la fecha de encolado reciente y limita a dos recuperaciones. Si se agotan,
conserva el mensaje fallido para revisión. La recuperación existente de processing
sin confirmación mantiene la protección contra duplicados.

## Paginación y memoria

`GET /crm-chat/sessions/?offset=100` devuelve la segunda página de hasta 100.
Offsets inválidos se rechazan. Los clientes que esperan un array lo conservan.

`GET /crm-chat/sessions/{id}/messages/?limit=100` devuelve la ventana más reciente
ordenada cronológicamente, `has_more` y `before`. El cursor de anteriores usa la
fecha efectiva del mensaje y el ID como desempate, validando que pertenezca a la
conversación autorizada. No se exponen mensajes de otra conversación mediante
un cursor ajeno. El consumidor anterior con `after` conserva ese parámetro.

La interfaz solicita anteriores explícitamente, elimina duplicados por ID,
conserva el scroll al anteponerlos y mantiene los mensajes ya cargados durante
el polling. La carga inicial deja de materializar todo el historial. Cargar
muchas páginas deliberadamente todavía aumenta la memoria del navegador; no se
implementó virtualización completa de todas las burbujas.

## Pruebas y resultados

Todas se ejecutaron en Docker. Línea base: 322 pruebas CRM/usuarios aprobadas.
Resultado final de `crmChat usuarios ecommerce shipping`: **454 ejecutadas,
454 aprobadas, cero fallidas y cero omitidas**. Se añadieron 14 métodos de
regresión, algunos con subcasos por canal o por configuración.

```sh
docker compose -f docker-compose.crm-audit.yml up -d
docker compose -f docker-compose.crm-audit.yml exec -T backend python manage.py check
docker compose -f docker-compose.crm-audit.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.crm-audit.yml exec -T backend python manage.py migrate --plan
docker compose -f docker-compose.crm-audit.yml exec -T backend python manage.py test crmChat usuarios ecommerce shipping --noinput --testrunner=crmChat.audit_runner.AuditRunner
```

No hay app llamada `crm`: el nombre real es `crmChat`. No se crearon migraciones.
Se aplicaron las migraciones ya existentes únicamente a la nueva base aislada.
El check no encontró problemas, makemigrations no encontró diferencias y el plan
posterior no tiene operaciones pendientes.

TypeScript, ESLint y build aprobaron en Node Docker. Las dependencias compartidas
se montaron de solo lectura; Vite se ejecutó con `--configLoader runner` para
evitar escribir su caché en ellas. El build fue a `/tmp/crm-build`, no a dist.

Siete suites Chromium Docker aprobadas:

- `crm-channel-filters.cjs`: cinco canales, filtros, borradores, cancelación,
  idempotencia, reconexión, aislamiento entre perfiles y móvil.
- `chat-upgrade.cjs`: selección de plantilla sin envío, variables y previsualización.
- `chat-media.cjs`: adjunto, fallo que conserva borrador, reintento estable y recarga.
- `templates-page.cjs`: página normal, sin modal automático, CRUD, foco, historial,
  confirmación de cambios y overlays.
- `template-preview.cjs`: formatos por canal, HTML seguro y adjuntos protegidos.
- `template-editor-validation.cjs`: validaciones de campos, longitud y doble clic.
- `crm-audit.cjs`: 201 conversaciones, 200 mensajes, cursores y etiqueta Simulado;
  anchos 1920, 1440, 1024, 820, 768, 390 y 320 sin overflow horizontal ni errores JS.

Las suites de interfaz usan fixtures HTTP/WebSocket. Las capturas sintéticas se
guardaron como artefactos locales excluidos de Git; se inspeccionó la vista móvil.
No son evidencia de funcionamiento del proveedor externo.

## Smoke con componentes reales aislados

`crmChat/audit_smoke.py` exige DEBUG, modo de pruebas, bloqueo de IO y la base
`crm_audit` en el host `database`. No acepta la base compartida.

Se ejecutó con Redis y worker Celery reales y el ASGI de la aplicación mediante
WebsocketCommunicator. Las solicitudes pasan por las vistas DRF mediante APIClient:
no es una prueba de proxy HTTP de producción ni del navegador contra datos reales.

Resultado final repetido después de recargar exclusivamente el worker de auditoría:

```json
{"worker":"simulated_sent","websocket":["message.created","message.updated","session.updated"],"duplicates":0,"messages":4,"template":true,"protected_attachment":true}
```

El flujo cubre recepción HMAC sintética, repetición del webhook, toma de conversación,
plantilla local, envío encolado, adjunto PNG sintético, acceso autenticado al archivo,
procesamiento del worker, notificación por Redis/ASGI y relectura persistida.
El rol administrador real del proyecto es 4; el rol 1 puede atender conversaciones
pero no administrar plantillas. El smoke se ajustó a esa política existente.

No se conectó con Baileys, Meta ni personas. No hubo mensajes, correos ni plantillas
reales. Los IDs de simulación no se presentan como IDs confirmados por proveedores.

## Medición antes/después

Mismo historial sintético de 2.000 mensajes, mismo contenedor, código original de
la vista tomado de fc76b383 frente al actual, con tracemalloc habilitado:

| Medida | Antes | Después |
|---|---:|---:|
| Mensajes materializados inicialmente | 2.000 | 100 |
| Tiempo de la vista | 0,5906 s | 0,0279 s |
| Pico de memoria Python | 19.921.643 bytes | 1.048.303 bytes |
| JSON serializado | 3.278.963 bytes | 166.086 bytes |
| Consultas SQL | 3 | 3 |

Es una medición local única, no un SLA. Los mensajes anteriores siguen accesibles
por páginas. No se observó crecimiento N+1 al cambiar el tamaño de página.
El benchmark concurrente del bot con ocho conversaciones y proveedor simulado
dio promedio 0,2665 s y máximo 0,2780 s, sin pendientes ni duplicados. Estos tiempos
NO miden inferencia real de Ollama ni latencia de canales externos.

## Servicios y logs

| Servicio | Estado observado | Validación funcional / límite |
|---|---|---|
| PostgreSQL aislado | healthy, sin reinicios | Migraciones, tests de locks y pg_isready |
| Redis aislado | healthy, sin reinicios | PONG, broker y eventos del smoke |
| Backend aislado | running, sin healthcheck | Check, suites, smoke API/ASGI y raíz HTTP 200 tras arrancar Daphne |
| Worker aislado | running | Ping/pong y dos salidas simuladas; reiniciado solo para recargar esta rama |
| Frontend aislado | running, sin healthcheck | HTTP 200 con Host permitido crm.localhost y siete suites de navegador |
| Backend y frontend compartidos | running, sin healthcheck | No se modificaron ni recrearon; las pruebas de esta rama usan otros contenedores |
| Workers/Beat compartidos | running, cero reinicios observados | Sin modificaciones; recuperación programada probada directamente, no esperando una hora |
| WhatsApp gateway compartido | healthy | GET /health HTTP 200; no login, QR ni envío |
| Ollama compartido | healthy | Catálogo local disponible; inferencia real no medida en esta auditoría |
| Nginx compartido | running | nginx -t correcto; sin cambios |
| PostgreSQL/Redis compartidos | healthy | pg_isready / PONG, sin cambios |

Muestra de recursos en reposo: backend aislado ~102 MiB, worker ~206 MiB,
PostgreSQL ~80 MiB, Redis ~4,6 MiB, frontend ~110 MiB. CPU cercana a cero salvo
Redis ~2,1 % en esa muestra. No son valores máximos bajo carga.

Ventana final de logs aislados: cero coincidencias de Traceback, CRITICAL,
connection refused, CERTIFICATE_VERIFY_FAILED o authentication failed. Las
advertencias y trazas del log de tests por timeout de Ollama, fallos SMTP/TCC y
broker caído son pruebas negativas simuladas, no incidentes del entorno real.
El primer arranque de build falló por intentar escribir caché sobre dependencias
read-only; se corrigió el comando de pruebas sin cambiar permisos del volumen.
La sonda HTTP inicial ocurrió antes de que Daphne terminase de arrancar y se
repitió después con HTTP 200. Vite rechazó correctamente Host=nginx con 403;
Host=crm.localhost devolvió 200. No se desactivó su validación de hosts.

## Límites por canal y pendientes externos

- WhatsApp Web: texto y archivos según validadores locales; entrega, lectura,
  reconexión de Baileys y envío desde otro dispositivo requieren validación real
  posterior. No se abrió sesión ni se alteró su almacenamiento.
- WhatsApp Cloud: se conservó la política existente de cero costos; plantillas
  de pago y nuevos adjuntos Cloud continúan deshabilitados. No se ampliaron permisos.
- Facebook: adaptación de texto y archivos, ventana reactiva, duplicados y errores
  comprobados con contratos simulados. Autorización y entrega real pendientes.
- Instagram: solo texto e imágenes habilitados por el contrato actual; no se
  simuló que audios/videos/documentos estén soportados por el proveedor.
- E-commerce: persistencia y acceso propios, multimedia y WebSockets comprobados
  localmente. La identidad y los datos del cliente permanecen separados del CRM.
- Ollama: contexto aislado, recuperación, timeout, intervención humana y concurrencia
  comprobados con mocks. No se certifica calidad factual universal ni rendimiento
  de inferencia del modelo real. La atención humana no depende de que el modelo responda.
- La prueba real del navegador a través del proxy, con un proveedor externo y
  notificaciones de entrega reales, NO se realizó y no queda certificada.

## Revisión, activación posterior y rollback

No desplegar esta rama automáticamente. Revisar el diff, los cambios de contrato
de historial paginado y el worker antes de autorizar PR o push.

En una futura prueba real autorizada: usar una cuenta/número controlado, un único
canal, token con permisos mínimos y allowlist en el adaptador o perímetro de pruebas;
verificar ventana reactiva y aceptación/entrega por separado; no enviar masivamente.
Requiere autorización nueva. No basta con activar las variables para afirmar que
Meta o Baileys funcionan realmente.

Para habilitar el envío asíncrono en otro entorno deben desplegarse el código de
backend y workers juntos y comprobar que el worker consume `celery`. Beat conserva
el scheduler existente de recuperación. No hay migraciones nuevas.

Rollback no destructivo: desactivar IO externo, conservar mensajes y colas, volver
a la imagen/commit anterior aprobado sin tocar volúmenes. Si se necesita volver al
recorrido síncrono durante una investigación, `CRM_ASYNC_OUTBOUND_ENABLED=false`
lo permite sin migrar datos; revisar primero mensajes queued/processing y entregas
inciertas. Nunca reenviar indiscriminadamente. No restaurar ni borrar la base.
