# Ubicación, direcciones y checkout — validación en dev

18 de octubre de 2026. Cambios locales sobre `dev`; se conserva el trabajo
anterior de TCC y plantillas. No se publica ni despliega producción.

## Problemas encontrados

- El componente geográfico ofrecía 1.343 registros en un solo desplegable.
- `/direcciones` y checkout conservaban los antiguos campos de ciudad y
  departamento junto al selector nuevo: pedían dos veces la misma información.
- El bloque de envío del producto dependía de que el servicio estuviera
  habilitado y estaba separado del precio; no explicaba siempre el envío pendiente.
- El checkout aceptaba una dirección escrita, pero no la guardaba en la cuenta.
  Su enlace de administración llevaba fuera de la compra.
- El paso del checkout solo vivía en memoria. POST de direcciones no protegía
  contra solicitudes repetidas o simultáneas.

## Implementación

`TCCAddressFields.tsx` conserva su nombre interno para mantener compatibilidad,
pero ahora muestra **Departamento de entrega** y **Ciudad o municipio de entrega**.
Por la indicación posterior del usuario, se retiraron los campos de búsqueda. Ambos son desplegables con orden alfabético y resultados
deduplicados. Ciudad permanece deshabilitada sin departamento. Cambiar departamento
vacía la ciudad y el código, invalidando la tarifa anterior. Los códigos internos
no se muestran en etiquetas. Hay estados de carga, error y reintento.

El producto presenta siempre un bloque de entrega junto al precio: precio unitario,
aviso de que el envío es adicional, estado pendiente sin tarifa, destino, costo
y total estimado cuando hay respuesta. No se inventan valores o plazos.
La selección de sesión permanece entre productos y una consulta anterior se
cancela cuando cambia el destino. El servidor conserva la caché basada en
producto, cantidades, destino y datos logísticos.

`DeliveryAddressForm.tsx` es el formulario compartido entre `/direcciones` y
checkout. Valida campos obligatorios, municipio y teléfono; incluye barrio,
complemento, código postal e indicaciones. No solicita departamento/ciudad dos
veces. Guarda, edita y conserva los datos ante errores. Se deshabilita durante
el guardado. `/direcciones` permite establecer la predeterminada y confirma la
eliminación con el diálogo accesible existente del proyecto.

Checkout ofrece tarjetas de direcciones con destinatario, teléfono, barrio,
dirección, municipio/departamento y marcador de predeterminada/seleccionada.
Agregar o editar abre el formulario dentro del mismo paso. Guardar selecciona
la dirección devuelta por el servidor y vuelve a consultar el envío. Cancelar
conserva la dirección anterior y el carrito.

El estado del checkout se guarda en sessionStorage por usuario: formulario,
dirección seleccionada, paso, contenido/cantidades de carrito e identificador de
cotización. Al recargar, se comprueba que la dirección guardada pertenezca a la
cuenta y se obtiene una cotización vigente. **No se restaura un importe del
navegador**. Si cambia el carrito o destino, no se reutiliza una tarifa anterior.
Mientras falta cotización válida, el botón de pago permanece deshabilitado y
el total se muestra pendiente. El carrito continúa usando su persistencia
existente en cuenta/servidor.

El backend serializa escrituras de direcciones por cuenta dentro de una
transacción. Un POST idéntico, incluso simultáneo, devuelve la dirección existente;
no modifica etiquetas históricas ni borra datos para deduplicar. Las comparaciones
normalizan mayúsculas y espacios. La primera dirección queda predeterminada.
Editar hacia otra dirección ya existente devuelve error; cambiar la predeterminada
mantiene una sola. Una dirección histórica reutilizada puede recibir el código
geográfico validado que le faltaba. Se conserva la propiedad por usuario.

## Archivos y API

- `frontend_U/src/components/TCCAddressFields.tsx`
- `frontend_U/src/components/ShippingCalculator.tsx`
- `frontend_U/src/components/DeliveryAddressForm.tsx` (nuevo)
- `frontend_U/src/app/pages/AddressesPage.tsx`
- `frontend_U/src/app/pages/CheckoutPage.tsx`
- `frontend_U/src/app/pages/ProductDetailPage.tsx`
- `frontend_U/src/app/pages/CartPage.tsx`
- `BACKEND/ecommerce/views.py`, `serializers.py`
- `BACKEND/ecommerce/test_delivery_addresses.py` (nuevo)
- `frontend_U/tests/tcc-live-flow.cjs`, `shipping-location.cjs`, `tcc-checkout.cjs`

Sin migraciones, nuevos modelos, dependencias ni variables de entorno.
Se reutilizan los endpoints existentes. Ajustes:

- POST `/api/ecommerce/user/addresses`: 201 para creación; 200 y mismo ID al
  repetir una dirección. Protección transaccional por usuario.
- PUT `/api/ecommerce/user/addresses/{id}`: actualización parcial, validación de
  duplicados y de ubicación, útil para cambiar la predeterminada.
- GET/DELETE de direcciones conservan sus permisos y alcance de cuenta.
- Cotizaciones y creación del pago mantienen la validación autoritativa de
  productos, transporte y total. No se agregan descuentos ni cargos nuevos.

## Pruebas Docker

Backend: 238 pruebas en PostgreSQL temporal; incluye reintentos concurrentes
(dos solicitudes devuelven un solo ID), validación, permisos entre usuarios,
predeterminada única, edición, eliminación, cotización y manipulación de importes.
`manage.py check` sin errores; `makemigrations --check --dry-run` sin cambios.

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 -e TCC_SHIPPING_ENABLED=False backend sh -c 'python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test shipping ecommerce crmChat usuarios.test_account --noinput'
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npm run build -- --outDir /tmp/delivery-checkout-build'
docker compose -f docker-compose.dev.yml run --rm --no-deps -T --name tcc-e2e-backend -e CRM_TEST_POSTGRES=1 backend python -m shipping.e2e_server --tcc-e2e
docker compose -f docker-compose.qa.yml run --rm --no-deps -T chat-ui-test sh -c 'npm install --no-audit --no-fund --prefix /tmp/crm-ui playwright@1.58.2 && node /tests/tcc-live-flow.cjs && node /tests/shipping-location.cjs && node /tests/tcc-checkout.cjs'
```

El flujo integral usa Django real y PostgreSQL temporal, con transportista y
pasarela simulados. Verifica producto → ubicación → estimación → carrito con
dos unidades → nueva dirección → error de guardado y reintento → dirección
persistida/seleccionada → cotización definitiva → paso de pago → recarga → pago.
Tras recargar conserva la dirección y el paso, y envía a la pasarela 28.000.000
centavos: productos 250.000 COP + transporte 30.000 COP = 280.000 COP.
Webhook repetido conserva una orden y un único despacho simulado.

Además verifica cancelación sin perder dirección, repetición de POST sin duplicado,
edición desde `/direcciones`, cambio de predeterminada, cancelación de eliminación,
eliminación confirmada, y regresiones del módulo de plantillas.
Pruebas de interfaz cubren ausencia de campos de búsqueda, ciudad dependiente, invalidación al cambiar
departamento, persistencia de ubicación, errores/reintentos y pantallas 1280,
768 y 390 px. Se mantienen las pruebas de dirección predeterminada, cambio de
tarifa, bloqueo de pago y total firmado por backend.

Logs privados: `.artifacts/delivery-*.log`. El servidor QA elimina únicamente su
base temporal al terminar; no se borran volúmenes ni datos de negocio.

## Límites

Comprobación de desarrollo del producto 5: existe, pero no hay fila en
`ProductShippingProfile` (`profile: None`). Por tanto, falla antes de llamar a
TCC. Se debe completar el perfil real desde administración: peso por paquete,
alto/ancho/largo, cantidad de paquetes, valor declarado y clasificación.
No se inventaron esos datos ni se insertó un perfil vacío para ocultar el problema.
Backend devuelve ahora `shipping_profile_incomplete` con un mensaje orientado
al cliente. El bloque de envío ofrece contacto con un asesor, sin sugerir que
reintentar o ir al checkout solucionará los datos faltantes.

El bloque visual de envío ahora separa encabezado, destino, estado, campos y
resumen. La estimación en producto solo requiere departamento y ciudad; la calle
y código postal se solicitan en los flujos de dirección y compra. Se retiraron
los campos de búsqueda según la corrección del usuario. Compilación Docker
correcta; persiste la advertencia previa de chunks grandes, sin errores.

Persisten requisitos operativos anteriores: completar peso/dimensiones y demás
datos logísticos reales de los productos, y confirmar con TCC las rutas sin tarifa.
Las pruebas no generan cobros, guías ni mensajes reales; no certifican disponibilidad
del proveedor externo. No hay nuevas credenciales ni cambios de producción.
Se preservan los artefactos `frontend_U/dist` y archivos locales ajenos a la tarea.
