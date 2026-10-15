# TCC: cotización, desglose y validación de extremo a extremo

Fecha: 15-10-2026. Rama `dev`. Solo Docker; sin despliegue ni cobros/despachos reales.

## Cambios de esta entrega

- Ficha de producto: selector de departamento/municipio TCC, dirección/código postal
  opcionales, botón **Calcular envío**, importe y destino. Siempre es una estimación
  identificada; no se acepta su resultado como autorización de cobro.
- Carrito: todos los productos/cantidades, dirección propia guardada o ingresada,
  cotización completa cuando están disponibles contacto y dirección. Cambiar cantidad,
  dirección o municipio invalida la anterior. Si falta información se identifica como
  estimación; nunca se inventa un costo cero ni se conserva una tarifa anterior visible.
- Destino del carrito se traslada al checkout en sessionStorage separado por usuario;
  no se trasladan importes como fuente confiable. Django valida nuevamente la dirección,
  dueño, precios, cantidades, empaque, vigencia y tarifa antes de emitir el total firmado.
- Panel de productos señala **Datos de envío pendientes**. Se conservan los perfiles,
  validaciones y paquetes separados de la primera entrega. Los cuatro productos locales
  existentes carecen de datos logísticos; no se inventaron ni completaron automáticamente.
  No hay un flujo de cobro con transporte manual indeterminado en este negocio: el
  cliente debe cotizar correctamente o contactar al asesor antes de pagar.
- Desarrollo configurado con razón social/documento suministrados, sede Cali Sur y
  código 76001000. `TCC_SHIPPING_ENABLED=True` local; **TCC_DISPATCH_ENABLED=False**.
  Producción sigue sin habilitarse ni recibir estos cambios.
- URLs TCC configurables por entorno y restringidas a los hosts oficiales. Tokens
  anulados en los servicios gateway de Node y ausentes de variables frontend.

## Desglose persistido y protegido

Se reutilizan los nombres canónicos existentes para evitar duplicar subtotal/envío.

| Concepto solicitado | Campo persistido |
|---|---|
| subtotal_productos | `Order.subtotal` / `WompiPaymentIntent.subtotal` |
| costo_envio | `shipping_cost`, separado del precio de cada producto |
| descuentos | `discounts`, descuentos adicionales |
| impuestos | `taxes`, impuestos adicionales |
| total a cobrar | `total = subtotal + shipping_cost + taxes - discounts` |
| total pagado | `Order.paid_total`, null hasta aprobación validada |

Después de una aprobación válida, `paid_total = total` y se cumple la misma fórmula.
Una intención pendiente no se presenta como dinero ya recibido. Registros históricos
no se reescriben ni se rellenan con pagos supuestos.

Los precios de venta vigentes ya son los que el ecommerce usa para cobrar. No existe
motor de cupones ni de impuestos adicionales: ambos ajustes se calculan en cero desde
el servidor. El ahorro respecto a `original_price` ya está reflejado en `price`; no se
descuenta dos veces. Esto conserva el tratamiento actual; no constituye una definición
de clasificación fiscal ni supone que los productos estén exentos. Reglas nuevas de
impuestos/descuentos requieren definición del negocio antes de aplicar otros importes.
La interfaz usa «adicionales» para distinguirlos de los precios de venta vigentes.
El usuario confirmó expresamente conservar los precios vigentes sin cargos ni
descuentos adicionales. Por tanto, recargo porcentual y manipulación TCC también
quedan en cero en desarrollo: solo se agrega la tarifa del transportador.

`ecommerce/pricing.py` realiza aritmética Decimal y rechaza componentes negativos o
no finitos. Checkout recalcula precios con la base de datos; campos monetarios enviados
por el navegador no se usan. Antes de aceptar Wompi también se verifica la coherencia
del desglose almacenado y el importe/moneda/referencia/firma del evento.

## Metadatos y contrato

La orden física conserva su cotización por `Shipment.quote`: paquetes con dimensiones,
pesos, valor declarado, origen/destino normalizados, cuenta, entorno, fecha/expiración,
tarifa, recargo y total. `ShippingQuote.provider_summary` conserva solamente resultado
normalizado y `totaldespacho`, nunca cuerpos brutos, tokens o credenciales.

El contrato entregado no devuelve un identificador externo de cotización ni un plazo
de entrega confirmado: `carrier_quote_id` y `estimated_delivery` son null. El UUID de
cotización es local. La UI no promete días de entrega ni inventa identificadores.

La cuenta se elige **por envío completo**, sumando pesos reales y volumétricos de
todas las unidades/cajas: si cualquiera supera 5 kg se utiliza PQT 1485100/código 1;
en caso contrario, incluida la igualdad a 5 kg, MSJ 5625200/código 2. Es el criterio
de acumulación y condicional del plugin TCC v2.5.1 entregado. Cada paquete conserva
sus medidas; no se suman largos/anchos/altos ni se divide la orden automáticamente.
Fórmula, unidades y fuentes se detallan en `TCC_INTEGRATION.md`.

## Endpoints

Rutas públicas de frontend mediante Nginx; Django mantiene los nombres internos sin
el prefijo `/api`, que elimina el proxy actual.

| Método/ruta pública | Función |
|---|---|
| GET `/api/shipping/config` | Indicador de activación y unidades, sin credenciales |
| GET `/api/shipping/cities` | Catálogo de 1.343 municipios, códigos de ocho dígitos |
| POST `/api/shipping/estimate` | Nuevo: estimación pública, limitada, sin guardar órdenes ni direcciones |
| POST `/api/shipping/quote` | Cotización autenticada para el carrito exacto y dirección completa |
| POST `/api/orders` | Revalidación, desglose e intención/orden pendiente con firma Wompi |
| POST `/api/webhooks/wompi` | Evento de pago verificado; ruta existente sin barra final |
| GET `/api/orders`, `/api/orders/tracking/<uuid>` | Orden y envío del dueño autorizado |
| POST `/api/shipping/orders/<id>/retry` | Solo administrador; error confirmado, no operación incierta |
| POST `/api/shipping/orders/<id>/sync` | 409: consulta remota diferida por falta de contrato |

Estimaciones tienen caché por entradas normalizadas y revisión de empaque; caducan y
no tienen UUID pagable. La cotización de checkout se guarda aparte y se revalida con
TCC antes de cobrar. Refrescar manualmente puede evitar la caché; cambios normales
reutilizan solo una cotización de entradas idénticas y vigente.

## Verificación realizada dentro de Docker

- **233 pruebas** de shipping/ecommerce/crmChat/usuarios.test_account aprobadas en
  PostgreSQL de prueba. Incluyen pesos límite, varios productos, empaques, ciudad de
  Cali y Bogotá, cantidad/destino/revisión de empaque, caché y expiración, falta de
  logística, cobertura/tarifa, timeout, credenciales, permisos e idempotencia.
- Manipulación de precio/envío/total/impuestos/descuentos desde el navegador: no
  cambia el cálculo de la orden. Desglose persistido alterado: se rechaza el pago.
- TypeScript, Vite y las cuatro pruebas existentes de cliente Wompi.
- Compose dev validado; Compose prod validado solo en sintaxis/interpolación con
  marcadores QA, sin iniciar servicios ni validar credenciales reales de producción.
- Prueba de navegador con **Django y PostgreSQL reales en base temporal independiente**:
  login → dirección guardada → estimación de producto → agregar al carrito → cambiar
  cantidad/ciudad → cotizar → conservar dirección en checkout → intención y orden
  pendiente → evento firmado de pago simulado → guía → enlace visible al cliente.
- Dos eventos idénticos de aprobación dieron una orden, una intención, un envío y
  **una única llamada de despacho simulada**. Antes de aprobar: cero despachos.
- Responsive en 1280 y 390 durante el recorrido completo. Pruebas de interfaz con
  APIs interceptadas también cubren 1280/768/390, errores bloqueantes, reintento
  administrativo, documentos y guardado/recarga de perfiles.
- TCC y Wompi se simulan en el flujo de pago/guía. No se llamó a la creación de
  despachos real ni se hizo ningún cobro. La base temporal solo contiene datos QA y
  se elimina al finalizar; la base normal y producción no se usan como fixtures.

### Tarifas reales del sandbox, sin crear despachos

Origen Cali 76001000; caja sintética de 10 × 10 × 10 cm, volumétrico 0,40 kg,
valor declarado 100.000 COP, consultada el 15-10-2026. No son tarifas universales.

| Cuenta/peso | Destino | Resultado |
|---|---|---|
| MSJ / 2 kg | Cali 76001000 | 9.820 COP |
| MSJ / 2 kg | Bogotá 11001000 | Sin tarifa configurada; código proveedor -1 |
| PQT / 6 kg | Cali 76001000 | 30.600 COP |
| PQT / 6 kg | Bogotá 11001000 | 44.700 COP |

Para MSJ → Bogotá TCC respondió «No existe tarifa para la ruta solicitada». La
aplicación informa el problema y no cambia de cuenta ni cobra un envío inventado.
Confirmar esa ruta/convenio/ambiente con TCC.

### Ejemplo persistido del recorrido completo de prueba

Dos unidades de 125.000 COP, cotización TCC **simulada** de 30.000 COP:

```json
{
  "subtotal": "250000.00",
  "shipping_cost": "30000.00",
  "discounts": "0.00",
  "taxes": "0.00",
  "total": "280000.00",
  "paid_total": "280000.00"
}
```

Wompi recibió 28.000.000 centavos. El subtotal/precio de producto no incluye el
envío. La guía QA `999000001` es simulada; nunca utilizarla para un envío real.

## Migraciones y conservación de datos

- `ecommerce.0015_order_discounts_order_paid_total_order_taxes_and_more`: agrega
  discounts/taxes en orden/intención (cero), paid_total nullable en orden.
- `shipping.0002_shippingquote_provider_summary`: agrega resumen JSON vacío para
  cotizaciones anteriores. No contiene secretos.
- Ambas aplicadas solo en desarrollo tras revisar el plan y crear respaldo.
- Respaldo privado `.artifacts/tcc-pricing-before-20261015.dump`, validado mediante
  lectura completa con pg_restore. SHA-256:
  `0fbe1282f21daa3a59670bde82063fb5d29313010f57d179e92338b980cccab2`.
- Hashes de todas las columnas y datos preexistentes iguales tras las migraciones;
  no se eliminó ni se ajustó ningún producto, orden, precio, pago o dirección previa.
- Backend, Celery Worker y Beat locales se recrearon para cargar el entorno actual.
  No se reinició ni desplegó el servidor de producción.

## Archivos principales afectados

- Backend: `core/settings.py`; `ecommerce/{models,serializers,views,pricing}.py`;
  `shipping/{models,serializers,services,tcc,views,urls,test_estimates,e2e_server}.py`;
  las dos migraciones indicadas.
- Frontend: `components/{ShippingCalculator,TCCAddressFields}.tsx`;
  `hooks/useShippingConfig.ts`; páginas ProductDetail, Cart, Checkout, OrderDetail;
  páginas administrativas Products y Orders; tipos/servicios shipping y orders;
  `tests/tcc-live-flow.cjs`.
- Configuración: ejemplos de entorno y Compose dev/prod para excluir tokens del gateway.

## Variables y comandos

Variables backend: `TCC_SHIPPING_ENABLED`, `TCC_API_ENVIRONMENT`,
`TCC_DEVELOPMENT_BASE_URL`, `TCC_PRODUCTION_BASE_URL`, `TCC_API_TOKEN`,
`TCC_PRODUCTION_API_TOKEN`, `TCC_PRODUCTION_APPROVED`, `TCC_DISPATCH_ENABLED`,
`TCC_PQT_ACCOUNT`, `TCC_MSJ_ACCOUNT`, `TCC_ORIGIN_CITY_CODE`, `TCC_SENDER_*`,
`TCC_SHIPPING_MARKUP_PERCENT`, `TCC_SHIPPING_HANDLING_FEE`,
`TCC_QUOTE_TTL_SECONDS`, `THROTTLE_SHIPPING_QUOTE_RATE`, `THROTTLE_SHIPPING_ADMIN_RATE`.
Ver ejemplos sin secretos en `.env.example` y `.env.prod.example`.

```sh
# Suite: comportamiento anterior por defecto, pruebas TCC habilitan su bandera explícitamente.
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 -e TCC_SHIPPING_ENABLED=False backend python manage.py test shipping ecommerce crmChat usuarios.test_account --noinput
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && node --test tests/wompiCheckout.test.mjs && npx vite build --outDir /tmp/tcc-v2-build'

# En dos terminales Docker. La primera sirve una base temporal QA por máximo 10 min.
docker compose -f docker-compose.dev.yml run --rm --no-deps -T --name tcc-e2e-backend -e CRM_TEST_POSTGRES=1 backend python -m shipping.e2e_server --tcc-e2e
docker compose -f docker-compose.qa.yml run --rm --no-deps -T chat-ui-test sh -c 'npm install --no-audit --no-fund --prefix /tmp/crm-ui playwright@1.58.2 && node /tests/tcc-live-flow.cjs'
```

## Pendientes y límites

1. Completar datos de empaque de los cuatro productos reales desde administración.
2. Confirmar tarifa MSJ Cali → Bogotá con TCC. Otras rutas deben cotizarse, no inferirse.
3. TCC no entregó contrato de seguimiento, códigos, cancelación ni webhook. Por tanto
   no se inventan actualizaciones ni una tarea diaria que consulte una API desconocida.
   Se conserva guía/historial local y enlace oficial, y el registro pendiente del
   documento principal. La entrega/transporte remoto **no queda validada** por una
   guía QA simulada. Implementarlo cuando TCC suministre el contrato.
4. Creación remota de guía, formato final de identidad de remitente y entrega de
   documentos reales no se probaron contra TCC porque los despachos reales están
   prohibidos durante esta tarea. Errores/timeout incierto no se reenvían a ciegas.
5. Producción requiere aprobación/despliegue separado, credencial propia y rotación
   del token compartido; no activar hasta resolver logística/rutas y validar pruebas
   autorizadas. Las nuevas reglas fiscales no se presumen.

Rollback: apagar la bandera TCC y volver a la imagen/revisión revisada anterior;
conservar campos/tablas nuevos. No revertir migraciones ni restaurar respaldos sobre
ventas posteriores sin análisis y autorización. Ver procedimiento principal.
