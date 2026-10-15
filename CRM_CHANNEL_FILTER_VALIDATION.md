# Validación de filtros y chatbot del CRM

Fecha: 14 de octubre de 2026. Rama de trabajo: `dev`. Base revisada: `5b2a6bca` de `origin/main`, ya contenida en dev al comenzar. Esta tarea prepara un PR hacia main; no incluye merge ni despliegue de producción.

## Diagnóstico y correcciones

Los identificadores de canal ya coincidían entre frontend y backend. Los problemas encontrados estaban en el contrato y la actualización de la bandeja:

- La API aceptaba canales inválidos sin error y no aplicaba filtro de cola. Se añadió validación común para lista y contadores.
- El contador de pendientes era global. Ahora devuelve `total`, `count` (pendientes) y `unread` con los mismos filtros. El campo `count` conserva compatibilidad.
- La lista hacía una consulta por conversación para el último mensaje. Ahora usa una subconsulta y contact en la misma consulta; mantiene el límite existente de 100 y orden estable por actividad/id. Los contadores abarcan todos los resultados y la interfaz avisa cuando muestra solo 100.
- Faltaban cancelación de solicitudes, persistencia por usuario y actualización inmediata tras reconectar WebSocket. Las claves de React Query incluyen usuario, canal, estado, búsqueda, prioridad, cola y sin responder; las consultas consumen AbortSignal.
- Los eventos invalidan y consultan el estado persistido, sin insertar conversaciones de otros canales ni sumar contadores en el cliente. Los cambios de lectura, cierre, asignación y transferencia publican eventos. La transferencia se publica después del commit.
- Los borradores se conservan por conversación mientras está abierta la bandeja, con su clave de idempotencia. Una respuesta tardía de envío no borra el borrador de otra conversación.
- Una caída del canal Redis podía convertir una operación persistida en un error HTTP. Ahora se registra el tipo de fallo sin incluir su contenido privado; polling y reconexión recuperan el estado.
- Una caída del broker al encolar el bot podía devolver un error después de guardar el mensaje. Ahora conserva el mensaje pendiente y el recuperador existente reintenta con límite; finalmente muestra un estado fallido recuperable manualmente.
- El endpoint ecommerce del bot no incrementaba no leídos ni emitía el evento entrante. Los mensajes posteriores a la transferencia tampoco actualizaban la fecha de cliente usada por “Sin responder”. Se corrigieron ambos caminos. El cliente envía UUID por mensaje; repetir la misma solicitud conserva un solo mensaje, contador y tarea. La creación es transaccional y protege la propiedad de la sesión.

No se modificó la lógica comercial simplificada: saludo una vez, recomendaciones desactivadas, transferencia por intención comercial y ninguna respuesta automática tras transferir. Se ampliaron sus pruebas a WhatsApp Cloud y al aislamiento paralelo entre Facebook e Instagram.

## API y persistencia

URLs públicas: `/api/crm-chat/sessions/` y `/api/crm-chat/sessions/pending-count/`. Ambos endpoints solo aceptan agentes/administradores según los permisos existentes. Consultar la lista y los contadores no modifica datos; abrir mensajes conserva el comportamiento existente de marcar lectura.

Filtros: `channel`, `status`, `search`, `priority`, `queue` (ID positivo), `unanswered`. `all` omite el filtro de selección. Un canal inválido devuelve HTTP 400; usuario sin rol devuelve 403; anónimo recibe 401/403 según autenticación.

Selecciones almacenadas por usuario en sessionStorage de la pestaña. La búsqueda queda solo en memoria y se conserva durante navegación interna. No se guardan contactos, textos de mensajes, archivos ni credenciales en las preferencias. Otra cuenta recibe sus propias preferencias.

## Resultados controlados por canal

Fixtures sintéticas en base aislada. Los envíos de canal se simularon; no se contactó a clientes reales.

| Filtro | Esperadas | Obtenidas | Canales encontrados | Resultado |
| --- | ---: | ---: | --- | --- |
| Todos | 5 | 5 | ecommerce, whatsapp, whatsapp_web, facebook, instagram | Aprobado |
| WhatsApp Web | 1 | 1 | whatsapp_web | Aprobado |
| WhatsApp Cloud | 1 | 1 | whatsapp | Aprobado |
| Instagram | 1 | 1 | instagram | Aprobado |
| Facebook Messenger | 1 | 1 | facebook | Aprobado |
| Ecommerce | 1 | 1 | ecommerce | Aprobado |
| Combinación sin resultados | 0 | 0 | ninguno | Aprobado |
| Canal inválido | HTTP 400 | HTTP 400 | ninguno | Aprobado |

Para cada canal se verificaron apertura de mensajes de la sesión correcta, respuesta manual con transporte simulado, saludo una vez, transferencia única y detención posterior del bot. Ecommerce omite el saludo ya mostrado en el widget. Pruebas existentes cubren normalización, firmas, ecos del celular, webhooks duplicados, nombres/avatares, adjuntos, ventanas de respuesta y rechazo de plantillas pagadas.

## Pruebas Docker

1. Suite final de CRM, ecommerce y cuentas: **202 pruebas aprobadas**, en PostgreSQL separado `test_crm_upgrade`, eliminado por el ejecutor de pruebas al terminar. Incluye concurrencia y orden por conversación, memoria aislada Facebook/Instagram, timeout de Ollama, envío externo fallido, caída simulada de broker/Redis y recuperación limitada.
2. Regresión ecommerce/cuentas/visitas con configuración predeterminada aislada SQLite: **57 pruebas aprobadas**, incluyendo PDF protegido, imágenes, Excel y costos. No se alteraron esos módulos.
3. Navegador Playwright en Docker: cinco filtros, todos, vacíos, combinación con búsqueda/estado/prioridad/cola, cambio rápido con respuesta tardía, apertura/envío simulado por canal, borradores, idempotencia tras cambiar filtro, respuesta tardía de envío, eventos duplicados, contadores, reconexión WebSocket, preferencias por usuario y móvil. Aprobado.
4. Regresión de interfaz de plantillas/adjuntos: inserción editable sin envío, variables, tipos de canal y responsive 1280/768/390. Aprobado.
5. TypeScript y Vite: aprobados. Persiste advertencia de bundle mayor de 500 kB.
6. `makemigrations crmChat --check --dry-run`: sin cambios. No se generaron ni aplicaron nuevas migraciones.
7. HTTP de desarrollo: Home, API, catálogo, producto, carrito, login y paneles chat/visitas devuelven 200. Esta comprobación de rutas no sustituye las pruebas autenticadas de backend.
8. Ambos workers Celery respondieron pong; no había tareas activas/reservadas antes de reiniciar únicamente backend, celery-worker, celery-chatbot y Beat de desarrollo para cargar el código. No se reinició PostgreSQL, Redis, Ollama ni gateway.

Comandos representativos:

```bash
docker compose -f docker-compose.dev.yml exec -T -e CRM_TEST_POSTGRES=1 backend python manage.py test crmChat ecommerce usuarios.test_account --settings=core.settings --noinput
docker compose -f docker-compose.dev.yml exec -T backend python manage.py test ecommerce usuarios.test_account AppVisits.tests --settings=core.settings --noinput
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npx vite build --outDir /tmp/crm-filter-dist'
docker compose -f docker-compose.qa.yml run --rm chat-ui-test sh -c 'npm install --no-audit --no-fund --prefix /tmp/crm-ui playwright@1.58.2 >/dev/null && node /tests/crm-channel-filters.cjs && node /tests/chat-upgrade.cjs'
docker compose -f docker-compose.dev.yml exec -T backend python manage.py makemigrations crmChat --check --dry-run
```

Evidencia local excluida de Git: `.artifacts/crm-filter-backend-final.log`, `crm-filter-browser-final.log`, `crm-filter-regression-sqlite.log`, `crm-filter-build-final.log` y `crm-filter-evidence/crm-channel-mobile.png`.

## Integridad y límites comprobados

- Conversaciones reales de desarrollo: **93 antes y 93 después**.
- Mensajes reales de desarrollo: **707 antes y 707 después**.
- Huellas de contenido de conversaciones, mensajes y tablas ajenas al CRM: iguales.
- Sin mensajes o adjuntos huérfanos; sin IDs externos o de cliente duplicados.
- La única huella variable fue `ChannelIntegration` por los callbacks automáticos de estado del gateway. Se observaron 29 POST de estado satisfactorios en diez minutos; los campos variables comprobados fueron configuración de conexión, último error, desconexión y actualización. No se atribuye este cambio de fondo a las fixtures de prueba.
- No se borraron conversaciones reales, tablas, columnas, archivos o volúmenes. Los registros sintéticos viven en la base temporal y los adjuntos de pruebas en media temporal.
- La regresión opcional de visitas sobre PostgreSQL produjo `InterfaceError: connection already closed` en generación PDF. Se reprodujo la misma prueba sobre una copia intacta de main `5b2a6bca`, en Docker y base separada, confirmando el fallo previo. No se cambió visitas; sus 57 pruebas combinadas pasan con la configuración predeterminada. No se afirma que toda configuración histórica de pruebas esté libre de fallos.
- Estado real local: Facebook e Instagram figuran activos en base; no se revalidaron permisos remotos ni se enviaron mensajes reales. WhatsApp Cloud y Web figuran inactivos; gateway saludable con QR pendiente. Sus contratos se probaron con fixtures y transportes simulados, sin afirmar entrega real.
- Ollama responde y las recomendaciones están desactivadas. El entorno local existente selecciona `qwen2.5:1.5b`; también tiene `qwen:4b` instalado. Esta tarea no cambia el modelo ni variables de producción.
- Producción no fue modificada. PR pendiente de revisión; no fusionar automáticamente.

## Archivos y rollback

Backend: `crmChat/session_filters.py`, `views.py`, `realtime.py`, `tasks.py`, `apps/whatsapp_web/views.py`, `test_session_filters.py`, `test_simple_chatbot.py`.

Frontend: `admin/hooks/useInboxFilters.ts`, `useCRMWebSocket.ts`, `admin/pages/ChatPage.tsx`, `admin/services/admin_chat.ts`, integración del contador CRM en `admin/components/DashboardLayout.tsx`, clientes de chat `services/chat.ts` y `services/chatbotService.ts`, y `tests/crm-channel-filters.cjs`.

Rollback: revertir el commit del PR mediante otro commit revisado y reconstruir/reiniciar solo frontend y servicios backend/Celery de desarrollo o del despliegue aprobado. No requiere migración inversa, restaurar datos ni eliminar volúmenes. Los parámetros y el campo `count` conservan compatibilidad; el UUID nuevo es opcional para clientes anteriores.

Los artefactos compilados de `frontend_U/dist` generados durante la prueba se excluyen del PR. La revisión automática rechazó retirarlos del árbol local por riesgo de descartar trabajo; se conservaron junto al archivo local previo `verify_live_meta_handshakes.py` y `.artifacts/`.
