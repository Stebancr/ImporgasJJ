# Direcciones y checkout general en dev

## Comportamiento temporal

El valor del envío no está incluido en esta compra. Las condiciones de entrega serán confirmadas posteriormente. No existen tarifas, estimaciones ni cargos de transporte en el checkout. Django calcula: total = subtotal de productos + impuestos - descuentos. Los pedidos nuevos y sus intenciones guardan shipping_cost = NULL; los importes históricos se conservan sin modificaciones.

Se conservan direcciones por usuario, destinatario, teléfono, departamento, ciudad, barrio, complemento, código postal, indicaciones y dirección predeterminada. Los selectores de departamento y ciudad utilizan nombres geográficos locales, sin códigos de transportadora ni solicitudes externas. Se conservan los valores históricos aunque su escritura difiera del catálogo. Las direcciones tienen permisos por propietario y guardado idempotente. El registro puede invitar a guardar una dirección sin impedir navegar.

El checkout permite utilizar, crear y editar direcciones, asocia la dirección con el pedido mediante FK y conserva una copia de barrio, complemento e indicaciones; recupera el paso de pago al recargar con el mismo carrito y conserva un borrador local y solicita una intención Wompi con importe calculado por Django. La orden se confirma mediante el flujo oficial ya existente. Se conservan los campos generales de contabilidad y la validación de importes de pagos.

## Verificaciones Docker

- Regresión Django de ecommerce, CRM, visitas, correos, gestión y cuentas.
- `shipping-without-carrier.cjs`: dirección guardada realmente en PostgreSQL aislado; carrito responsive; subtotal y total $125.000, sin cargo de envío, y 12.500.000 centavos entregados al widget Wompi simulado; ninguna solicitud a transportadoras.
- `test_shipping_independence`: proveedor ausente de aplicaciones y configuración Django; endpoints retirados no resuelven; ausencia de costos de transporte en todos los importes de compra.
- No se realizaron cobros, despachos, correos ni mensajes a clientes reales.

Las cotizaciones, guías, perfiles logísticos y contratos del proveedor se retoman exclusivamente en `codex/dev-tcc`.
