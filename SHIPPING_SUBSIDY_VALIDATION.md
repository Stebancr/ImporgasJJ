# Direcciones persistidas, tarifas TCC y envío gratis — validación en dev

Fecha: 21 de octubre de 2026. Trabajo y commits exclusivamente locales en `dev`.

## Estado Git y alcance

- Commit inicial: `48d781edc68947c8d540b6ad6053005908dac539`.
- Backend: `ec71e44a` — política de subsidio, contabilidad separada, migración,
  endpoints y pruebas.
- Frontend: `e4548d2f` — dirección persistida, promoción y pruebas de navegador.
- El commit de este informe cierra el trabajo; consultar `git rev-parse dev`
  para su hash final.
- `main` permaneció en `d61725ab7463cd1bebae5368d97ef3788580d09a`.
- No se hizo push, PR, merge, despliegue ni operación sobre producción.
- Cambios previos de `frontend_U/dist` y `verify_live_meta_handshakes.py`
  quedaron fuera de los commits y no se modificaron durante esta tarea.
- No se sobrescribieron `.env`, `.envdev` ni credenciales. Solo se añadió el
  nombre y valor comercial no secreto del umbral a `.env.example`.

## Causas y correcciones

1. El selector compartido admitía destinos genéricos incluso después del login;
   al no encontrar dirección predeterminada recuperaba la ciudad temporal del
   visitante. Ahora los autenticados resuelven únicamente una dirección propia:
   selección de sesión, predeterminada o disponible. La ubicación genérica queda
   reservada al visitante. Una carga fallida de direcciones no borra la selección
   previa ni dispara una cotización sin dirección.
2. La API de estimaciones admitía municipio aislado para ambos tipos de sesión.
   Ahora exige `address_id` al autenticado, verifica propiedad y obtiene el código
   geográfico del registro. No confía en la ciudad enviada junto con ese ID.
3. El único importe de envío se utilizaba tanto para TCC como para el cliente.
   Ahora la cotización conserva tarifa real, cobro, subsidio y política congelada.
   La orden y la intención conservan esos conceptos sin mezclar el subsidio con
   descuentos de productos. La revalidación consulta la tarifa real incluso si
   el cliente tiene envío gratis.
4. El checkout podía restaurar un formulario temporal sin dirección asociada.
   Ahora solo cotiza cuando hay una dirección guardada seleccionada. La edición
   se realiza mediante el formulario persistente integrado; el resto del resumen
   queda de solo lectura y no elimina la selección accidentalmente.

## Flujo final

- **Visitante:** departamento/municipio → estimación → ubicación genérica de
  sesión al navegar. No crea direcciones permanentes. El login conserva carrito
  y producto; la cuenta selecciona o crea su dirección antes de cotizar.
- **Autenticado sin direcciones:** tarjeta «Todavía no tienes una dirección de
  entrega» → botón principal con icono «Agregar nueva dirección» → formulario
  integrado → guardado → selección automática → cotización. No hay selector
  temporal ni modal abierto automáticamente.
- **Autenticado con direcciones:** selección persistida/predeterminada → resumen
  → cotización → cambiar a otra dirección o guardar una nueva → recotización.
  Crear una dirección secundaria no cambia la predeterminada sin solicitarlo.
- El formulario conserva datos tras error, ofrece campos dependientes de
  departamento/municipio, validaciones por campo y protección contra doble clic.
- **Checkout:** dirección persistida y carrito vigente → cotización definitiva
  → recotización backend antes del pago → importe firmado para Wompi → webhook
  oficial verificado → orden confirmada → encolamiento idempotente del despacho.
  Todas las pruebas de esta parte usan pago y guía simulados, no productivos.

## Fórmula y persistencia

```text
eligible = subtotal_productos - descuentos_productos
free = cotización válida y tarifa positiva y eligible >= FREE_SHIPPING_THRESHOLD
customer_shipping_charge = 0 si free; tarifa TCC en caso contrario
shipping_discount = carrier_shipping_cost - customer_shipping_charge
total = subtotal_productos + customer_shipping_charge + impuestos - descuentos_productos
```

Umbral configurado: **$2.000.000 COP**, inclusivo. Los precios vigentes ya son los
precios de venta. Los descuentos e impuestos adicionales siguen en cero porque
no existe un motor de cupones o impuestos adicionales; el navegador no los decide.
La función de política prueba también descuentos que reducen la base elegible.

`ShippingQuote.tcc_rate` permanece como tarifa real; `total` es el cobro al cliente.
`snapshot.shipping_policy` conserva ambos, subsidio, umbral y elegibilidad. El
umbral entra en la huella de caché y la orden conserva la dirección inmutable.

Campos de orden:

| Concepto | Campo |
|---|---|
| Tarifa real | `carrier_shipping_cost` |
| Cobro al cliente | `shipping_cost`; alias API `customer_shipping_charge` |
| Subsidio de transporte | `shipping_discount` |
| Promoción aplicada | `free_shipping_applied` |
| Umbral congelado | `free_shipping_threshold` |
| Cotización/fecha/cuenta/destino | Relación `Shipment.quote` y su snapshot |

El administrador muestra tarifa real, cobro, subsidio, indicador, total y los
datos existentes de guía/estado. Los campos también están disponibles en la API
de pedidos. No se inventó una exportación de reportes que antes no existiera.

## Endpoints y archivos principales

- `POST /api/shipping/estimate`: dirección propia obligatoria para autenticados;
  municipio temporal permitido al visitante.
- `POST /api/shipping/quote`: cotización definitiva del carrito existente.
- `GET /api/shipping/config`: incluye `free_shipping_threshold`, sin secretos.
- `POST /api/shipping/promotion`: progreso con precios de DB, sin llamada TCC;
  valida estructura, cantidades y hasta 100 líneas. No concede entrega gratis.
- Endpoints existentes de direcciones y órdenes conservan permisos e idempotencia.
- `BACKEND/shipping/policy.py`, `services.py`, `serializers.py`, `views.py`;
  modelos/serializers/views de ecommerce y `core/settings.py`.
- `ShippingCalculator`, `ProductShippingEstimate`, `ShippingProgress`,
  `useDeliveryLocation`, `useShippingConfig`, servicios HTTP, Home, carrito,
  checkout, pedidos administrativos y `ShipmentDetails`.

## Migración y respaldo

`ecommerce.0020_order_shipping_subsidy` añade cuatro columnas opcionales NULL.
No contiene `RunPython`, eliminación de tablas/columnas ni cambios de registros
históricos. No se reescribieron migraciones publicadas ni campos anteriores.

Se ejecutaron en Docker sobre PostgreSQL QA aislado:

```sh
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
python manage.py migrate --plan
python manage.py sqlmigrate ecommerce 0020
python manage.py migrate --noinput
python manage.py check
```

Resultado: sin cambios de modelo pendientes, grafo coherente, SQL únicamente
aditivo, migración y comprobaciones correctas. Después se aplicó la misma
migración al **desarrollo local**, con respaldo previo; no quedan migraciones
pendientes. No se aplicó nada en producción.

Respaldo local privado e ignorado por Git:
`.artifacts/dev-tcc-qa/dev-before-shipping-subsidy.dump` (668.029 bytes).
Validación: archivo no vacío y catálogo `pg_restore -l` inspeccionable de 621
líneas. No se ejecutó restauración sobre ninguna base existente. No se borraron
volúmenes ni archivos multimedia.

## Pruebas y evidencia

Todos los procesos y pruebas se ejecutaron dentro de Docker.

| Verificación | Resultado final |
|---|---|
| Backend: ecommerce, shipping, crmChat, transactional_mail, AppVisits, gestion, usuarios | **451 descubiertas/ejecutadas/aprobadas; 0 fallidas; 0 omitidas**, 66,139 s |
| Gateway WhatsApp | **38 aprobadas**, 7 archivos, configuración sintética |
| TypeScript | `tsc --noEmit` correcto |
| Vite producción | Compilación correcta en `/tmp`, sin tocar dist local |
| Docker backend/frontend | Dos imágenes construidas correctamente |
| Navegador — tres perfiles | Visitante, sin dirección, con varias direcciones; persistencia, error conservado, reintento, privacidad logout, default intacto |
| Navegador — subsidio | 1.999.999 / 2.000.000 / 2.100.000; Home, detalle, carrito, checkout y pago simulado |
| Navegador — flujo integral previo | Logística administrativa, cantidades, direcciones, Wompi simulado, guía única y CRUD de plantillas con PostgreSQL real aislado |
| Navegador — tarjetas/estados/registro/direcciones | Búsqueda, navegación, error/catálogo vacío, nueve estados de entrega, reintentos independientes, sin bucles ni promoción falsa |
| Navegador — plantillas/usuarios | Tres scripts de plantillas y uno de usuarios aprobados; formularios, errores, duplicados, permisos UI y responsive |
| WebSocket real QA | Nginx → ASGI → JWT subprotocol → Redis → ping/pong aprobado, sin mensajes a clientes |
| Responsive | 1280 / 768 / 390 px, sin scroll horizontal; tarjeta móvil inspeccionada visualmente |

**13 scripts de navegador distintos aprobados** entre las ejecuciones finales.
Evidencias privadas en `.artifacts/dev-tcc-qa/`; capturas de la tarjeta de entrega
en `subsidy-evidence/destination-card-{1280,768,390}.png`.

Pago simulado inclusivo verificado end-to-end:

```text
Productos:             2.000.000
Tarifa TCC simulada:       30.000
Cobro cliente envío:            0
Subsidio almacenado:       30.000
Wompi amountInCents: 200.000.000
Dos webhooks aprobados: una orden, una guía sintética y una llamada de despacho mock
```

Compra inferior al umbral también atravesó el flujo completo con pago simulado:
productos $250.000 + transporte $30.000 = $280.000. La prueba de límites valida
$1.999.999 + tarifa $30.000 = $2.029.999 en el backend.

## Consultas sandbox reales

Ver [documento técnico para TCC](docs/TCC_VALIDACION_COTIZACIONES.md), que incluye
request y respuesta sanitizados, códigos, pesos, cuentas y preguntas de soporte.
Se hicieron **12 cotizaciones**, desde Cali a seis ciudades: **10 aceptadas y
2 rechazadas**, todas HTTP 200. MSJ rechazó Bogotá y Medellín con resultado -1 y
ausencia de tarifa para esa ruta/cuenta. PQT aceptó las seis rutas. No se deduce
de esos rechazos falta de cobertura física ni token globalmente inválido.

## Servicios de desarrollo

Todos quedaron running; **0 reinicios automáticos**. Los reinicios manuales de
backend/workers/beat cargaron el código local. No se recrearon volúmenes.

| Servicio | Health check | Función validada | RAM aproximada |
|---|---|---|---:|
| backend | No definido | Config/catálogo/productos 200, permisos 401, migraciones | 114 MiB |
| frontend-ecommerce | No definido | Home y plantillas 200 con Host localhost; navegador | 309 MiB |
| postgres | Healthy | pg_isready y operaciones/pruebas DB | 72 MiB |
| redis | Healthy | PONG, broker y grupos WebSocket | 12 MiB |
| celery-worker | No definido | inspect ping/pong | 224 MiB |
| celery-chatbot | No definido | inspect ping/pong | 210 MiB |
| celery-beat | No definido | Proceso scheduler activo y Redis disponible | 142 MiB |
| whatsapp-gateway | Healthy | `/health` 200, `ok=true`, suite 38 | 149 MiB |
| ollama | Healthy | `/api/tags` 200; qwen:4b instalado | 112 MiB |
| nginx | No definido | nginx -t y proxy HTTP correctos | 3 MiB |

CPU: servicios generalmente <1% en la muestra; Vite alcanzó aproximadamente 48%
durante las comprobaciones y recompilaciones. No se enviaron consultas comerciales
a Ollama ni mensajes externos para probar salud.

## Logs e incidencias de validación

- Revisión sanitizada de los últimos cinco minutos de nueve servicios locales:
  **0 Traceback/CRITICAL, 0 duplicate key/connection refused/permission denied y
  0 respuestas HTTP 5xx** en esa ventana. No equivale a monitoreo indefinido.
- 400/401/404/422/503 de pruebas negativas corresponden a validaciones, permisos,
  producto incompleto o proveedor simulado, no fallos inesperados del flujo.
- Los Traceback de generación PDF y timeout Ollama en el log de tests son
  excepciones inyectadas por las pruebas negativas; la suite terminó en OK.
- Un WebSocket QA recibió 502 por una IP antigua de backend retenida por Nginx
  después del reinicio. Se recargó **solo el proxy de QA**, sin cambio versionado
  de Nginx; la repetición real de handshake/ping-pong pasó.
- El frontend rechazó inicialmente Host interno `nginx` con 403; con el Host
  correcto `localhost` respondió 200. No se desactivó esa protección.
- Los primeros ensayos de gateway carecían de variables sintéticas requeridas;
  con la configuración de test correcta pasaron sus 38 pruebas.
- Se adaptaron selectores de pruebas a las nuevas etiquetas y espacios de moneda
  COP, sin relajar las comprobaciones de importes o persistencia.

## Pendientes y límites reales

1. TCC debe aclarar/habilitar la tarifa MSJ Cali–Bogotá y Cali–Medellín en sandbox.
   No se marca ese requisito externo como resuelto.
2. Las respuestas probadas no proporcionan plazo estimado ni contrato de API de
   seguimiento/cancelación/webhook. Se mantiene el enlace oficial existente.
3. Producción sigue sin token y no fue activada. En desarrollo se comprobó
   `TCC_DISPATCH_ENABLED=False` y `TCC_PRODUCTION_APPROVED=False`.
4. Los pagos y remesas E2E fueron simulados; no certifican un cobro bancario o
   despacho productivo real. No se enviaron correos ni mensajes a clientes.
5. Los endpoints históricos de cotización definitiva conservan compatibilidad
   con clientes que envían dirección completa. El frontend actual exige guardarla
   antes de cotizar y el endpoint de estimación autenticada exige su ID propio.
6. No existe un nuevo motor de descuentos/impuestos ni exportación de reportes
   añadida artificialmente; la contabilidad nueva se consulta en pedidos y API.

## Reversión propuesta, no ejecutada

Revertir los commits locales mediante nuevos commits revisados, sin reset ni
reescritura. Mantener las columnas aditivas para no perder datos de promociones
nuevas; no ejecutar una reversión de esquema que las elimine. Si es necesario
detener cotizaciones, usar la bandera existente; no convertir la tarifa en cero.
La restauración de una base requeriría autorización explícita. Se conservaron
respaldo y evidencia. No se realizó ninguna restauración ni despliegue.
