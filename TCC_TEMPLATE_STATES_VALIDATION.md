# Estados de entrega y página de plantillas — dev

Validación del 21 de octubre de 2026. Commit inicial: `a9bebcecdcd4d9842a5160a72dabbc57010d843e`. Commits de implementación: `d8ee7c88` y `a2fe4a50`. El commit documental posterior cierra este informe; su hash se obtiene con `git log -1`.

**Causas reproducidas.** El proceso del backend de desarrollo había arrancado antes de restaurar las rutas de shipping: Nginx entregaba las solicitudes correctamente, pero Django respondía 404 tanto en `/api/shipping/config` como en `/api/shipping/cities`. El frontend mostraba dos fallos sin relación con la logística del producto. Además, el transformador de productos descartaba `shipping_ready`, por lo que el detalle no podía presentar la falta de logística antes de intentar cotizar. En plantillas, `TemplatesPage` inicializaba `open=true` y renderizaba el administrador completo dentro de `TemplateDialog`; no existía un listado normal en la página.

**Cambios TCC.** Product Detail conserva `shipping_ready` y los campos faltantes; `ShippingCalculator` separa el producto incompleto, configuración cargando/error/desactivada, catálogo cargando/vacío/error, destino pendiente y cotización cargando/error/exitosa. La información del producto incompleto tiene prioridad y no dispara cotizaciones ni ofrece un reintento inexistente. Cada botón repite solo su solicitud. `useDeliveryCatalog` comparte una consulta para el catálogo; no se vuelve a solicitar por separado durante la restauración de la ubicación. No se muestran dos errores contradictorios ni se restaura un total vencido después de un fallo. Los mensajes distinguen sesión/permisos, servicio ausente, indisponibilidad temporal, red y timeout sin mostrar trazas. Se mantiene la causa específica de falta de cobertura.

**Contratos.** `GET /api/shipping/config` devuelve 200 con `status=available|disabled` y `can_quote`, además de conservar `enabled` para compatibilidad. Configuración y catálogo son lecturas públicas que ignoran un JWT vencido enviado accidentalmente. `GET /api/shipping/cities` acepta un catálogo vacío válido (200 con `[]`). El detalle de productos añade `shipping_missing_fields`. `POST /api/shipping/estimate` devuelve 422 controlado para logística incompleta, con `status=incomplete`, `can_quote=false`, código y campos faltantes; un producto inexistente devuelve 404. Las solicitudes inválidas siguen siendo 400 y los errores temporales del proveedor 503. No se cambiaron los contratos de cobro ni se añadieron llamadas productivas.

**Administrador de productos.** Se conserva el filtro completo/incompleto y la actualización del listado después de guardar. El aviso editable bajo el nombre ahora dice «Configuración TCC incompleta» y muestra los campos faltantes. Los casos completos, incompletos, valores insuficientes y producto que no requiere envío tienen pruebas de backend; la edición logística y persistencia están incluidas en el recorrido de navegador con base real de QA.

**Plantillas.** `/chat/plantillas` mantiene esa URL y usa el layout protegido del administrador. `/admin/chat/plantillas` conserva compatibilidad. `TemplatesPage` renderiza la presentación de página del componente compartido: título, descripción, buscador, filtros, tarjetas, estados, canales, categoría, autor, actualización, acciones y paginación local de diez elementos. Los errores de carga tienen reintento y no se confunden con un listado vacío. El editor se abre únicamente por crear, editar o duplicar; eliminar utiliza un diálogo pequeño. Se conservan formato, adjuntos, variables y vistas previas por canal. El selector de plantillas dentro del chat conserva su presentación de diálogo y comparte la misma lógica.

El editor enfoca el nombre al terminar la animación de apertura, conserva datos ante errores, bloquea solicitudes duplicadas, pide confirmación de descarte dentro del mismo editor y limpia el estado temporal al cerrar. MUI restaura el foco y libera el scroll; se verificó la ausencia de overlays visibles residuales. Los filtros y la paginación se reinician o ajustan cuando corresponde. No se cambió la identidad global ni se crearon editores duplicados.

**Archivos afectados.** Backend: `ecommerce/serializers.py`, `shipping/views.py`, `shipping/test_admin_logistics.py`, `shipping/test_estimates.py`. Frontend: `App.tsx`, `TemplatesPage`, `TemplateDialog`, `ProductsPage` administrativo, `ProductDetailPage`, `ShippingCalculator`, `TCCAddressFields`, hooks `useShippingConfig`/`useDeliveryCatalog`, servicios `api`/`products`/`shipping` y tipo Product. Pruebas nuevas: `shipping-states.cjs`, `templates-page.cjs`; se adaptaron las regresiones de ubicación, tarjetas, formato, editor y recorrido integrado a los mensajes y a la página normal.

**Entorno local.** Antes de reiniciar el backend de desarrollo se inspeccionó el plan: solo estaba pendiente `ecommerce.0019_restore_provider_address`, la migración aditiva de la tarea anterior. Se creó un respaldo privado en `.artifacts/tcc-template-states/dev-backup.dump` (427.977 bytes), se inspeccionó con `pg_restore --list` (621 líneas) y se conservó su índice junto al archivo. Se reinició únicamente el backend local, que aplicó esa migración y cargó las rutas actuales. No se crearon migraciones nuevas en esta tarea. Después: `makemigrations --check --dry-run` sin cambios y `migrate --plan` sin operaciones pendientes. Configuración, catálogo y listado de productos responden 200 a través de Nginx en localhost. No se modificó `.env` ni producción.

**Pruebas Docker.**

| Prueba | Resultado |
|---|---|
| Backend: ecommerce, shipping, CRM, correos, visitas, gestión y usuarios | 431 descubiertas/ejecutadas/aprobadas; 0 fallidas, 0 omitidas; 68,207 s |
| Gateway WhatsApp aislado, sin sesiones reales | 38 aprobadas, 7 archivos, 0 fallidas/omitidas |
| TypeScript y Vite | Aprobados; salida temporal `/tmp`, dist original intacto |
| `shipping-states.cjs` | Nueve escenarios aprobados: incompleto, desactivado, fallo de configuración, fallo/vacío de catálogo, ubicación pendiente, fallo del proveedor, red/timeout y éxito; reintentos independientes y sin bucles |
| `templates-page.cjs` | Página normal, dos rutas, recarga/historial, menú móvil, creación, edición, guardado, errores conservando datos, confirmación de descarte, duplicado, activación/eliminación, filtros, búsqueda, foco y overlays aprobados |
| `shipping-location.cjs` | Selectores dependientes, persistencia, cambio de destino, error, cobertura y reintento aprobados |
| `product-shipping-cards.cjs` | Ubicación compartida, caché, invalidación, carga diferida y recuperación de errores aprobados |
| `delivery-address-flow.cjs` | Dirección nueva/seleccionada, validación, error/reintento, cancelación y persistencia de compra aprobados |
| `template-editor-validation.cjs`, `template-preview.cjs` | Variables, límites, errores por campo, formato por canal y adjunto protegido aprobados |
| `recovery-websocket.cjs` | Nginx/ASGI/Redis, JWT y ping/pong aprobados |
| `tcc-live-flow.cjs`, última ejecución `verified-live-flow.log` | Django/PostgreSQL real de QA: logística guardada, productos, dirección, cotización, compra y CRUD de plantillas con persistencia aprobados; TCC y pago simulados |

El recorrido integrado verifica subtotal 250.000 COP + transporte simulado 30.000 COP = 280.000 COP, confirmación firmada repetida y una sola orden/guía/despacho simulado. No se hicieron pagos, guías ni mensajes reales. La regresión incluye permisos/autenticación, Usuarios y Trabajadores, CRM/adjuntos, visitas, correos, PDFs e integraciones simuladas. Las pruebas visuales cubren 1280, 768 y 390 px. Se inspeccionó la captura móvil de la página normal. La medición inicial de overflow capturó la transición de padding del layout; al estabilizarse no había desbordamiento. La comprobación final espera esa estabilización y sigue verificando el ancho.

**Servicios locales comprobados.**

| Servicio | Estado/healthcheck | Reinicios automáticos | Validación funcional | Memoria aproximada |
|---|---|---:|---|---:|
| Backend | running; no declara healthcheck | 0 | Configuración, catálogo y productos 200; plan de migraciones limpio | 108 MiB |
| Frontend | running; no declara healthcheck | 0 | Compilación y navegador desktop/móvil | 289 MiB |
| PostgreSQL | healthy | 0 | pg_isready, respaldo inspeccionable y persistencia de QA | 72 MiB |
| Redis | healthy | 0 | PONG y transporte WebSocket de QA | 12 MiB |
| Celery worker | running; sin healthcheck | 0 | inspect ping/pong | 224 MiB |
| Celery chatbot | running; sin healthcheck | 0 | Segundo nodo responde inspect ping/pong | 210 MiB |
| Celery Beat | running; sin healthcheck | 0 | Proceso/scheduler; no se dispararon tareas comerciales reales | 142 MiB |
| WhatsApp/Baileys | healthy | 0 | Healthcheck y suite aislada de 38 pruebas | 149 MiB |
| Ollama | healthy | 0 | Lista de modelos disponible, incluye qwen:4b; sin mensajes reales | 112 MiB |
| Nginx | running; sin healthcheck | 0 | Proxy HTTP 200 y upgrade WebSocket QA | 3 MiB |

El backend sí tuvo el reinicio manual descrito; el contador Docker anterior solo representa reinicios automáticos. CPU muestreada aproximadamente 0–0,3% por servicio, salvo Vite durante pruebas (~28%).

**Logs.** Antes de la corrección: 404 en `/shipping/config` y `/shipping/cities`. Tras reiniciar el proceso: 200, sin patrones recientes ERROR/CRITICAL/Traceback/conexión rechazada/CORS en backend, frontend y Nginx. Los fallos PDF, SMTP, timeout de Ollama y violaciones de unicidad de la suite son pruebas negativas esperadas; no son fallos de producción. Los fallos simulados 400/404/422/503 se comprueban por contrato. No se imprimieron credenciales ni datos de clientes.

**Límites y conservación.** No se afirma haber enviado mensajes reales por Meta/WhatsApp ni haber probado un pago o despacho real. Las limitaciones externas de TCC registradas en la tarea anterior no cambian con esta corrección de interfaz. Se conservaron los cambios ajenos de dist y `verify_live_meta_handshakes.py`; su estado Git coincide con el inicial. Los registros, capturas y respaldo están ignorados en `.artifacts/tcc-template-states`, fuera de los commits. Sin push, PR, merge, cambios en main ni despliegue. Rama final: dev.
