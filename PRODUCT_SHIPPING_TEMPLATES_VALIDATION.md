# Envío por producto y plantillas internas del CRM

Fecha: 2026-10-21. Base: `b012a052`, rama local `codex/recover-tcc-on-current-dev`.

## Resultado y limitación principal

El catálogo y el detalle muestran el precio del producto separado de la estimación
de entrega para el destino del cliente. El flujo integrado con PostgreSQL y
proveedores simulados pasa. **La cotización real sandbox permanece pendiente:**
el endpoint suministrado respondió HTTP 502 en las tres consultas de 2, 5 y 6 kg.
Esto no demuestra que la credencial o el convenio sean válidos. Tampoco permite
atribuir la causa interna del 502 a TCC o a un intermediario de red.

No se declara validado el recorrido con tarifa real. No hubo pagos, guías,
mensajes, correos ni modificaciones de producción. Las guías y eventos de pago
del ensayo integral son ficticios, dentro de una base temporal independiente.

## Fallos encontrados y correcciones

| Problema | Corrección |
|---|---|
| Las tarjetas no mostraban costo de entrega | Bloque común en ProductCard: destino, tarifa, cobertura, plazo si existe y total estimado |
| Repetir configuración/catálogo por tarjeta | Consulta de configuración compartida y catálogo deduplicado durante cinco minutos |
| Muchas tarjetas podían consumir el límite de checkout | Carga al entrar al área visible, máximo tres estimaciones simultáneas, presupuesto separado de estimación |
| La sesión desplazaba automáticamente la dirección predeterminada | Prioridad automática: predeterminada, historial válido, sesión; elección manual explícita prevalece durante esa sesión |
| El destino reciente solo consultaba cotizaciones | Busca el municipio válido más reciente entre pedidos y cotizaciones propios; no devuelve dirección ni teléfono |
| Cambiar ubicación en una tarjeta no actualizaba las demás | Evento compartido que invalida ubicación y cambia las claves de consulta |
| Faltaba advertencia explícita ante nueva tarifa | Checkout compara la estimación informativa o la cotización previa con la definitiva y avisa antes del pago |
| Variables añadidas al final del contenido | Selector y accesos rápidos insertan en el cursor, sin reemplazar el resto del borrador |
| Errores del servidor mostrados como JSON genérico | Errores por campo y aviso comprensible; el formulario sigue abierto y conserva datos |
| Doble clic podía iniciar dos operaciones de plantilla | Bloqueo inmediato mediante referencia, además del estado visual |
| Sin categoría equivalía al filtro Todas | Valores diferenciados para filtrar correctamente la categoría vacía |

## Ubicación y cotización

- `useDeliveryLocation` comparte consultas por usuario; no reutiliza la identidad
  de otro cliente. Los códigos guardados se validan contra el catálogo.
- La selección manual puede realizarse dentro de un modal en cualquier tarjeta.
  Departamento y municipio siguen siendo selectores separados con búsqueda.
- La dirección predeterminada tiene prioridad automática. Una selección manual
  intencional se conserva; borrar la ciudad invalida el destino manual anterior.
- Por respuesta expresa del usuario se usan direcciones y selección manual:
  **no se incorpora geolocalización ni consulta de IP a terceros**.
- La tarjeta cotiza una unidad. El detalle contempla su cantidad. Carrito y
  checkout cotizan nuevamente todos los productos y la dirección completa.
- React Query conserva temporalmente la estimación por usuario/producto/precio/
  municipio; la tarifa deja de mostrarse cuando vence. El caché del backend
  incluye cantidades, precios, dimensiones, pesos y configuración logística.
- El último importe estimado en memoria solo permite mostrar un aviso de cambio;
  nunca autoriza cobros ni sustituye una cotización del backend.
- Solicitudes obsoletas reciben AbortSignal. Las que esperan turno y ya están
  canceladas no realizan HTTP. Los fallos no generan reintentos automáticos en
  bucle; el cliente dispone de reintento explícito.
- Ausencia de ubicación, cobertura, perfil o respuesta: envío pendiente/error,
  sin precio inventado ni promoción general de envío gratuito.
- No se inventa un plazo: el contrato disponible no proporciona ETA actualmente.

## Pesos, cuentas y total

Se conserva la regla de los contratos y del plugin suministrado, documentada en
`TCC_INTEGRATION.md`: medidas individuales por paquete; suma de peso real y de
peso volumétrico de todos los paquetes del despacho. Si cualquiera de ambos
totales supera 5 kg corresponde PQT; de otro modo MSJ, incluyendo exactamente
5 kg. No se decide la cuenta evaluando aisladamente cada paquete.

MSJ: código 2 / cuenta 5625200; PQT: código 1 / cuenta 1485100. El convenio
comercial debe confirmarse con TCC si difiere del material entregado. No existe
un contrato adicional de seguimiento remoto o un plazo confirmado que permita
añadirlos por suposición.

El backend mantiene la validación de carrito, precios vigentes, perfil,
dirección, cotización, vencimiento y nueva tarifa antes de generar el pago:

`total = subtotal + envío + impuestos - descuentos`

La orden conserva por separado subtotal, shipping_cost, taxes, discounts y
paid_total. El navegador no envía un importe de transporte confiable. Las
notificaciones verificadas de Wompi conservan idempotencia. Los productos
históricos siguen editables; falta de logística bloquea la cotización/guía,
no la visualización. El indicador administrativo de logística incompleta y
la validación de perfiles ya existentes se conservaron.

## Plantillas

Se preservan CRUD, duplicación, confirmación de eliminación, búsqueda, filtros,
activación y permisos del backend. Se añadieron título de formulario, selección
del estado al guardar, selector de variables en el cursor, errores junto a
campos y comprobación de longitud por canal usando el texto de ejemplo.

Las vistas previas existentes siguen diferenciando e-commerce, WhatsApp Web,
Facebook e Instagram. Negrilla/cursiva se representan o degradan a texto plano
según el adaptador. Las variables definitivas se validan nuevamente al preparar
y enviar el mensaje; sus valores reales pueden exceder el ejemplo y requieren
esa validación final. Los adjuntos continúan autenticados. No se crean plantillas
comerciales de Meta ni se envían mensajes reales.

## Archivos

- Backend: `core/settings.py`, `shipping/views.py`, `shipping/test_estimates.py`.
- Configuración de ejemplo: `.env.example`, `.env.prod.example`.
- Catálogo/detalle: `components/ProductCard.tsx`, nuevo
  `components/ProductShippingEstimate.tsx`, `components/ShippingCalculator.tsx`.
- Estado compartido: nuevo `hooks/useDeliveryLocation.ts`,
  `hooks/useShippingConfig.ts`, `services/shipping.ts`, `services/addresses.ts`.
- Compra: `app/pages/CheckoutPage.tsx`.
- Plantillas: `admin/components/TemplateDialog.tsx`.
- Pruebas: nuevos `tests/product-shipping-cards.cjs` y
  `tests/template-editor-validation.cjs`; ampliados `tests/tcc-checkout.cjs`,
  `tests/tcc-live-flow.cjs`, `tests/template-preview.cjs`.

Las rutas anteriores de frontend son relativas a `frontend_U/src`, salvo las
pruebas, que son relativas a `frontend_U`. No se crearon migraciones ni modelos.
`makemigrations --check --dry-run`: **No changes detected**.

## Configuración y endpoints

Nuevo parámetro opcional: `THROTTLE_SHIPPING_ESTIMATE_RATE`, por defecto 60/min.
El checkout conserva `THROTTLE_SHIPPING_QUOTE_RATE`, por defecto 10/min.
Las credenciales solo se leen en backend. Variables ya requeridas para sandbox:
`TCC_API_TOKEN`, `TCC_API_ENVIRONMENT`, `TCC_DEVELOPMENT_BASE_URL`,
`TCC_SHIPPING_ENABLED`, `TCC_MSJ_ACCOUNT`, `TCC_PQT_ACCOUNT`,
`TCC_ORIGIN_CITY_CODE`, y datos `TCC_SENDER_*` cuando corresponde despachar.
`TCC_DISPATCH_ENABLED` y `TCC_PRODUCTION_APPROVED` permanecen desactivados en QA.
No se modificó ningún archivo privado de entorno.

- `GET /api/shipping/destination`: ampliado para pedidos e historial válido.
- `POST /api/shipping/estimate`: mismo contrato, límite independiente.
- `GET /api/shipping/config`, `/api/shipping/cities` y
  `POST /api/shipping/quote`: contratos conservados.
- Plantillas: endpoints `/api/crm-chat/templates/` conservados.
- No hay nuevos endpoints, WebSockets, permisos ni URLs públicas de terceros.

## Verificaciones Docker

| Verificación | Resultado |
|---|---|
| Suite backend ecommerce/shipping/crmChat/transactional_mail/AppVisits/gestion/usuarios | 424 descubiertas y ejecutadas, 424 aprobadas, 0 fallidas, 0 omitidas |
| Catálogo personalizado y destino | Prioridad predeterminada > historial > sesión, cambio manual, propagación entre tarjetas, caché, error/reintento y tres tamaños aprobados |
| Detalle de invitado | Cantidad/ciudad invalidan, ubicación persiste entre productos, sin tarifa falsa; aprobado |
| Checkout de navegador | Cambio de tarifa avisa, fallo bloquea pago, reintento conserva referencia, monto backend; aprobado |
| Editor y filtros de plantillas | Inserción en cursor, variables inválidas, límites, doble clic, error preserva borrador, categoría vacía y estado; aprobado |
| Preview y adjuntos | Tres estilos de canal, XSS, formato, PDF protegido y error de adjunto; aprobado |
| Flujo integral con PostgreSQL | Catálogo → detalle → carrito → dirección nueva → cotización → pago simulado → orden persistida; aprobado |
| Total y duplicados | Productos 250.000 + envío 30.000 = 280.000 COP; evento repetido mantiene una sola orden y despacho ficticio |
| Inicio QA con TCC desactivado | Config HTTP 200; estimación HTTP 503 controlado, sin contactar al proveedor |
| Construcción frontend Docker | TypeScript y Vite aprobados |
| Sandbox real | 2/5 kg MSJ y 6 kg PQT: HTTP 502 en los tres; pendiente externo |

Comandos utilizados (rutas de QA ignoradas por Git):

```text
docker compose -f .artifacts/build.yml build frontend
docker compose -f .artifacts/compose.yml run --rm -T backend python manage.py makemigrations --check --dry-run
docker compose -f .artifacts/compose.yml run --rm -T -e DJANGO_SETTINGS_MODULE=recovery_test_settings -e PYTHONPATH=/app:/qa -e RECOVERY_QA_TEST_DB=test_recovery_catalog_templates -v <worktree>/.artifacts:/qa:ro backend python manage.py test ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios --noinput
docker compose -f .artifacts/compose.yml run --rm -T browser ... node /tests/product-shipping-cards.cjs
docker compose -f .artifacts/compose.yml run --rm -T browser ... node /tests/shipping-location.cjs
docker compose -f .artifacts/compose.yml run --rm -T browser ... node /tests/tcc-checkout.cjs
docker compose -f .artifacts/compose.yml run --rm -T browser ... node /tests/template-preview.cjs
docker compose -f .artifacts/compose.yml run --rm -T browser ... node /tests/template-editor-validation.cjs
docker compose -f .artifacts/compose.yml run -d --name catalog-complete-e2e backend python -m shipping.e2e_server --tcc-e2e
docker compose -f .artifacts/compose.yml run --rm -T -e QA_API_URL=http://catalog-complete-e2e:8099 -e QA_WEB_URL=http://crm.localhost -e QA_FRONTEND_HOST=nginx browser ... node /tests/tcc-live-flow.cjs
```

Los puntos suspensivos representan la instalación temporal de Playwright dentro
del contenedor, no ejecución en el anfitrión. Evidencias en `.artifacts`:
`catalog-backend.log`, `catalog-location-final.log`, `catalog-ui-final.log`,
`catalog-templates-final.log`, `catalog-complete-e2e.log`,
`catalog-release-build.log`, `catalog-migrations.log`, `catalog-sandbox.log`;
capturas `product-shipping-{1280,768,390}.png` y
`template-editor-{1280,768,390}.png`. No se versionan imágenes ni logs.

## Seguridad y pendientes

El checkout original continúa en dev/97f2bc96 con sus 100 rutas locales
preexistentes intactas; main, PR y producción no se modificaron. Se usaron solo
commits locales en el worktree de recuperación. No se copiaron credenciales al
código ni a la imagen frontend. La consulta real sandbox leyó exclusivamente
el token de desarrollo en memoria mediante un montaje privado de solo lectura;
sus salidas contienen únicamente peso, tipo de cuenta y código de error.

Pendiente: investigar el HTTP 502 del endpoint sandbox con el operador de TCC o
la red y repetir las tres cotizaciones. No se cambió la URL contractual ni se
desactivó TLS. Tampoco se habilitó producción para eludir el error. La recuperación
de una tarifa real y la habilitación productiva no quedan aprobadas por este
ensayo. El despliegue y el push siguen fuera de alcance.
