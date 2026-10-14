# Chatbot omnicanal: implementación y validación en dev

Fecha: 2026-10-08. Base aprobada: `origin/main` **9808b47b**.
`dev` se actualizó mediante fast-forward desde **60e0b6c7**, conservando
`verify_live_meta_handshakes.py` sin seguimiento. Producción no se modificó.

## Diagnóstico y cambios

- El bloqueo anterior protegía un mensaje, pero dos mensajes de una conversación podían inferir simultáneamente y sobrescribir memoria. El historial también incluía mensajes posteriores a la consulta procesada.
- Ecommerce ejecutaba inferencia en la petición HTTP, con un flujo diferente a los canales externos. Ahora devuelve **202** y consulta el resultado mediante polling protegido.
- Webhooks, descargas y respuestas lentas competían en una sola cola de dos workers. Se separaron `celery` y `chatbot`; esta última tiene dos procesos y prefetch 1.
- El contexto de inferencia incluía hasta 40 productos, 12 mensajes extensos y estado JSON completo. Ahora hay un presupuesto menor de contexto, resumen estructurado y salida de 180 tokens. Las recomendaciones continúan resolviéndose con datos del catálogo, sin inferir precios.
- El `.env` local fijaba `qwen:4b` y prevalecía sobre los valores predeterminados de Compose. Se actualizaron exclusivamente sus parámetros locales de Ollama y los ejemplos versionables. Ningún `.env` real se publica.
- Messenger recibía `document` en lugar del tipo oficial `file`. Instagram enviaba texto al recibir un archivo. Se corrigieron los adaptadores y se rechazan tipos no habilitados antes de guardar/enviar.
- El gateway solo admite URLs del origen interno del CRM, pero el backend construía una URL pública. Ahora genera una URL firmada nueva por intento: origen interno para Baileys y público HTTPS para Meta.
- Las carpetas `crm_gateway` y `crm_templates` necesitaban protección adicional: se bloquearon en Nginx dev, Nginx de producción, ambos servidores multimedia y Django DEBUG.

## Concurrencia, orden e idempotencia

1. La entrada real se persiste como `queued` cuando corresponde al bot habilitado; nunca se procesan mensajes de agentes ni historial importado de WhatsApp.
2. Una concesión en PostgreSQL por `session_id`, con propietario UUID y vencimiento de 150 s, impide dos inferencias simultáneas de la misma conversación. No se mantiene una transacción abierta durante la inferencia.
3. Un mensaje espera a los anteriores pendientes de su conversación. Celery reprograma la espera cada dos segundos, sin ocupar un proceso durante ese intervalo. Conversaciones diferentes usan los dos procesos disponibles.
4. La relación única `reply_to_message` impide crear otra respuesta para el mismo mensaje. El historial incluye respuestas a preguntas anteriores aunque estas respuestas se hayan guardado después de una segunda pregunta rápida.
5. Estados visibles: recibido, en cola, procesando, enviado, entregado, leído y fallido. Se publican eventos WebSocket de los cambios.
6. Timeout HTTP de Ollama: 60 s; límites soft/hard del task: 110/120 s. La concesión se libera en `finally`. Beat recupera trabajos abandonados después de 180 s, con dos recuperaciones como máximo. Un fallo normal de inferencia queda disponible para reintento manual; no se envían errores técnicos al cliente externo como respuestas del bot.
7. `client_message_id` se conserva en el compositor durante reintentos; se rechaza reutilizarlo con otro contenido. Baileys conserva su idempotencia. Un envío confirmado no se repite.
8. Si Meta no confirma la entrega por timeout, respuesta sin ID o error 5xx, se bloquea el reenvío automático/manual ciego. Debe comprobarse el canal para evitar duplicados.
9. Los archivos entrantes del gateway utilizan una clave estable. Reintentar la carga reutiliza el archivo persistido. Las copias temporales se eliminan únicamente tras confirmación de persistencia del CRM.

Los logs registran IDs internos, canal, espera de cola, duración de inferencia y resultado. No registran cuerpos de conversación, tokens ni URL firmadas completas. Los access logs existentes usan `$uri`, sin parámetros.

## Modelo y rendimiento medido

CPU en Docker Desktop; tres consultas sintéticas por modelo, misma pregunta comercial en español. El promedio incluye carga inicial y no constituye un SLA de producción.

| Métrica | Anterior | Nuevo |
|---|---:|---:|
| Modelo | qwen:4b | qwen2.5:1.5b |
| Contexto por petición | 4096 | 2048 |
| Máximo de salida | 450 | 180 |
| Tiempo de muestras, segundos | 8.402 / 2.863 / 2.615 | 6.239 / 2.227 / 2.584 |
| Promedio, segundos | 4.627 | 3.683 |
| Memoria cargada informada por `/api/ps` | 5,816,073,583 bytes | 1,168,491,150 bytes |

- Dos inferencias simultáneas con el modelo nuevo: **2.632 / 2.672 s**.
- `docker stats` después de la prueba: Ollama **1.146 GiB**, backend 112.6 MiB, worker chatbot 189.7 MiB, Redis 4.035 MiB.
- Dos conversaciones ecommerce con cola real y saludo determinístico: **1.160 / 1.159 s**, incluyendo el intervalo de polling de un segundo. Una respuesta por conversación; acceso desde otro cliente rechazado con 403.
- Se conserva un solo modelo cargado, paralelismo 2 y Ollama Cloud deshabilitado. El modelo anterior superaba el presupuesto aproximado de 3–4 GB al ampliar contexto/concurrencia.
- Las pruebas existentes de contexto cubren respuestas cortas, referencias a productos, cambio de necesidad, presupuesto y preguntas progresivas. Se agregó el caso `baño` → hogar, `dos` → dos puntos y `apartamento` → inmueble, sin exigir respuestas literales.

## Plantillas internas

- Vista `/admin/chat/plantillas` y botón **Plantillas** en la conversación seleccionada.
- Nombre, categoría, canales, texto plano, variables, adjunto opcional protegido, estado, autor y fechas.
- Buscar por nombre/categoría/texto, categorías, favoritas y recientes por usuario.
- Completar variables → vista previa final validada en backend → insertar → editar → enviar. Seleccionar, previsualizar o insertar no envía nada.
- Administradores `tipo_usuario=4`: crear, editar y desactivar. Agentes CRM autorizados `1/4`: consultar, usar y marcar favoritas. Los clientes no acceden.
- Variables admitidas: nombre_cliente, nombre_agente, numero_visita, fecha_visita, costo_final, enlace_pdf, nombre_producto, enlace_producto. Los datos de visita/producto no se inventan ni se extraen de registros ajenos: el agente completa los valores faltantes.
- Se registra la creación/modificación y el uso efectivo en auditoría; el mensaje conserva `template_id`. HTML se representa como texto mediante React.
- Son borradores internos. No se crean plantillas de WhatsApp Cloud API, campañas, etiquetas para ampliar ventanas ni servicios de pago.

## Archivos y restricciones por canal

| Canal | Tipos habilitados desde el CRM |
|---|---|
| WhatsApp Web | Imágenes, audio, video, PDF y DOCX/XLSX seguros |
| Facebook Messenger | Imágenes, audio, video y documentos mediante `file` |
| Instagram | Imágenes; audio, video y documentos deshabilitados hasta verificar soporte/permisos del modo de conexión concreto |
| Ecommerce, agente autenticado | Imágenes, audio, video y documentos seguros |
| WhatsApp Cloud API | No se amplían funcionalidades de archivos o plantillas |

- Límite configurable predeterminado: 25 MB. Extensiones: JPG/JPEG, PNG, WEBP, GIF, PDF, DOCX, XLSX, MP3, OGG, WAV, M4A, MP4 y WEBM, sujeto al canal y al rechazo del proveedor.
- Pillow verifica imágenes reales; pypdf verifica PDF y rechaza contenido activo; los documentos OOXML rechazan macros, objetos incrustados, relaciones externas, fórmulas y campos activos; ffprobe verifica streams y contenedor de audio/video. DOC/XLS heredados no se aceptan en nuevas cargas; los archivos históricos se conservan.
- Nombre seguro, MIME, tamaño, SHA-256, canal y estado se conservan en metadatos. Descargas requieren permisos o token firmado temporal; los archivos no son media pública.
- El compositor muestra vista previa, carga y progreso, espera de confirmación, errores y reintento cuando es seguro.
- Messenger e Instagram no reciben un texto junto a un archivo en esta implementación. Se rechaza el intento con explicación, conservando el borrador; el agente debe revisar y enviar cada contenido por separado. También se rechazan textos junto a audio. No se crean dos envíos implícitos.
- Los envíos externos siguen requiriendo integración activa, destinatario válido, mensaje entrante real y ventana reactiva de 24 horas. No se agregan mecanismos para eludir restricciones ni generar cobros.

## Migraciones y configuración

- **0015_chatbot_leases_internal_templates**: agrega tres tablas, concesiones por conversación, plantillas y preferencias. No transforma ni elimina conversaciones históricas.
- **0016_message_processing_status**: agrega la opción `processing` al estado del mensaje. No modifica el contenido existente.
- Aplicadas únicamente en dev mediante Docker; `makemigrations --check --dry-run` no detecta cambios pendientes.
- Parámetros nuevos: `OLLAMA_NUM_PREDICT=180`, `CRM_GATEWAY_MEDIA_BASE_URL` (backend:8000 en dev; backend:8001 en prod), `THROTTLE_CRM_UPLOAD_RATE=30/min`. Compose fija un modelo cargado y modo local de Ollama.
- Redis usa `noeviction` para no expulsar silenciosamente tareas del broker compartido. Hay que vigilar su memoria; cuando se alcanza el límite rechaza escrituras explícitamente.
- Los parámetros existentes modelo/timeout/contexto cambian en los ejemplos y en dev. Los valores reales de producción deberán revisarse manualmente al aprobar el despliegue.

## Verificación Docker

```sh
docker compose -f docker-compose.dev.yml exec -T -e CRM_TEST_POSTGRES=1 backend python manage.py test crmChat --noinput
docker compose -f docker-compose.dev.yml --profile test run --rm --build whatsapp-gateway-test
docker compose -f docker-compose.qa.yml run --rm chat-ui-test
docker compose -f docker-compose.qa.yml run --rm proxy-config-test
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce npm run build -- --outDir /tmp/chatbot-build --emptyOutDir
docker compose -f docker-compose.dev.yml exec -T backend python manage.py check
docker compose -f docker-compose.dev.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec -T backend sh -c 'python manage.py shell < scripts/benchmark_chatbot.py'
docker compose -f docker-compose.dev.yml exec -T backend sh -c 'python manage.py shell < scripts/verify_chat_queue.py'
docker compose -f docker-compose.dev.yml exec -T celery-worker celery -A core inspect active_queues --timeout=3
docker compose -f docker-compose.prod.yml config --no-env-resolution --no-interpolate --quiet
```

Resultados: **139 tests CRM PostgreSQL aprobados**, **38 tests gateway aprobados**, navegador Chromium Docker aprobado en 1280/768/390 px, build TypeScript/Vite aprobado, ambas colas registradas y activas, Nginx dev y configuración prod válidos. El browser usa fixtures sintéticos; persistencia, permisos y errores de transporte se prueban en Django. La prueba ecommerce de cola real crea dos conversaciones sintéticas locales, sin mensajes externos.

La suite general no está verde: `origin/main` presenta **49 fallos y 33 errores** (81 en usuarios y un import de `test_ecommerce_api` que ejecuta `sys.exit`). Se ejecutó desde un archivo Git independiente dentro del contenedor y se compararon los nombres de fallos con dev: coinciden. Las pruebas de concurrencia se ejecutan en PostgreSQL; se omiten con SQLite, que no implementa los bloqueos necesarios.

## Archivos afectados

- Backend: `core/settings.py`, `core/urls.py`, `crmChat/{models,tasks,bot_concurrency,ollama_service,attachment_validation,views,urls,quick_replies}.py`, adaptadores Meta/Instagram/WhatsApp Web, migraciones 0015/0016 y tests CRM.
- Imágenes: `BACKEND/Dockerfile` y `Dockerfile.prod` incorporan ffprobe mediante ffmpeg.
- Gateway: `src/whatsapp/{messages,media}.ts`.
- Frontend: `App.tsx`, `Chatbot.tsx`, servicio chatbot, servicios/admin chat, ChatPage, TemplateDialog, TemplatesPage, DashboardLayout y prueba de navegador.
- Infraestructura: Compose dev/prod/QA, ejemplos de entorno, configuraciones Nginx dev/media y `nginxprod/{nginx,media}.conf`.
- Scripts reproducibles de benchmark y cola ecommerce; este informe.

## Despliegue futuro y rollback — no ejecutados

1. Revisar el PR, los fallos generales preexistentes y permisos reales de Meta. Probar envío real únicamente con conversaciones/números de prueba autorizados; no se envió a clientes durante esta tarea.
2. Antes de desplegar, registrar commit/imágenes anteriores, respaldar PostgreSQL y media y verificar los respaldos. Revisar valores reales de `.env.prod` mediante el mecanismo seguro existente, sin publicarlos.
3. Iniciar primero Compose de datos prod existente. Reconstruir backend, ambos workers, beat, gateway y frontend. Aplicar migraciones desde el backend dentro de Compose. Incluir explícitamente **celery-chatbot**; actualizar modelo mediante `ollama-init` antes de habilitar tráfico.
4. Verificar colas, memoria Redis/Ollama, callbacks, medios protegidos, WebSockets y conversación ecommerce. Verificar permisos y ventana de Meta antes del envío autorizado.
5. Rollback: detener consumidores nuevos, conservar logs y datos, restaurar imágenes/código/configuración de la versión anterior, y arrancar su worker de cola `celery`. Conservar las tablas aditivas; no deshacer 0015 ni eliminar plantillas. No usar reset de base, flush, eliminación de volúmenes ni force-push. Restaurar respaldos solo ante una necesidad justificada y autorizada.

Pendientes: prueba real de entrega/visualización en cuentas Meta y WhatsApp de prueba autorizadas; soporte adicional de Instagram condicionado a documentación/permisos concretos; corrección de la suite general heredada. El PR debe permanecer sin fusionar y producción sin actualizar.

## Fuentes primarias consultadas

- [Ollama FAQ: contexto, paralelismo, memoria y desactivación de Cloud](https://docs.ollama.com/faq).
- [Meta, colección oficial Messenger Platform](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api).
- [Meta, ejemplo oficial de imagen/GIF de Instagram](https://www.postman.com/meta/instagram/request/psiv6gj/media-message-gif).
