# Direcciones y checkout general en dev

## Comportamiento temporal

Se recupera la regla comercial anterior: envío estándar de $25.000 COP para subtotales inferiores a $500.000 COP, y envío gratis desde $500.000 COP. Es una regla explícita previamente existente, no un valor de emergencia ante fallos de una transportadora. Backend calcula subtotal, envío, impuestos adicionales y descuentos; estos dos últimos permanecen en cero según la política autorizada. El cliente no decide el importe cobrado.

Se conservan direcciones por usuario, destinatario, teléfono, departamento, ciudad, barrio, complemento, código postal, indicaciones y dirección predeterminada. Los selectores de departamento y ciudad utilizan nombres geográficos locales, sin códigos de transportadora ni solicitudes externas. Se conservan los valores históricos aunque su escritura difiera del catálogo. Las direcciones tienen permisos por propietario y guardado idempotente. El registro puede invitar a guardar una dirección sin impedir navegar.

El checkout permite utilizar, crear y editar direcciones, conserva un borrador local y solicita una intención Wompi con importe calculado por Django. La orden se confirma mediante el flujo oficial ya existente. Se conservan los campos generales de contabilidad y la validación de importes de pagos.

## Verificaciones Docker

- Regresión Django de ecommerce, CRM, visitas, correos, gestión y cuentas.
- `shipping-without-carrier.cjs`: dirección guardada realmente en PostgreSQL aislado; carrito responsive; subtotal $125.000, envío $25.000, total $150.000 y 15.000.000 centavos entregados al widget Wompi simulado; ninguna solicitud a transportadoras.
- `test_shipping_independence`: proveedor ausente de aplicaciones y configuración Django; endpoints retirados no resuelven; límites de tarifa comercial explícitos.
- No se realizaron cobros, despachos, correos ni mensajes a clientes reales.

Las cotizaciones, guías, perfiles logísticos y contratos del proveedor se retoman exclusivamente en `codex/dev-tcc`.
