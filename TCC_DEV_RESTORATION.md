# Restauración directa en dev — auditoría 21 de octubre de 2026

Base: `97f2bc96d52beaa0c6cf14447c7bf3e108787a01`, rama `dev`.
Fuentes de lectura: `d8c6d067`, `749ccf56` (`codex/dev-tcc`) y la conciliación local `7e84464c`. Esta última parte exactamente del dev actual; se revisa su delta, sin fusionar ramas ni sustituir el árbol antiguo.

Los cambios locales de `frontend_U/dist` y `verify_live_meta_handshakes.py` quedan excluidos e intactos. Se registraron estado y hashes en `.artifacts/dev-tcc-qa`, ignorado por Git. El respaldo de hashes no es un respaldo de contenido.

## Inventario anterior a la restauración

| Funcionalidad | d8c6d067 | 749ccf56 | dev inicial | Acción |
|---|---|---|---|---|
| Modelos, cliente, catálogo y endpoints TCC | Sí | Sí | No | Recuperar |
| Perfiles logísticos y campos administrativos | Sí | Sí | No | Recuperar y mejorar avisos/filtros |
| Cotización en detalle | Sí | Sí | No | Recuperar |
| Cotización en tarjetas de catálogo | No | No | No | Incorporar mejora local posterior |
| Direcciones generales y selección en compra | Sí | Sí | Sí, mejoradas | Conciliar, conservar deduplicación |
| Códigos geográficos de transportadora | Sí | Sí | Retirados del modelo | Migración nueva 0019 |
| Checkout con transporte | Sí | Sí | Sin transporte | Conciliar con dirección e idempotencia actuales |
| Guías tras pago confirmado | Sí | Sí | No | Recuperar; pruebas simuladas, despachos desactivados |
| Seguimiento web e historial local | Sí | Sí | No | Recuperar |
| API remota de estados, cancelación y webhook TCC | No | No | No | Pendiente de contrato, no inventar endpoints |
| Productos históricos editables | Parcial | Corregido | Sí | Incorporar condición de publicación de 749ccf56 |
| Usuarios, contraseñas y protección de administradores | Anterior | Anterior | Mejorado | Conservar íntegro |
| Seguridad WebSocket | Anterior | Anterior | Mejorado | Conservar íntegro |
| CRM, adjuntos, plantillas, visitas, PDFs y correos | Sí | Sí | Sí | Conservar; conciliar representación del transporte |
| Eliminación de anuncios de envío gratis | No | No | Sí | Conservar |
| Migraciones 0014/0017/0018 actuales | No | No | Sí | No sustituir; añadir conciliación hacia adelante |
| Pruebas de ausencia de TCC | No | No | Sí | Adaptar a integración desactivada |
| Dist y archivo local de diagnóstico | Generados | Generados | Cambios ajenos | Excluir |

La causa comprobada es la retirada deliberada de módulos y conexiones en dev. La recuperación anterior solo existe en otra rama/worktree. No basta activar una variable: faltan aplicación Django, rutas, perfiles y componentes.

Se inspeccionaron nombres de archivos, resumen, historial divergente, range-diff, contenido de serializadores/vistas, modelos y migraciones. El delta conciliado comprende 83 archivos y conserva sin cambios los módulos de Usuarios y la seguridad de WebSocket. Los informes anteriores se conservan como evidencias históricas, no como resultados de esta ejecución.

## Contratos y límites

La documentación suministrada calcula el umbral por despacho: suma peso físico y volumétrico de los paquetes; PQT cuando cualquiera supera 5 kg, MSJ en otro caso. El peso volumétrico procede de dimensiones por paquete, no de una caja inventada. Falta contrato de consulta remota de estados, cancelación y webhooks; no se implementará una API supuesta.

El plan conserva 0014, 0017 y 0018 de dev, restaura las tres migraciones originales shipping y añade 0019 para recuperar el estado del código geográfico sin borrar columnas ni códigos históricos. Toda aplicación se verificará únicamente en PostgreSQL aislado.

## Implementación y diferencias deliberadas

Commits locales: `71676e38` (backend, migraciones, logística y pruebas), `41bd92e4` (editor, direcciones, catálogo, checkout y navegador). Base inicial `97f2bc96`. El commit documental posterior completa el informe; consultar `git log -3 --oneline` para su hash.

Se recuperaron `BACKEND/shipping` y sus rutas, configuración, perfiles, catálogo, cotización, guías idempotentes y pruebas. Se conciliaron ecommerce/models.py, serializers.py, views.py y pricing.py con las direcciones copiadas al pedido y pagos actuales. Se restauraron ShippingProfileFields, TCCAddressFields, ShippingCalculator, ShipmentDetails y shipping.ts, y se conectaron ProductsPage administrativo, ProductDetailPage, ProductCard, CartPage, CheckoutPage y pedidos. Se conservaron las mejoras de plantillas de la recuperación local.

Mejoras adicionales de esta ejecución: filtro SQL antes de paginar, `shipping_missing_fields` en listado, aviso editable bajo el nombre con campos faltantes, estado completo visible, foco/errores por campo logístico y valor declarado automático por defecto en perfiles nuevos. El perfil permanece visible con TCC desactivado. No se actualizan productos históricos al leerlos ni se crean perfiles por editar campos generales.

Se eliminaron los recargos porcentuales y de manipulación de las cotizaciones nuevas. Las variables anteriores se ignoran y no aparecen en los ejemplos nuevos. Las columnas históricas se conservan. Fórmula: subtotal + tarifa TCC + impuestos - descuentos. No hay nuevas reglas de impuestos o descuentos. El total se valida en backend y se recotiza antes de Wompi; la política nueva invalida cachés antiguas mediante fingerprint.

749ccf56: se conserva la validación al publicar/reactivar sin bloquear ediciones ordinarias de productos históricos; las pruebas generales fijan explícitamente TCC desactivado. Su variante 0017 se sustituye por la nueva 0019, no se copia sobre el historial de dev. Las migraciones 0014, 0017 y 0018 actuales no cambiaron. No hay diferencias en Usuarios, consumidores/autorización WebSocket ni UsersPage contra el dev inicial. Se mantienen f5fdf28a y la eliminación de promociones falsas.

## Endpoints

Rutas públicas bajo `/api/shipping/`: `config`, `cities`, `estimate`; rutas autenticadas `destination`, `quote`, `orders/<id>/<action>` con permisos por operación. Productos: `/api/ecommerce/products?shipping_status=complete|incomplete`, detalle y editor transaccional existentes. Direcciones: rutas existentes `/api/ecommerce/user/addresses`. No se añadió un webhook TCC no documentado.

## Validación ejecutada en Docker

Proyecto privado `tcc-dev-qa`, código montado desde dev, PostgreSQL/Redis aislados y datos sintéticos. No se usó la base normal de desarrollo ni producción para migraciones/pruebas.

| Verificación | Resultado |
|---|---|
| Backend ecommerce, shipping, CRM, correos, visitas, gestión y usuarios | 428 descubiertas/ejecutadas/aprobadas; 0 fallidas, 0 omitidas; 67,709 s |
| Gateway WhatsApp | 38 ejecutadas/aprobadas, 7 archivos; 0 omitidas/fallidas |
| TypeScript y compilación Vite | Aprobadas; salida `/tmp`, dist original intacto |
| Imágenes backend, frontend y gateway | Tres construcciones aprobadas |
| makemigrations --check --dry-run | No changes detected |
| migrate --plan, migrate --noinput, showmigrations | Aprobados en base aislada; ecommerce hasta 0019 y shipping hasta 0003 |
| product-shipping-cards.cjs | Dirección predeterminada/historial/sesión/manual, caché, actualización entre tarjetas, errores y responsive aprobados |
| template-editor-validation.cjs y template-preview.cjs | Variables, errores conservando borrador, prevención doble envío y formatos por canal aprobados |
| delivery-address-flow.cjs | Crear dirección sin perder compra, error/reintento/cancelación/persistencia aprobados |
| shipping-location.cjs | Selectores, cambio de destino, persistencia, error y reintento aprobados |
| recovery-completeness.cjs | Carrito, total pendiente, desglose y ausencia de promociones falsas aprobados |
| recovery-websocket.cjs | Nginx → ASGI → Redis, JWT y ping/pong aprobados |
| tcc-live-flow.cjs | Administrador guarda 6,100 kg y valor automático, recarga y confirma persistencia; catálogo → detalle → carrito → dirección nueva → cotización → pago simulado → pedido/guía únicos aprobado |

El flujo integrado utiliza Django y PostgreSQL reales de QA, con TCC y pago interceptados: subtotal 250.000 COP, transporte 30.000 COP, total 280.000 COP; webhook repetido, una orden, una guía y una llamada simulada de despacho. También verifica CRUD de direcciones y plantillas con persistencia. No es una guía real sandbox ni una transacción Wompi real.

Consulta externa autorizada de tarifas sandbox, desde Docker, Cali → Bogotá, sin crear guía: 2 kg MSJ y 5 kg MSJ rechazados con código seguro `route_not_configured` (proveedor -1); 6 kg PQT cotizado en **44.700 COP**. La causa exacta contractual del rechazo MSJ debe confirmarla TCC; no se cambió de cuenta para evitarlo. Las credenciales de desarrollo están presentes y las cuentas, origen, razón social y NIT coinciden con lo solicitado; ningún valor secreto se imprime ni versiona.

## Servicios y logs

| Servicio | Estado / salud / reinicios | Función comprobada | Memoria aproximada |
|---|---|---|---|
| Backend QA | running, sin healthcheck declarado, 0 reinicios | API config, suite y flujo persistente | 83 MiB |
| Frontend QA | running, sin healthcheck declarado, 0 | Navegador y build | 989 MiB durante pruebas |
| PostgreSQL QA | healthy, 0 | pg_isready, migraciones, persistencia | 63 MiB |
| Redis QA | running, 0 | PONG y grupos WebSocket | 4 MiB |
| Worker QA | running, 0 | inspect ping devuelve pong; cola aislada | 117 MiB |
| Beat QA | running, 0 | Arranque/scheduler sin errores; no se ejecutaron tareas comerciales reales | 116 MiB |
| Nginx QA | running, 0 | HTTP frontend y upgrade WebSocket | 11 MiB |
| WhatsApp local | healthy, 0 | Healthcheck existente y suite aislada de 38 pruebas; sin mensajes reales | 139 MiB |
| Ollama local | healthy, 0 | Lista de modelos incluye qwen:4b; sin generación/mensajes reales | 112 MiB |

CPU muestreada: servicios QA aproximadamente 0–0,3%, frontend durante pruebas aproximadamente 28%. No se reiniciaron servicios normales para desplegar estos cambios. No se atribuye una prueba de integración externa real a Meta/WhatsApp por haber pasado sus pruebas simuladas.

Logs QA backend/frontend/worker/beat/nginx/redis sin patrones de error en la ventana revisada. PostgreSQL registra violaciones de unicidad provocadas por pruebas negativas de CRM: cuenta WhatsApp activa, conversación activa, identificador externo y asociación de identidad. La suite también provoca fallos PDF, SMTP y timeout de Ollama para verificar manejo de errores; no son fallos de la ejecución final. El primer intento del gateway falló por longitud de la clave sintética de QA, se corrigió el entorno de prueba y pasó. Vite avisa de un chunk mayor de 500 kB; no impide compilación.

Comandos principales (siempre Docker):

```powershell
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py makemigrations --check --dry-run
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py migrate --plan
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py migrate --noinput
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py showmigrations shipping ecommerce
docker compose -f .artifacts/dev-tcc-qa/compose.yml run --rm backend python manage.py test ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios --noinput
docker compose -f .artifacts/dev-tcc-qa/build.yml build backend frontend gateway-test
```

Los scripts y registros operativos están en `.artifacts/dev-tcc-qa`, fuera del repositorio. Los informes de recuperación anteriores tienen alcance histórico y no sustituyen esta evidencia.

## Pendientes y activación futura

La implementación local quedó restaurada, pero **la aceptación externa completa sigue pendiente**: TCC debe habilitar/confirmar la ruta MSJ para la cuenta suministrada y entregar contrato de estados, webhook o consulta de seguimiento. Actualmente funcionan número de guía, enlace web e historial local; no se afirma seguimiento remoto automático ni ETA que el contrato no devuelve.

Se migró exclusivamente la base aislada solicitada. La base habitual de desarrollo no fue migrada ni sus servicios recreados: para usar la nueva API en el entorno habitual falta revisar/aplicar su plan con respaldo bajo una autorización que permita esa base. No se debe interpretar la prueba QA como un despliegue sobre localhost habitual.

Producción permanece desactivada por defecto. Cuando llegue la credencial productiva: aprobación de despliegue separada, respaldo y ensayo de migraciones, variables backend TCC_PRODUCTION_API_TOKEN y dominio oficial, cuentas/origen/remitente validados; después activación explícita de TCC_API_ENVIRONMENT=production, TCC_PRODUCTION_APPROVED y TCC_SHIPPING_ENABLED. Mantener TCC_DISPATCH_ENABLED desactivado hasta aprobar despachos controlados. No reutilizar token sandbox. Este informe no autoriza ninguna de esas acciones.

Se conservaron los archivos ajenos: hashes de dist sin cambios y archivo local de diagnóstico intacto; no se añadieron secretos, medios ni bases. Sin push, merge, PR, cambio de main ni producción. Rama final: dev.
