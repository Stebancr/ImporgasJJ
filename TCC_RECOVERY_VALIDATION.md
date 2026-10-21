# Recuperación local de TCC sobre dev actual — 20 de octubre de 2026

## Referencias y aislamiento

- Base: `97f2bc96d52beaa0c6cf14447c7bf3e108787a01`.
- Respaldo: `codex/backup-dev-before-tcc-recovery`, apunta a esa base. Conserva commits; no incluye archivos sin commit.
- Referencia exacta: `codex/tcc-pre-separation-reference` en `d8c6d067f0cd2d57de1a248629f5fd127b1a97e4`, worktree `.artifacts/tcc-pre-separation-reference`, sin modificaciones.
- Recuperación: `codex/recover-tcc-on-current-dev`, worktree `.artifacts/recover-tcc-on-current-dev`.
- `codex/dev-tcc` permanece en `749ccf5630251e6e33644a621070b6e4604ad05f`.
- Checkout original permanece en dev/97f2bc96, con los 100 cambios locales previos (dist y verify_live_meta_handshakes.py) fuera de esta recuperación. No se agregaron ni restauraron.
- Sin fetch, push, PR, cambios de main/dev ni despliegue. PR #7 no fue modificado.

## Recuperación selectiva

Se restauró BACKEND/shipping: cliente oficial, catálogo, perfiles, cotizaciones, despacho posterior a pago, eventos, tareas, endpoints, serializadores y pruebas. Se recuperaron los formularios logísticos, cotizador de producto/carrito, checkout y vistas de pedidos. No se copió el árbol antiguo completo ni se revirtieron commits mixtos.

Se conservaron sin diferencias respecto a dev Usuarios/Trabajadores, contraseñas, activos/inactivos, protección de administradores y seguridad WebSocket. Se conservaron la dirección del pedido y su instantánea, permisos, idempotencia, borradores y recuperación del checkout. Home/Login conservan f5fdf28a; carrito/checkout no reintroducen promociones ni umbrales de envío gratis.

El total con TCC activo utiliza subtotal + transporte cotizado por servidor + impuestos - descuentos. La tarifa se revalida antes del pago; se ignoran precios y cargos manipulados desde el navegador. Con TCC desactivado se mantiene envío NULL/fuera de la compra y aviso explícito, sin tarifa fija ni gratis por monto. Despachos inciertos requieren revisión, no reenvío ciego.

Compatibilidad de 749ccf56: edición no logística de productos históricos permitida sin crear perfiles ficticios; columna de ciudad preservada o creada si falta. El frontend omite el perfil no modificado al editar productos históricos. Los campos logísticos siguen permitiendo NULL; la cotización incompleta falla claramente antes de llamar al proveedor.

## Migraciones

Se restauraron intactas shipping.0001, 0002 y 0003. ecommerce.0014, 0017_preserve_legacy_address_writes y 0018_delivery_without_shipping permanecen idénticas a dev. No se copió la variante antigua 0017_resume_provider_address.

Se agregó ecommerce.0019_restore_provider_address: avanza el estado del modelo y crea tcc_city_code únicamente si falta. Conserva códigos existentes y establece default vacío PostgreSQL para que el modelo anterior pueda seguir insertando direcciones. No elimina columnas, perfiles ni datos; no hay valores logísticos de relleno ni migraciones fake.

Docker: makemigrations --check --dry-run, showmigrations, migrate --plan, migrate --noinput y check aprobados en PostgreSQL aislado. Plan final sin pendientes. Ensayos con bases sintéticas desde dev actual y desde d8c6d067: ambos aprobados, preservando contraseñas, roles, productos, direcciones y perfiles históricos. La suite también comprueba escrituras usando el modelo de direcciones anterior.

## Configuración segura

Nombres reales: TCC_SHIPPING_ENABLED=False, TCC_API_ENVIRONMENT=sandbox, TCC_DISPATCH_ENABLED=False, TCC_PRODUCTION_APPROVED=False. El alias development continúa admitido. Tokens, cuentas y remitente se dejan vacíos en los ejemplos y deben configurarse privadamente. Arranque sin token productivo y con bandera sandbox comprobado. Las máscaras vacías del gateway y Docker Compose permanecen intactas.

No se suministró contrato de tracking, cancelación o webhooks de TCC: solo se recupera el enlace de seguimiento web y el historial local; tracking_api_available=False. No se inventaron endpoints.

## Pruebas Docker y evidencias locales ignoradas

| Verificación | Resultado | Log en .artifacts/ del worktree |
|---|---|---|
| Django ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios | 419 aprobadas | tests-release.log |
| Gateway WhatsApp | 38 aprobadas | gateway-verified.log |
| TypeScript/Vite e imágenes backend/frontend/gateway | Aprobados | frontend.log, build-final.log |
| Inicio desactivado y sandbox sin token productivo | Aprobados | migration-final.log, start-sandbox.log |
| Actualización dev actual → recuperación | Aprobada | recovery_current_dev-after.log |
| Actualización esquema TCC anterior → recuperación | Aprobada | recovery_old_tcc-after.log |
| Flujo real de persistencia: login, dirección, carrito, cotización, pago firmado, webhook duplicado, pedido y guía simulada | Aprobado; 250000 productos + 30000 transporte = 280000 COP | browser-verified.log |
| Usuarios, chat con archivos y vistas previas de plantillas | Aprobados, 1280/768/390 | browser-verified.log |
| Editor: creación, validación, imágenes/principal, error/reintento, persistencia y edición | Aprobado | browser-products.log |
| Ubicación invitado, dirección opcional, errores y reintento | Aprobado | browser-carrier-matrix.log |
| Checkout/cambio de ciudad/recotización/Wompi/perfil/despacho/documento | Aprobado con API simulada | browser-carrier-matrix.log |

Cobertura TCC: <=5 kg MSJ, >5 kg PQT y peso volumétrico, perfiles incompletos, productos antiguos, direcciones válidas/incompletas, fallos y timeout, guía única, reintentos, desglose y protección de pago. CRM cubre contratos simulados de Meta, adjuntos, permisos, duplicados, formato y WebSocket. Correos, PDFs y visitas incluidos en regresión.

Los errores iniciales detectados se corrigieron: eliminación de producto con historial, expectativa anterior de bloqueo al editar producto histórico, etiquetas de pruebas previas y tiempos de carga. El primer intento de gateway carecía de variables obligatorias de QA; con valores sintéticos sus 38 pruebas pasan. El intento inicial de Vite escribía caché en dependencias de solo lectura; se usa configLoader runner y caché temporal.

No hubo pagos, correos, mensajes, tarifas ni guías reales. Los contratos externos se simularon. No se certifica tarifa sandbox real ni permisos productivos; siguen pendientes credenciales y autorización específica. No se escanearon archivos con antivirus inexistente.

## Commits locales y revisión

- 8f11e0b9: servicios TCC, migración hacia adelante, checkout backend y regresiones.
- 62ac5465: frontend recuperado, perfiles históricos, direcciones, cotización y pruebas de navegador.
- Commit documental posterior: este informe y documentación histórica recuperada.

Revisión de rutas: sin dist, verify_live_meta_handshakes.py, .env privados, medios ni bases. Escaneo de patrones de credenciales sin hallazgos. Los valores sintéticos de pruebas no son credenciales reales.

Contra d8c6d067/749ccf56 se mantiene la integración funcional disponible, agregando mejoras posteriores de cuentas/seguridad/direcciones, compatibilidad progresiva y banderas seguras. La migración antigua de retorno de direcciones se reemplaza por 0019; el cálculo fijo anterior y promociones de envío gratis no se recuperan.

## Continuación y límites

Revisar esta rama local antes de autorizar cualquier publicación o integración. No utilizar reset de dev para recuperar TCC. Para desactivar basta TCC_SHIPPING_ENABLED=False y TCC_DISPATCH_ENABLED=False. Las migraciones son aditivas; no eliminar datos ni restaurar bases para alternar código. Los contenedores QA usan red propia y PostgreSQL sintético, sin puertos públicos. Sus bases quedan disponibles para inspección; no se eliminó ningún volumen.

## Diferencias exactas frente a dev (antes del commit documental)

Salida de git diff --stat dev...codex/recover-tcc-on-current-dev:

```text
 .env.example                                       |   26 +
 .env.prod.example                                  |   24 +
 BACKEND/core/settings.py                           |   23 +
 .../migrations/0019_restore_provider_address.py    |   28 +
 BACKEND/ecommerce/models.py                        |   10 +
 BACKEND/ecommerce/pricing.py                       |   16 +-
 BACKEND/ecommerce/serializers.py                   |   69 +-
 BACKEND/ecommerce/test_shipping_independence.py    |   10 +-
 BACKEND/ecommerce/urls.py                          |    1 +
 BACKEND/ecommerce/views.py                         |   87 +-
 BACKEND/shipping/__init__.py                       |    0
 BACKEND/shipping/apps.py                           |    6 +
 BACKEND/shipping/catalog.py                        |   13 +
 BACKEND/shipping/cities.json                       | 6717 ++++++++++++++++++++
 BACKEND/shipping/e2e_server.py                     |   96 +
 BACKEND/shipping/migrations/0001_initial.py        |   93 +
 .../0002_shippingquote_provider_summary.py         |   18 +
 ...uctshippingprofile_declared_value_from_price.py |    7 +
 BACKEND/shipping/migrations/__init__.py            |    0
 BACKEND/shipping/models.py                         |   78 +
 BACKEND/shipping/serializers.py                    |   55 +
 BACKEND/shipping/services.py                       |  282 +
 BACKEND/shipping/tasks.py                          |  109 +
 BACKEND/shipping/tcc.py                            |  113 +
 BACKEND/shipping/test_estimates.py                 |  133 +
 BACKEND/shipping/test_recovery.py                  |   72 +
 BACKEND/shipping/tests.py                          |  398 ++
 BACKEND/shipping/urls.py                           |   11 +
 BACKEND/shipping/views.py                          |  125 +
 BACKEND/transactional_mail/documents.py            |    2 +-
 BACKEND/transactional_mail/service.py              |    5 +-
 .../templates/transactional_mail/message.html      |    2 +-
 .../templates/transactional_mail/message.txt       |    2 +-
 BACKEND/transactional_mail/tests.py                |    2 +-
 frontend_U/src/admin/pages/OrdersPage.tsx          |   30 +
 frontend_U/src/admin/pages/ProductsPage.tsx        |   23 +-
 frontend_U/src/admin/services/admin_products.ts    |    1 +
 frontend_U/src/admin/services/product_draft.ts     |    4 +-
 frontend_U/src/admin/types/index.ts                |    3 +
 frontend_U/src/app/pages/CartPage.tsx              |   16 +-
 frontend_U/src/app/pages/CheckoutPage.tsx          |  157 +-
 frontend_U/src/app/pages/MyOrdersPage.tsx          |    1 +
 frontend_U/src/app/pages/OrderDetailPage.tsx       |   16 +-
 frontend_U/src/app/pages/ProductDetailPage.tsx     |    6 +
 frontend_U/src/components/DeliveryAddressForm.tsx  |    7 +-
 .../src/components/DeliveryAddressInvitation.tsx   |    2 +-
 frontend_U/src/components/ShipmentDetails.tsx      |   28 +
 frontend_U/src/components/ShippingCalculator.tsx   |  137 +
 .../src/components/ShippingProfileFields.tsx       |   22 +
 frontend_U/src/components/TCCAddressFields.tsx     |   50 +
 frontend_U/src/hooks/useShippingConfig.ts          |   17 +
 frontend_U/src/services/addresses.ts               |    6 +-
 frontend_U/src/services/orders.ts                  |    3 +
 frontend_U/src/services/shipping.ts                |   45 +
 frontend_U/tests/product-editor-live.cjs           |    2 +-
 frontend_U/tests/shipping-location.cjs             |   89 +
 frontend_U/tests/tcc-checkout.cjs                  |  156 +
 frontend_U/tests/tcc-live-flow.cjs                 |  192 +
 frontend_U/vite.config.ts                          |    1 +
 59 files changed, 9549 insertions(+), 98 deletions(-)
```

Salida de git diff --name-status dev...codex/recover-tcc-on-current-dev:

```text
M	.env.example
M	.env.prod.example
M	BACKEND/core/settings.py
A	BACKEND/ecommerce/migrations/0019_restore_provider_address.py
M	BACKEND/ecommerce/models.py
M	BACKEND/ecommerce/pricing.py
M	BACKEND/ecommerce/serializers.py
M	BACKEND/ecommerce/test_shipping_independence.py
M	BACKEND/ecommerce/urls.py
M	BACKEND/ecommerce/views.py
A	BACKEND/shipping/__init__.py
A	BACKEND/shipping/apps.py
A	BACKEND/shipping/catalog.py
A	BACKEND/shipping/cities.json
A	BACKEND/shipping/e2e_server.py
A	BACKEND/shipping/migrations/0001_initial.py
A	BACKEND/shipping/migrations/0002_shippingquote_provider_summary.py
A	BACKEND/shipping/migrations/0003_productshippingprofile_declared_value_from_price.py
A	BACKEND/shipping/migrations/__init__.py
A	BACKEND/shipping/models.py
A	BACKEND/shipping/serializers.py
A	BACKEND/shipping/services.py
A	BACKEND/shipping/tasks.py
A	BACKEND/shipping/tcc.py
A	BACKEND/shipping/test_estimates.py
A	BACKEND/shipping/test_recovery.py
A	BACKEND/shipping/tests.py
A	BACKEND/shipping/urls.py
A	BACKEND/shipping/views.py
M	BACKEND/transactional_mail/documents.py
M	BACKEND/transactional_mail/service.py
M	BACKEND/transactional_mail/templates/transactional_mail/message.html
M	BACKEND/transactional_mail/templates/transactional_mail/message.txt
M	BACKEND/transactional_mail/tests.py
M	frontend_U/src/admin/pages/OrdersPage.tsx
M	frontend_U/src/admin/pages/ProductsPage.tsx
M	frontend_U/src/admin/services/admin_products.ts
M	frontend_U/src/admin/services/product_draft.ts
M	frontend_U/src/admin/types/index.ts
M	frontend_U/src/app/pages/CartPage.tsx
M	frontend_U/src/app/pages/CheckoutPage.tsx
M	frontend_U/src/app/pages/MyOrdersPage.tsx
M	frontend_U/src/app/pages/OrderDetailPage.tsx
M	frontend_U/src/app/pages/ProductDetailPage.tsx
M	frontend_U/src/components/DeliveryAddressForm.tsx
M	frontend_U/src/components/DeliveryAddressInvitation.tsx
A	frontend_U/src/components/ShipmentDetails.tsx
A	frontend_U/src/components/ShippingCalculator.tsx
A	frontend_U/src/components/ShippingProfileFields.tsx
A	frontend_U/src/components/TCCAddressFields.tsx
A	frontend_U/src/hooks/useShippingConfig.ts
M	frontend_U/src/services/addresses.ts
M	frontend_U/src/services/orders.ts
A	frontend_U/src/services/shipping.ts
M	frontend_U/tests/product-editor-live.cjs
A	frontend_U/tests/shipping-location.cjs
A	frontend_U/tests/tcc-checkout.cjs
A	frontend_U/tests/tcc-live-flow.cjs
M	frontend_U/vite.config.ts
```
