# Verificación exhaustiva de recuperación — 20 de octubre de 2026

## Alcance y resultado

Fuentes: d8c6d067 (780 archivos, fuente autoritativa previa), 749ccf56, dev/97f2bc96 y recuperación inicial/96ba8524. Rama de trabajo exclusiva codex/recover-tcc-on-current-dev; dev/main, referencias de origen y PR sin cambios. No se hizo push, PR, merge, despliegue ni acceso a producción. El checkout original conserva sus 45 eliminaciones, 2 modificaciones y 53 archivos sin seguimiento previos; no se movieron, agregaron ni restauraron.

El inventario inicial está en RECOVERY_COMPLETENESS_INVENTORY.md y comprende las 61 diferencias existentes antes de editar. La tabla adicional cubre archivos de 749ccf56 y los agregados durante esta revisión. Ninguna ruta de d8c6d067 quedó ausente. El único archivo de migración de 749ccf56 no restaurado literalmente es 0017_resume_provider_address, sustituido por la conciliación hacia adelante 0019. La justificación individual de las demás diferencias está en el inventario.

## Omisiones reales y causas

La recuperación anterior restituyó los módulos exclusivos y sus recorridos, pero no inventarió todos los fragmentos ni comparó los nombres de pruebas de cada referencia. Eso dejó:

- Carrito sin error de configuración visible, sin desglose completo y mostrando subtotal como total mientras esperaba tarifa.
- Checkout con impuestos/descuentos visuales fijados en cero en vez de usar los datos cotizados.
- Pedido, PDF y correo confundiendo tarifa real cero con ausencia de cálculo o ausencia de transporte.
- Dos pruebas específicas del editor logístico retiradas durante la separación, sin recuperar su cobertura exacta.
- Condición de reactivación/publicación y banderas de pruebas generales de 749ccf56 no conciliadas completamente.
- Documento TCC_BRANCH_LOCAL.md exclusivo de 749ccf56 no recuperado.

Se corrigieron por fragmentos. La tarifa fija 25000 y el umbral/promoción de 500000 permanecen excluidos. Una tarifa real de cero se representa como importe de transporte, sin inventar una promoción. NULL se conserva como envío fuera de la compra en modo desactivado.

## Inventario funcional

| Área | Evidencia contra snapshot | Estado final |
|---|---|---|
| Productos | Editor transaccional, borradores, descripción con formato, galería, principal y servicios iguales; formulario histórico más compatible | Dos pruebas de reparto exacto/valor manual recuperadas; publicar/reactivar valida con TCC activo, editar histórico sin logística sigue permitido |
| TCC | Cliente, catálogo, servicios, modelos, rutas, tareas, perfiles y migraciones originales presentes | Alias sandbox, cuentas explícitas privadas y protección de configuración; cotización por peso, guías idempotentes y errores simulados probados |
| Direcciones | Formularios, catálogo, identificadores, predeterminada y CRUD conservados | Edición/creación dentro de compra, sin duplicados y con continuidad probadas |
| Checkout/Wompi | Cotización/recotización restauradas sobre seguridad posterior | Total de servidor, dirección FK más copia, precios no manipulables, idempotencia y webhook duplicado probados |
| CRM | Archivos del módulo iguales salvo mejoras posteriores de autorización WebSocket | Filtros, contactos y separación de canales conservados; suite actual aprobada |
| Adjuntos y formato | Adaptadores, medios protegidos, normalización y vistas de archivo del snapshot presentes | Imágenes/audio/video/PDF, errores, duplicados, saltos y formatos incluidos en regresión |
| Plantillas | Editor, barra de formato y vista previa por canal iguales al snapshot | CRUD persistido, variables y degradación por canal en navegador y backend |
| Correos y PDFs | Módulo transaccional y enlaces protegidos presentes | Confirmación de compra/visita, reintentos, deduplicación y diferencia cero/NULL aprobados |
| Visitas | Sin diferencias de código frente al snapshot | Suite AppVisits, PDF y sincronización incluida |
| WhatsApp/Meta | Gateway y adaptadores de Meta iguales al snapshot | 38 pruebas del gateway; contratos de Meta, nombres, medios y duplicados simulados; no se enviaron mensajes reales |
| Usuarios/Trabajadores | Implementación de dev/97f2bc96 intacta | Contraseñas seguras, inactivos, permisos, último administrador y revocación probados |
| Docker/Nginx/dependencias | Sin diferencias contra snapshot en Compose, Nginx, lockfiles y requisitos | Imágenes compiladas y servicios comprobados funcionalmente; QA usa configuración ignorada independiente |

## Migraciones y pruebas

No se crearon nuevas migraciones en esta segunda revisión. Se mantiene la 0019 de recuperación y se conservan intactas las migraciones publicadas en dev (0014, 0017, 0018), usuarios, CRM y adjuntos. Shipping 0001–0003 conserva los archivos originales. makemigrations --check --dry-run, showmigrations, migrate --plan y migrate se ejecutaron dentro de Docker en QA: sin cambios de modelo ni operaciones pendientes. Los ensayos previos dev→recuperación y TCC anterior→recuperación permanecen aprobados; esta revisión no cambia su esquema.

Resultados definitivos de esta revisión:

| Suite | Descubiertas | Ejecutadas | Aprobadas | Fallidas | Omitidas |
|---|---|---|---|---|---|
| Django actual completa | 422 | 422 | 422 | 0 | 0 |
| Compra/editor/TCC con bandera global activada | 66 | 66 | 66 | 0 | 0 |
| Gateway WhatsApp | 38 | 38 | 38 | 0 | 0 |

La ronda inicial de recuperación tenía 419 pruebas; se agregaron dos de editor y una de comprobante/correo. Las cifras históricas 276/307 son antecedentes, no resultados reejecutados en esta revisión. Cinco nombres antiguos de usuarios fueron reemplazados por pruebas actuales equivalentes con permisos más estrictos; su correspondencia está documentada. No se volvió a permitir autoinactivación ni éxito masivo parcial.

Navegador Docker: recovery-completeness, tcc-checkout, shipping-location, tcc-live-flow, users-admin, chat-media, template-preview, product-editor-live y recovery-websocket aprobados. El flujo persistente usa PostgreSQL real de QA y proveedores simulados; 250000 de productos + 30000 de transporte = 280000 COP, webhook repetido sin pedido/guía duplicados. WebSocket real cruza Nginx→ASGI→Redis con JWT por subprotocolo y ping/pong, sin credenciales en URL ni mensajes a clientes.

Imágenes actuales: backend, frontend y gateway de pruebas construidas; TypeScript/Vite aprobados. Las cuatro imágenes de la separación anterior no se presentan como una compilación nueva: en esta revisión se construyeron tres.

## Servicios

Los servicios locales preexistentes se consultaron sin reiniciarlos ni modificar sus archivos. Los servicios tcc-recovery-qa ejecutan código recuperado y usan PostgreSQL/Redis propios, sin puertos públicos ni credenciales externas. La ausencia de healthcheck configurado se indica y se complementa con una prueba funcional; no se interpreta running como validación suficiente. Los datos del sondeo son una observación puntual.
| Servicio | Estado | Healthcheck | Reinicios | Logs recientes | Verificación funcional |
|---|---|---|---|---|---|
| backend | running | no configurado | 1 | 0 líneas de error en ventana del sondeo | HTTP productos 200; contenedor local anterior, sin reinstalar |
| frontend-ecommerce | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | HTTP 200 usando Host localhost |
| postgres | running | healthy | 0 | Sondeo inicial sin usuario generó error de rol; sondeo correcto pasó | pg_isready con usuario/base configurados |
| redis | running | healthy | 0 | 0 líneas de error en ventana del sondeo | PING/PONG |
| celery-worker | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | Ambos workers contestan inspect ping |
| celery-chatbot | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | Ambos workers contestan inspect ping |
| celery-beat | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | Proceso activo y 105 publicaciones observadas en sondeo previo |
| whatsapp-gateway | running | healthy | 0 | 0 líneas de error en ventana del sondeo | HTTP /health 200/ok y 38 pruebas de Baileys simuladas |
| ollama | running | healthy | 0 | 0 líneas de error en ventana del sondeo | /api/tags 200; inferencia qwen:4b respondió y done=true |
| nginx | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | nginx -t, frontend 200 y /api/products 200 |
| media | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | nginx -t; acceso protegido y archivos validados por tests |
| tcc-recovery-qa-backend-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | HTTP productos 200 con código recuperado |
| tcc-recovery-qa-worker-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | Ping y tarea debug sintética SUCCESS |
| tcc-recovery-qa-beat-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | Scheduler inició y publicó 4 tareas en Redis QA; cola aislada |
| tcc-recovery-qa-database-1 | running | healthy | 0 | Errores esperados de duplicados; incidencia de base de pruebas documentada | pg_isready y 422 pruebas/ensayos de persistencia |
| tcc-recovery-qa-redis-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | PING/PONG y grupos WebSocket reales |
| tcc-recovery-qa-frontend-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | HTTP 200 y pruebas responsive de navegador |
| tcc-recovery-qa-nginx-1 | running | no configurado | 0 | 0 líneas de error en ventana del sondeo | nginx -t y WebSocket real con proxy HTTP upgrade |

## Errores de verificación e incidencias

Una ejecución adicional de QA coincidió con la terminación de otra y compartió test_crm_upgrade; esa ronda quedó invalidada. Se repitieron las suites con settings privados de prueba y nombres exclusivos test_recovery_completeness_full / test_recovery_enabled_mode. No afectó bases de desarrollo ni producción. Los conteos finales corresponden únicamente a las rondas aisladas definitivas.

El primer sondeo de Vite usó un Host interno no permitido y obtuvo 403; con Host localhost respondió 200. Media no tiene endpoint /health (404 esperado al probar una ruta inexistente); se verificaron nginx -t y acceso real protegido mediante las pruebas de archivos. El primer pg_isready sin usuario generó un error de rol; el sondeo con usuario/base configurados pasó. No se modificó configuración de servicios preexistentes para ocultar esos resultados.

## Evidencias y comandos

Logs ignorados en .artifacts/: completeness-tests-isolated.log, completeness-enabled-isolated.log, completeness-gateway.log, completeness-browser.log, completeness-e2e.log, completeness-products.log, completeness-websocket-proxy.log, completeness-build.log, completeness-migrations.log, qa-task.log, qa-http.log, qa-worker.log y container-status.json. Los diffs completos, name-status, summary y range-diff también quedan allí. No se incluyen bases, media, secretos o dist en commits.

Comando base de la suite: docker compose -f .artifacts/compose.yml run --rm -T backend python manage.py test ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios --noinput --verbosity=2. En las rondas finales se agregaron DJANGO_SETTINGS_MODULE=recovery_test_settings, PYTHONPATH=/app:/qa, nombre de prueba exclusivo y montaje de configuración QA ignorada; sus valores son sintéticos y el módulo exige DB_HOST=database. Las pruebas de proveedor interceptan HTTP; tareas Celery usan únicamente broker QA.

## Commits locales de esta revisión

- 3499fa6f: recupera cobertura del editor y validación al publicar/reactivar.
- 4aa57f48: recupera desglose cotizado y errores/pendientes del carrito.
- 37674525: distingue tarifa real cero de NULL en correos/PDF.
- Commit posterior de pruebas/documentación: banderas de 749ccf56, WebSocket por proxy, documento histórico, inventario e informe final.

## Recomendación y límites

La conciliación del código está justificada contra las fuentes versionadas: todas las funcionalidades de d8c6d067 están presentes o tienen reemplazo explícito; los campos, rutas y pruebas no se juzgaron solo por contener TCC. Es apta para revisión local, sin alterar dev ni el PR #7.

No se certifica una cotización contra el servidor externo de TCC: sandbox se validó con contratos simulados. Siguen pendientes credenciales/cuentas/origen privados y autorización para una prueba externa controlada. Tampoco se certifica entrega real de Meta/Baileys/Brevo ni pago real de Wompi, porque no se efectuaron esas operaciones. No hay contrato suministrado para API de seguimiento, cancelación o webhooks de TCC; se conserva seguimiento web e historial local. TCC y despacho permanecen desactivados por defecto. No corresponde desplegar ni publicar hasta nueva autorización.