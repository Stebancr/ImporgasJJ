> Documento histórico recuperado. Para el estado actual, configuración y pruebas de esta rama consulta TCC_RECOVERY_VALIDATION.md.

# Ubicación de entrega y plantillas internas — desarrollo

Fecha: 18 de octubre de 2026. Rama `dev`, base `e46de09c`. `origin/main`
ya está contenido en esta base (comparación tras `git fetch`: 3 commits propios
de dev, 0 pendientes de main). No se despliega ni se modifica producción.

## Causas y cambios

El cotizador de producto no cargaba direcciones: su efecto estaba limitado a
`cart`. Tampoco recuperaba la sesión y necesitaba pulsar Calcular. Ahora carga
la dirección predeterminada con código TCC válido, recupera el municipio de la
última cotización autenticada si falta dirección, y conserva la selección de
sesión. Una ubicación cambiada explícitamente en la sesión prevalece para no
restablecer la dirección predeterminada al navegar. Cada usuario tiene su clave
de sesión; el visitante utiliza una clave independiente.

Sin ubicación se muestra «Configurar ubicación de entrega», con el formulario
plegado. Con ubicación se consulta automáticamente, con debounce de 500 ms,
AbortController y descarte de respuestas anteriores. Se muestran envío,
productos, total estimado y municipio. Solo se muestra plazo si el proveedor lo
devuelve. Un error elimina la tarifa anterior y permite reintentar, sin indicar
envío gratis. La ubicación permanece aunque TCC falle o falten medidas.

Por indicación posterior del usuario, no se incorporan geolocalización ni
proveedor por IP. Tras registrarse aparece una invitación opcional a agregar
dirección, que se puede omitir. Se reutiliza Mis Direcciones; la primera se
guarda como predeterminada y el formulario conserva sus datos ante errores.
La navegación y el registro no requieren dirección. El checkout sí debe tener
la dirección completa para la cotización definitiva.

El carrito y checkout conservan la recotización autoritativa existente. Nunca
se cobra el importe almacenado en el navegador. El servidor conserva subtotal,
transporte, impuestos y descuentos separados y genera el total de Wompi.
Se mantiene la decisión aprobada: precios vigentes, impuestos/descuentos
adicionales en cero y sin nuevos recargos.

La selección de cuenta sigue el plugin suministrado: se suman los pesos reales
y volumétricos de todas las unidades logísticas del despacho. Si alguno supera
5 kg se usa PQT 1485100/unidad 1; en otro caso MSJ 5625200/unidad 2. El límite
no se evalúa individualmente por producto. Las dimensiones permanecen por caja.
Detalle y fuentes existentes: `TCC_INTEGRATION.md`, sección Empaque.

Las plantillas eran un selector de borradores con edición básica. Se agregan
duplicación como inactiva, eliminación confirmada, filtros por canal/estado,
ejemplos sustituidos, variables de pedido/técnico/seguimiento, validación de
variables incompletas y nombres repetidos (sin renombrar históricos), etiquetas
de canal/estado y mensajes de carga/error/éxito. Duplicación y eliminación se
auditan; se conservan los archivos compartidos e históricos. El rol 4 administra;
los permisos existentes de consulta/inserción para rol 1 se conservan. No se
crean plantillas comerciales de Meta ni se envían mensajes al previsualizar.

## Archivos

- Backend: `shipping/views.py`, `shipping/urls.py`, `shipping/test_estimates.py`.
- CRM backend: `crmChat/quick_replies.py`, `crmChat/test_chatbot_upgrade.py`.
- Frontend: `components/ShippingCalculator.tsx`, `services/shipping.ts`,
  `services/api.ts`, `components/DeliveryAddressInvitation.tsx`,
  `components/Layout.tsx`, `app/pages/LoginPage.tsx`, `app/pages/AddressesPage.tsx`.
- CRM frontend: `admin/components/TemplateDialog.tsx`, `admin/pages/ProductsPage.tsx`.
- Pruebas: `tests/tcc-live-flow.cjs`, `tests/shipping-location.cjs`.

## API y configuración

- Nuevo GET `/api/shipping/destination`: autenticado, devuelve solo municipio
  de la última cotización del propio usuario; `Cache-Control: private, no-store`.
- Nuevo POST `/api/crm-chat/templates/{id}/duplicate/`: rol 4, copia inactiva.
- Nuevo DELETE `/api/crm-chat/templates/{id}/`: rol 4, conserva archivos físicos.
- Se mantienen `/api/shipping/estimate`, `/quote` y el preview seguro de plantillas.
- Sin migraciones, dependencias o variables de entorno nuevas. Credenciales TCC
  continúan exclusivamente en backend. Despachos reales siguen deshabilitados.

## Verificación Docker

Regresiones backend: 235 pruebas aprobadas, PostgreSQL de pruebas aislado,
`manage.py check` correcto y `makemigrations --check --dry-run` sin cambios.

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 -e TCC_SHIPPING_ENABLED=False backend sh -c 'python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test shipping ecommerce crmChat usuarios.test_account --noinput'
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npm run build -- --outDir /tmp/tcc-location-build'
```

Compilación correcta; persiste advertencia de tamaño de chunks, sin error.
Pruebas Playwright dentro de `docker-compose.qa.yml`, con
`shipping.e2e_server --tcc-e2e` en contenedor dedicado, PostgreSQL temporal,
TCC y pagos simulados. El flujo real de persistencia comprueba: login, dirección,
estimación automática, carrito, cantidades, ciudad, checkout, pago simulado
280.000 COP, webhook firmado repetido, una orden y un único despacho simulado.
La orden guarda 250.000 de productos, 30.000 de envío y 280.000 pagados.
También prueba crear/editar/previsualizar/activar/desactivar/duplicar/eliminar
plantillas contra PostgreSQL, sin mensajes a clientes.

Las pruebas de interfaz con APIs controladas cubren invitado, sesión, errores y
reintentos, registro y omisión de dirección, además de recotización del checkout,
manipulación de importes rechazada por backend y pantalla 1280/768/390.
Los logs privados quedan en `.artifacts/tcc-location-*.log`, fuera del repositorio.

## Límites operativos

- Los productos reales sin peso, dimensiones, valor declarado o paquetes siguen
  bloqueando la cotización/guía; el administrador ve «Información logística
  incompleta». No se inventan medidas ni se modifica el inventario real.
- Sigue pendiente confirmar con TCC la tarifa MSJ Cali–Bogotá rechazada en la
  validación anterior. Esta entrega no modifica las cuentas para eludirla.
- No hay contrato adicional de seguimiento API ni plazo garantizado: se conserva
  el enlace web oficial, sin inventar estados o tiempos.
- No se realizaron cobros, guías ni envíos reales; las pruebas de pago/transportista
  usan simulaciones explícitas. No constituyen certificación del servicio externo.
- Se preservan los cambios previos en `frontend_U/dist` y el archivo ajeno
  `verify_live_meta_handshakes.py`. No se ejecuta migración sobre datos de negocio.
