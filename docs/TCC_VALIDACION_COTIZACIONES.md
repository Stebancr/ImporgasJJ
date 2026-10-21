# Validación de cotizaciones TCC y subsidio de envío

## Alcance y reproducción

Fecha: 2026-10-21. Ambiente efectivo: `development` (sandbox). Exclusivamente
cotizaciones; cero pagos, remesas, recogidas o mensajes reales. Sin escrituras en
base de datos durante las consultas externas. Las tarifas siguientes son las
respuestas observadas del sandbox, no precios garantizados de producción.

Comando ejecutado dentro del backend Docker de desarrollo:

```sh
docker exec backend python manage.py validate_tcc_quotes --sandbox-quote-only
```

El comando rechaza producción, un origen diferente de Cali y cualquier URL que
no corresponda al host oficial de pruebas y al endpoint de cotización. No lee ni
imprime clientes, direcciones, tokens ni cabeceras de autorización.

## Contrato utilizado

- Host sandbox: `https://testsomos.tcc.com.co`.
- Método: `POST`.
- Ruta: `/api/clientes/tarifas/v5/consultarliquidacion`.
- El adaptador requiere JSON y la credencial privada del contrato en AccessToken.
  Su valor no se incluye en este documento ni en las salidas del comando.
- TLS validado, sin seguir redirecciones. Timeout de conexión 5 s y lectura 12 s.
- Empresa remitente: ImporGas JJ S.A.S.; NIT 900739269-1; origen oficial Cali,
  Valle del Cauca, código `76001000`. No se usaron direcciones de clientes.
- Catálogo de ocho dígitos suministrado con el plugin; no se truncan códigos.

Solicitud sanitizada para PQT hacia Bogotá:

```json
{
  "tipoenvio": "",
  "idciudadorigen": "76001000",
  "idciudaddestino": "11001000",
  "valormercancia": 125000,
  "boomerang": 0,
  "identificacion": "",
  "cuenta": "1485100",
  "fecharemesa": "2026-10-21",
  "idunidadnegocio": 1,
  "unidades": [{
    "numerounidades": "1", "pesoreal": 6, "pesovolumen": 0.4,
    "alto": 10, "largo": 10, "ancho": 10, "tipoempaque": ""
  }]
}
```

Extracto relevante de una respuesta exitosa:

```json
{"codigoResultado": 0, "total": {"totaldespacho": 44700}}
```

Respuesta de rechazo observada para MSJ Cali–Bogotá y Cali–Medellín:

```json
{"codigoResultado": -1, "mensajeResultado": "No existe tarifa para la ruta solicitada"}
```

El adaptador guarda/expone únicamente el código seguro `route_not_configured`;
no propaga mensajes arbitrarios del proveedor que pudieran contener secretos.

## Matriz observada

Todas las consultas usaron una caja de **10 × 10 × 10 cm**, un paquete,
**$125.000** de valor declarado y peso volumétrico **0,40 kg**.
Todas recibieron **HTTP 200**, incluso los rechazos funcionales.

| Destino desde Cali | Código | MSJ, 2 kg | PQT, 6 kg |
|---|---|---:|---:|
| Bogotá, D.C. | 11001000 | Rechazada: ruta sin tarifa | $44.700 |
| Medellín | 05001000 | Rechazada: ruta sin tarifa | $44.700 |
| Barranquilla | 08001000 | $11.600 | $47.916 |
| Bucaramanga | 68001000 | $11.600 | $59.644 |
| Pereira | 66001000 | $11.600 | $44.700 |
| Palmira | 76520000 | $10.320 | $30.600 |

**10 cotizaciones aceptadas; 2 rechazadas; 0 errores HTTP.** Una tarifa aceptada
confirma la cotización de ese paquete y ruta en pruebas. Un rechazo no demuestra
falta de cobertura física. Ninguna respuesta proporcionó plazo de entrega; la UI
no inventa días ni presenta una promesa de entrega.

### Selección de cuenta y peso

Según el contrato/plugin disponible, la selección usa el agregado del despacho:
si peso real **o volumétrico** supera 5 kg se usa PQT; si ambos son <= 5 kg se usa
MSJ. Cada unidad logística conserva sus dimensiones, sin sumar largos ni crear
cajas ficticias. Las pruebas automatizadas incluyen 5 kg exactos, 5,001 kg,
varias unidades y peso volumétrico superior al físico.

| Cuenta | Código de negocio enviado | Número |
|---|---:|---|
| MSJ | 2 | 5625200 |
| PQT | 1 | 1485100 |

### Diagnóstico

Los códigos de origen/destino existen en el catálogo. Los paquetes son válidos y
las credenciales consiguen cotizaciones aceptadas en el mismo host. No hay
evidencia de token globalmente inválido, certificado fallido o cuenta MSJ
totalmente deshabilitada. La causa concreta comunicada por el proveedor para
Bogotá y Medellín es **ausencia de tarifa de esa ruta en MSJ sandbox**. No es
posible distinguir sin soporte si falta habilitación comercial, homologación o
configuración de rutas del ambiente. No se cambia de cuenta silenciosamente ni
se sustituye esa tarifa por cero, una tarifa fija o una cotización de PQT.

## Direcciones y endpoints internos

- Visitante: `/shipping/estimate` admite municipio temporal; no guarda dirección.
- Autenticado: la estimación exige `address_id` propio; un municipio aislado
  devuelve 400. Un ID ajeno devuelve 404, sin revelar su contenido.
- `/ecommerce/user/addresses`: creación, edición, predeterminada y borrado con
  permisos, bloqueo por cuenta y prevención de duplicados ya existentes.
- `/shipping/quote`: cotización definitiva del carrito; la interfaz utiliza la
  dirección persistida. Se recotiza antes del pago y se verifica la huella del
  carrito, revisión logística, dirección y política comercial.
- `/shipping/config`: umbral público, sin credenciales.
- `/shipping/promotion`: progreso calculado con precios del backend; no concede
  envío gratis por sí mismo y no llama a TCC.

## Política de envío gratis

Una sola configuración backend: `FREE_SHIPPING_THRESHOLD`, por defecto
**2000000 COP**. No se sobrescribieron archivos privados de entorno.

```text
subtotal_elegible = subtotal_productos - descuentos_productos
aplica = cotización válida con transporte y tarifa positiva
         Y subtotal_elegible >= umbral
cobro_cliente = 0 si aplica; tarifa_TCC en caso contrario
subsidio_envío = tarifa_TCC - cobro_cliente
total_cliente = subtotal_productos + cobro_cliente + impuestos - descuentos_productos
```

Los precios actuales ya representan el precio de venta; no existe motor de
cupones ni impuestos adicionales. Esos ajustes continúan en cero y no se aceptan
importes arbitrarios del navegador. La función de política sí prueba descuentos
de productos que dejan el subtotal por debajo del umbral.

- `ShippingQuote.tcc_rate`: tarifa real de TCC, nunca sobrescrita por cero.
- `ShippingQuote.total`: cobro al cliente; `snapshot.shipping_policy` congela
  costo real, cobro, subsidio, indicador, umbral y subtotal elegible.
- `Order.carrier_shipping_cost`: costo real.
- `Order.shipping_cost`: cobro al cliente; API alias `customer_shipping_charge`.
- `Order.shipping_discount`: subsidio, separado de `discounts` de productos.
- `Order.free_shipping_applied` y `free_shipping_threshold`: decisión y umbral.
- La intención conserva la política en `checkout_data.shipping_policy` y el
  cobro en `shipping_cost`. La orden guarda destino inmutable; Shipment enlaza
  cotización, fecha, cuenta y origen/destino.
- El precio de TCC se vuelve a verificar incluso si el cliente paga envío cero.
- El umbral forma parte de la huella de caché: cambiarlo invalida la cotización.
- Migración `ecommerce.0020_order_shipping_subsidy`: cuatro columnas NULL
  adicionales; no actualiza pedidos históricos, no borra ni inventa tarifas.

## Preguntas para soporte técnico TCC

1. ¿Pueden habilitar o confirmar las tarifas MSJ 5625200 de Cali 76001000 hacia
   Bogotá 11001000 y Medellín 05001000 en sandbox? El resultado es -1, mientras
   las mismas rutas PQT y las otras cuatro rutas MSJ sí cotizan.
2. ¿La cuenta está habilitada para cotización nacional y qué diferencias tiene
   el catálogo de rutas/tarifas de sandbox frente a producción?
3. ¿Confirman el endpoint y los códigos de población anteriores para producción?
4. ¿MSJ admite <=5 kg y PQT >5 kg considerando el agregado físico/volumétrico del
   despacho? ¿Cómo se agrupan múltiples unidades y cuál es el factor oficial?
5. ¿Cuáles son los límites de valor declarado, mínimos facturables y mercancías
   permitidas por cuenta? ¿Qué campos adicionales rechaza cada tipo de envío?
6. ¿Sandbox devuelve precios simulados o tarifas comerciales vigentes?
7. ¿Qué contrato permite consultar cobertura y plazo de entrega explícitamente?
8. ¿Qué habilitación requiere crear la guía después del pago? ¿Es necesario
   registrar previamente la sede de Cali, razón social o NIT/homologación?
9. ¿Qué permisos y credenciales productivas se requieren? Entregarlos únicamente
   mediante el mecanismo privado acordado, nunca en este documento.
10. ¿Pueden suministrar contrato de consulta de estados, cancelación y webhook de
    seguimiento? Por ahora solo existe enlace web oficial y no se inventan APIs.

## Límites y activación

No hay token productivo, no se activó producción ni se creó un despacho real.
Mantener `TCC_SHIPPING_ENABLED=False`, `TCC_DISPATCH_ENABLED=False` y
`TCC_PRODUCTION_APPROVED=False` en producción hasta revisión explícita. Los
ensayos de pago, duplicados y guías usan proveedores simulados y una base
PostgreSQL desechable. La aceptación de tarifas sandbox no certifica la operación
productiva ni reemplaza resolver las rutas MSJ pendientes con TCC.
