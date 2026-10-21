> Documento histórico recuperado. Para el estado actual, configuración y pruebas de esta rama consulta TCC_RECOVERY_VALIDATION.md.

# Transporte TCC

## Alcance y contratos comprobados

Fuentes entregadas: `OneDrive_1_14-10-2026`, manuales PDF de configuración,
creación/consulta y WooCommerce, y código de integración `tcc-shipping-v2.5.1`.
Se revisaron también los paquetes anteriores. No se ejecuta ni instala PHP.
El catálogo público de 1.343 municipios/códigos proviene de `geo/cities.php`;
`shipping/cities.json` conserva códigos de ocho dígitos, con ceros iniciales.

| Operación | Contrato suministrado |
|---|---|
| Cotizar | POST `/api/clientes/tarifas/v5/consultarliquidacion` |
| Crear despacho | POST `/api/clientes/remesas/grabardespacho8` |
| Autenticación | Encabezado `AccessToken`, JSON; sin Bearer |
| Desarrollo | `https://testsomos.tcc.com.co` |
| Producción | `https://somos.tcc.com.co`, bloqueado salvo autorización/configuración separada |
| Rastrear en web | `https://www.tcc.com.co/rastreo?tipo=RE&documento=<guía>` |

No hay contrato confirmado de consulta remota de estados, cancelación, webhook,
límites de frecuencia, SLA de entrega ni garantía de idempotencia del proveedor.
El ZIP antiguo `ConsultarDespachos` consulta órdenes locales de WordPress: no
constituye una API de seguimiento TCC. Por instrucción del usuario, estas funciones
no se integran todavía. No hay estados de transporte ficticios ni tarea diaria de
seguimiento. `/shipping/orders/<id>/sync` devuelve 409 explicando la limitación.

## Empaque, medidas y cuentas

- Peso en kg, dimensiones en cm. Decimales positivos. Vacío se conserva como null.
- Cada unidad vendida utiliza N paquetes uniformes, con medidas y **valor declarado
  por paquete**. Las cajas se envían separadas; nunca se suman sus dimensiones.
- Peso volumétrico por paquete: largo × ancho × alto × 0,0004; dos decimales,
  conforme a la implementación suministrada. Se suman pesos por cantidad/paquete.
- PQT código 1, cuenta 1485100 si peso real total o volumétrico total supera 5 kg.
  En otro caso MSJ código 2, cuenta 5625200. Exactamente 5 kg usa MSJ según el
  condicional del plugin entregado. Confirmar cualquier cambio de convenio con TCC.
- `billable_kg` es el máximo calculado entre peso real, volumétrico y mínimo global
  de 1 kg del ejemplo. No se aplica un mínimo ficticio de 1 kg por caja al payload:
  se envían pesos/medidas individuales y se cobra **la tarifa devuelta por TCC**.
  Este dato calculado no pretende reemplazar la liquidación del transportador.
- Frágil es una indicación operativa interna; no se inventa un atributo TCC.
- Límite interno de seguridad: 100 paquetes por checkout. No es un límite oficial.
- El perfil de transporte es adicional: no rellena ni modifica productos existentes.
  Para publicar/editar un físico con perfil o TCC activo se requieren los datos;
  cotizar bloquea cualquier producto físico incompleto. No se despublican históricos.

## Configuración privada y origen

Desarrollo: backend y Celery cargan `.envdev` mediante Compose. `.env` solamente
sirve para interpolación de Compose; poner allí una variable no la añade por sí
solo al backend. Producción carga el archivo privado indicado por `PROD_ENV_FILE`.
Ver ejemplos versionados `.env.example` y `.env.prod.example` sin credenciales.
No registrar configuración resuelta de Compose: puede mostrar todos los secretos.

`TCC_API_TOKEN` es exclusivo del lado servidor y desarrollo. Se eliminan espacios
exteriores antes de formar el encabezado. Rotar la credencial compartida antes de
habilitar producción. Producción exige `TCC_PRODUCTION_API_TOKEN` separado y
`TCC_PRODUCTION_APPROVED=True`; un token de desarrollo no se utiliza como respaldo.
Ninguna variable TCC se incorpora a `VITE_*` o al frontend.
Los servicios gateway de Node anulan explícitamente ambos tokens TCC heredables
del archivo privado compartido: las credenciales quedan en Django/Celery.
`TCC_DEVELOPMENT_BASE_URL` y `TCC_PRODUCTION_BASE_URL` son configurables, pero se
validan contra los hosts HTTPS oficiales del entorno para evitar fugas de tokens.

`TCC_SHIPPING_ENABLED=False` mantiene el checkout anterior. En producción no
activarlo hasta completar perfiles de productos y confirmar tarifas/cuentas. En
el entorno local de desarrollo se activó para mostrar y verificar el cotizador;
los productos incompletos bloquean la cotización con un error explícito. Las pantallas de
administración permiten completar los perfiles sin habilitar TCC para compradores.
`TCC_DISPATCH_ENABLED=False` permite consultar tarifas sin crear remesas. No se
ha autorizado activar despachos reales ni producción durante esta implementación.

El remitente es la empresa y la sede de salida, NO el comprador. Origen confirmado
por el usuario: **SEDE CALI SUR**, código TCC **76001000**, dirección
**Cll 10 # 65a-75 local 809**, teléfono **3160188422**. Se configuró en el archivo
privado local sin alterar registros de sedes existentes.

`TCC_SENDER_NAME`, `TCC_SENDER_COMPANY`, `TCC_SENDER_DOCUMENT_TYPE` (CC/NIT),
`TCC_SENDER_DOCUMENT`, `TCC_SENDER_ADDRESS`, `TCC_SENDER_PHONE` corresponden al
remitente de la empresa. Correo opcional. Razón social **ImporGas JJ S.A.S.** y
documento NIT configurados en `.envdev` según los datos suministrados por el
usuario. Se conserva el documento proporcionado, sin inventar reglas de dígito
de verificación no documentadas por TCC ni utilizar la cédula del comprador. Con creación
de despachos habilitada se valida el remitente completo antes de cotizar/pagar.
Para cotización de desarrollo con despachos apagados basta el código de origen.

El destinatario se toma de una dirección propia guardada o del checkout. Se piden
nombre, teléfono, correo, dirección y municipio del catálogo; complemento, barrio,
indicaciones y código postal son opcionales. El contrato suministrado permite
documento del destinatario vacío. La orden/cotización conservan una copia histórica.
Editar posteriormente la dirección del usuario no cambia esa copia.

## Flujo y recuperación

1. Carrito autenticado → dirección/catálogo → cotización backend con caché 600 s.
2. Resumen separa tarifa TCC y productos. Desde la restauración directa en dev no se aplican recargos; las columnas históricas se conservan para lectura.
3. Antes del pago se verifican dueño, expiración, productos, cantidades, precios,
   revisión de empaque, dirección, origen, entorno y tarifa TCC actual.
   Si cambió la tarifa se exige recotizar; `force=true` evita conservar una tarifa
   anterior hasta su expiración. No se acepta un costo decidido por el frontend.
4. La intención Wompi TCC crea orden local pendiente y copia de ítems, sin descontar
   inventario ni crear remesa. El flujo no TCC conserva su comportamiento previo.
5. Solo evento/consulta Wompi validada, APPROVED, importe/moneda/referencia correctos,
   marca pago y descuenta inventario una vez. No basta lo enviado por el frontend.
6. Despacho durable pendiente → Celery reclama fila con bloqueo de PostgreSQL →
   TCC → guarda guía única, recogida, enlaces seguros de documentos e historial.
   Referencia enviada a TCC: número de orden. UUID de idempotencia **local**, sin
   inventar un encabezado remoto que no aparezca en el contrato.
7. Dos workers/webhooks simultáneos no duplican la remesa. Worker perdido durante
   HTTP, timeout de lectura o 5xx dejan `uncertain`, sin repetición automática.
   Los errores conocidos previos a conexión se reintentan de forma acotada por
   Beat cada cinco minutos. Redis caído no elimina la orden pagada pendiente.
8. Administradores/superadministradores pueden reintentar errores confirmados;
   una operación incierta exige verificación humana con TCC y no tiene botón de
   reenvío. La UI no permite marcar entregado un TCC sin seguimiento confirmado.
   Un pago tardío no reabre una orden TCC cancelada localmente ni crea su despacho;
   queda registrado para revisión del asesor. No implementa reembolsos ni una
   cancelación remota de TCC, cuyo contrato sigue pendiente.

Los documentos se conservan como enlaces del proveedor y solo se muestran al
administrador. Se aceptan HTTPS/443 y hosts oficiales explícitos, sin descargas
servidor ni redirecciones automáticas. Clientes ven guía, historial local y enlace
oficial de rastreo. No se registra el cuerpo bruto del proveedor (puede repetir
datos privados); los logs solo incluyen operación, IDs locales y códigos seguros.

## Comprobaciones realizadas el 15-10-2026

La segunda entrega añade el cotizador público de producto, cotización del carrito,
traslado del destino al checkout y desglose contable. Informe vigente con pruebas,
ejemplos y limitaciones: **[TCC_COMPLETION_VALIDATION.md](TCC_COMPLETION_VALIDATION.md)**.
Las cifras de la primera ronda siguientes se conservan como antecedente.

- 225 pruebas backend en PostgreSQL de prueba: shipping, ecommerce, crmChat y
  usuarios.test_account. HTTP TCC/Wompi simulado; ninguna remesa real.
- Dos workers concurrentes con PostgreSQL: un solo POST de despacho simulado.
- Pesos 2 / 5 / 5,001 kg y volumétrico 8 kg; varios productos y paquetes.
- Direcciones ajenas/incompletas, caché, cambios de empaque, expiración/tarifa,
  ausencia de recargos/importe firmado, estados no aprobados, webhook duplicado, permisos,
  indisponibilidad, timeout incierto, recuperación y bloqueo de producción.
- TypeScript, compilación Vite y pruebas existentes del cliente Wompi en Docker.
- Playwright con APIs interceptadas: dirección guardada, cambio de ciudad,
  error bloquea pago, recotización forzada, importe firmado backend y responsive
  1280/768/390 sin desbordamiento horizontal en checkout/detalle; campos de producto
  dentro del modal, guardado y recarga, detalle administrativo/reintento/documento.
  No son pagos reales.
- Consulta **real de desarrollo**, sin datos de cliente y sin escrituras: Cali
  76001000 → Bogotá 11001000, PQT 6 kg, tarifa **44.700 COP**.
- MSJ 2 kg misma ruta: código proveedor **-1**, respuesta identifica
  **«No existe tarifa para la ruta solicitada»**. Confirmar con TCC tarifas de la
  cuenta 5625200 para esa ruta/ambiente. No cambiarla a otra cuenta arbitrariamente.
- Dos migraciones locales aditivas aplicadas: ecommerce.0014 y shipping.0001.
  Hashes de tablas de negocio preexistentes sin cambios. Django agregó 4 tipos de
  contenido y 16 permisos esperados, además de sus registros de migración.

Respaldo local privado: `.artifacts/tcc-before-20261015.dump`, formato custom
PostgreSQL, lista de restauración verificada. SHA-256:
`43b4fc99068e9261efa94c4c02644b217706c30fc271dded2c8f21051e829c31`.
No subir este respaldo ni `.artifacts`, archivos privados o sesiones al repositorio.

### Comandos de verificación (siempre dentro de Docker)

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 backend python manage.py test shipping ecommerce crmChat usuarios.test_account --noinput
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py check
docker compose -f docker-compose.dev.yml exec -T backend python manage.py migrate --plan
docker compose -f docker-compose.dev.yml run --rm --no-deps -T frontend-ecommerce sh -c 'npm ci --no-audit --no-fund && npx tsc --noEmit && node --test tests/wompiCheckout.test.mjs && npx vite build --outDir /tmp/tcc-build'
docker compose -f docker-compose.qa.yml run --rm --no-deps -T chat-ui-test sh -c 'npm install --no-audit --no-fund --prefix /tmp/crm-ui playwright@1.58.2 && node /tests/tcc-checkout.cjs'
```

### Activación posterior y rollback

No se despliega ni fusiona main en esta tarea. Antes de activar producción: validar
la identidad del remitente con TCC, rutas MSJ, todos los perfiles físicos, credencial apropiada,
tarifas y pruebas autorizadas de extremo a extremo. El checkout mantiene su envío
anterior mientras `TCC_SHIPPING_ENABLED=False`. Desarrollo quedó con cotización
habilitada y despachos apagados; la guía se verificó únicamente con mocks y una
base PostgreSQL temporal independiente.

Producción necesita su respaldo verificable y revisión de migraciones antes de
aplicar las dos migraciones, reconstruir backend/Celery/frontend y habilitar flags.
No usar makemigrations ni flush en producción. Si se requiere rollback, apagar los
flags TCC y volver a la imagen/revisión anterior conservando tablas y datos nuevos.
No revertir migraciones que borren shipping ni restaurar el dump sobre una base
activa con ventas posteriores; esa restauración requiere revisión/autorización.

## Registro pendiente para cuando TCC entregue documentación

- Contrato autenticado de consulta de guía/estado, códigos y transiciones.
- Límites y periodicidad permitida para consultas, tarea diaria solo entonces.
- Webhook: firma, reintentos, deduplicación y validación de remitente.
- Cancelación y conciliación de operación incierta; confirmar garantía remota de
  idempotencia antes de permitir reenvío tras un timeout.
- Estados reales de recogida/tránsito/entrega/novedad/devolución/cancelación y fechas.
- Consulta manual de estado desde CRM y mapeo compatible con órdenes históricas.

Estos puntos están documentados, **no implementados**, por instrucción expresa.
