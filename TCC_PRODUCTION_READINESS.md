# Preparación y ensayo de despliegue TCC — 19 de octubre de 2026

## Decisión de despliegue

**NO se desplegó ni se activó TCC.** Las condiciones de aprobación del usuario todavía no se cumplen:

- Producción y `main`: `5b2a6bca9fef8910487e7f1b5f09459ef4be13aa` (PR #6).
- PR #7, `dev` → `main`, `e46de09cc7a5572f0d1f6c411cf6dd8226d54dc5`: abierto, sin aprobaciones registradas.
- PR #8, `codex/fix-usuarios-trabajadores` → `dev`, `88592f0c4d2e026e8da96519af9f564e7da65d03`: abierto, sin aprobaciones registradas.
- Esta preparación usa `codex/tcc-safe-production-rollout`, basada en el SHA de #8; necesita su propia revisión. No constituye una versión aprobada para desplegar.
- No se incorporaron los numerosos cambios sin commit de la copia original local de `dev`.

Commits pendientes respecto de producción: `2970de14` (filtros CRM), `1a757490` (TCC inicial), `e46de09c` (cotización y checkout), `cac808e0` (Usuarios), `88592f0c` (regresiones), más la preparación de esta rama. No se sustituyó ninguna dependencia por `main` ni se fusionó ningún PR.

## Auditoría de producción, solo lectura

Consultas mediante el backend Docker, antes de modificar datos o migraciones:

| Concepto | Conteo |
| --- | ---: |
| Productos totales | 23 |
| Activos / inactivos | 23 / 0 |
| Productos con imágenes | 23 |
| Productos referenciados por pedidos actuales | 0 |
| Variantes | 0; no existen tablas de variantes en el esquema |
| Productos sin peso | 23 |
| Sin alto / ancho / largo | 23 / 23 / 23 |
| Sin cantidad de paquetes definida | 23 |
| Sin valor declarado definido | 23 |
| Sin códigos logísticos definidos | 23 |
| Listos para cotización TCC | 0 |
| Información logística incompleta | 23 |

La tabla `shipping_productshippingprofile` aún no existe. Los conteos logísticos expresan ausencia de configuración; no se interpretaron valores ausentes como cero ni como un paquete. Las migraciones crean una tabla independiente, sin crear perfiles automáticamente para productos existentes. La API representa un perfil ausente como `null` y expone el estado derivado y los campos faltantes.

## Respaldo verificado

Ubicación privada en el servidor: `/root/backups/imporgas-pre-tcc-20261019/`, creada con `umask 077`.

- `postgres.dump`: aproximadamente 856 KB, formato custom PostgreSQL.
- `media.tar.gz`: aproximadamente 367 MB.
- `configuration.tar.gz`: aproximadamente 8 KB; contiene configuración privada y no debe publicarse.
- `commit.txt`, `containers.txt`, `image-ids.txt`, `restore-list.txt`, `restored-product-count.txt`.

Verificación realizada: archivos no vacíos; `pg_restore --list`; lectura del índice de ambos tar; SHA-256 de los tres respaldos; restauración completa con `--exit-on-error --no-owner --no-privileges` en un contenedor PostgreSQL aislado, sin red y con almacenamiento temporal en memoria. La tabla real `products` restaurada contiene 23 productos. Ese contenedor temporal se cerró después de verificarlo. No se restauró sobre la base productiva ni se borraron volúmenes.

Espacio disponible antes del respaldo: aproximadamente 72 GB. Antes del despliegue efectivo debe repetirse el respaldo para incluir operaciones posteriores; no usar este respaldo para sobrescribir compras o registros nuevos sin autorización explícita.

## Compatibilidad y correcciones preparadas

- Producto histórico: continúa visible y editable; no se crea logística por abrir o guardar el formulario. El frontend omite `shipping_profile` cuando no se modificó. Los números vacíos permanecen `null`.
- La edición manda únicamente atributos modificados. El precio y los stocks sin cambios no se vuelven a escribir, evitando sobrescribir cambios concurrentes al editar una descripción.
- Filtro de administrador: `shipping_status=incomplete|ready|not_required`. La API conserva sus campos previos y agrega `shipping_status` y `shipping_missing_fields`.
- Estados derivados: `ready` (Listo para cotizar), `incomplete` (Información de envío incompleta), `not_required` (No requiere envío). No existe cotización manual de envíos implementada: no se simula esa funcionalidad.
- La preparación para cotizar exige valores positivos, entre 1 y 100 paquetes y código de empaque admitido por el adaptador. Tener un perfil no basta. El envío mixto con un producto incompleto se rechaza antes de cotizar.
- Configuración incompleta, fuente de tarifa ausente o bandera desactivada nunca se convierten en un envío gratis en el modo protegido de producción. Se muestra “Envío pendiente por confirmar” y se bloquea el pago antes de crear orden o intención Wompi.
- Esta restricción es deliberada: **los 23 productos actuales requieren datos logísticos reales antes de permitir compra automática con TCC**. Mientras no haya cotización válida ni un flujo manual aprobado, no se puede prometer una tarifa ni cobrarla. No se alteró el checkout actualmente desplegado.
- No se modifican automáticamente precio, inventario, imágenes, descripción, disponibilidad ni perfiles históricos. No hay migraciones de relleno masivo de productos.

## Migraciones revisadas y ensayadas

Pendientes de despliegue, todas ejecutadas únicamente en el ensayo:

1. `ecommerce.0014_useraddress_complement_and_more`: datos opcionales adicionales de dirección.
2. `ecommerce.0015_order_discounts_order_paid_total_order_taxes_and_more`: impuestos/descuentos adicionales en cero según la política vigente y total pagado opcional; no cambia los totales históricos.
3. `shipping.0001_initial`: perfiles independientes, cotizaciones y registros de despachos/eventos. Peso/dimensiones/valor declarado permiten `NULL`. No crea perfiles para los productos antiguos.
4. `shipping.0002_shippingquote_provider_summary`: metadatos de cotización.
5. **Nueva** `ecommerce.0016_rollback_safe_tcc_defaults`: mantiene defaults en PostgreSQL para las columnas nuevas de direcciones e impuestos/descuentos. Permite que el código anterior inserte filas sin conocer esas columnas. No inventa datos logísticos ni rellena productos.

Riesgo corregido en el ensayo: los defaults de Python de las migraciones anteriores no bastaban para que la versión antigua insertara direcciones, órdenes o intenciones de pago sobre el esquema actualizado. No se editaron las migraciones pendientes originales; se añadió una migración compatible. El comando `migrate_tcc_release` envuelve todo el plan en una transacción PostgreSQL y rechaza migraciones no atómicas/reversiones. Así la aplicación anterior no ve una fase intermedia con columnas nuevas sin sus defaults. El arranque normal se realiza después de completar este comando, no simultáneamente con otra ejecución de migraciones.

## Ensayos y pruebas

- Suite completa final de la propuesta: **381 pruebas aprobadas**, PostgreSQL temporal, dentro de Docker. Incluye autenticación/Usuarios, CRM, chat, plantillas, integraciones simuladas, pedidos/Wompi, visitas/PDFs, recuperación de correo y TCC. No se enviaron mensajes o pagos reales.
- Siete pruebas nuevas cubren productos sin perfil, edición sin rellenar logística, filtros, código de empaque inválido, checkout bloqueado sin tarifa confirmada, activación solo para administradores, preflight sin secretos y migración/rollback. Se comprueba que un fallo dentro de la migración transaccional no deje cambios parciales.
- Ensayo adicional con el código **exacto de producción** (`origin/main`, SHA `5b2a6bca`), base local independiente `test_tcc_deploy_20261019` y multimedia local sintética: se crearon 23 productos, 23 imágenes y un pedido histórico. Se aplicaron las cinco migraciones con el código propuesto. Se compararon precios, inventario, estado y descripciones; se verificaron los archivos y el pedido. La API permite editar una descripción sin crear perfil logístico.
- Reversión ensayada: se volvió a ejecutar el código real anterior contra el esquema actualizado, conservando las migraciones. Se crearon correctamente dirección, orden e intención de pago desde ese código. Su comando de arranque `migrate --noinput` también termina sin revertir el esquema. No se restauró la base del ensayo para hacer pasar esta prueba.
- TypeScript y Vite build aprobados. Persiste la advertencia de tamaño de bundles.
- Playwright Docker aprobado en 1280/768/390: edición de un producto sin perfil, envío de descripción sin precio/logística no modificados, cero solicitudes de modificación de stock y mensaje público de envío pendiente.
- No se realizó cotización real de producción: faltan credenciales de producción y el código sigue pendiente de revisión. Las cotizaciones y despachos de las pruebas están interceptados. No se generó ningún despacho real.

Evidencias locales privadas: `.artifacts/tcc-release-final-tests.log`, `tcc-atomic-rehearsal-final.log`, `tcc-live-create.log`, `tcc-live-upgrade.log`, `tcc-live-verify.log`, `tcc-live-rollback.log`, `tcc-old-startup-migrate.log`, `tcc-legacy-final-ui.log`, `tcc-rollout-final-build.log`.

## Configuración de activación

`TCC_SHIPPING_ENABLED=False`, `TCC_ADMIN_ONLY=True`, `TCC_REQUIRE_CONFIRMED_SHIPPING=True`, `TCC_DISPATCH_ENABLED=False`, `TCC_PRODUCTION_APPROVED=False` son la preparación inicial del ejemplo de producción. No se escribieron estos valores en el servidor.

En el entorno de los contenedores productivos no están presentes las variables TCC auditadas. Deben configurarse mediante el archivo privado del servidor y el mecanismo seguro existente; no compartir valores por chat ni Git:

`TCC_API_ENVIRONMENT`, `TCC_PRODUCTION_BASE_URL`, `TCC_PRODUCTION_API_TOKEN`, `TCC_PRODUCTION_APPROVED`, `TCC_PQT_ACCOUNT`, `TCC_MSJ_ACCOUNT`, `TCC_ORIGIN_CITY_CODE`, `TCC_SENDER_NAME`, `TCC_SENDER_COMPANY`, `TCC_SENDER_DOCUMENT_TYPE`, `TCC_SENDER_DOCUMENT`, `TCC_SENDER_ADDRESS`, `TCC_SENDER_PHONE`, `TCC_SENDER_EMAIL`, además de las banderas anteriores. No se asume que las cuentas de los ejemplos estén autorizadas para producción.

Comprobación de solo lectura una vez desplegado el código aprobado:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T backend python manage.py tcc_preflight --production --strict
```

Informa conteos y nombres de variables faltantes/incorrectas sin imprimir sus valores. Rechaza entorno/URL de desarrollo y coincidencia del token productivo con el de desarrollo. El adaptador usa conexión de 5 s, cotización de 12 s y despacho de 45 s; no hay reintentos automáticos de cotización. Los reintentos de despacho incierto continúan bloqueados.

Activar primero `TCC_SHIPPING_ENABLED=True` manteniendo `TCC_ADMIN_ONLY=True` y `TCC_DISPATCH_ENABLED=False`, después de completar logística real y validar preflight. Esto habilita cotizaciones únicamente a roles administrativos 1/4; usuarios públicos no pueden saltarse la restricción por API. Solo después de una cotización productiva controlada y revisión de totales puede cambiarse `TCC_ADMIN_ONLY=False`. Los despachos reales requieren una autorización independiente; no se activan con la cotización.

## Estado de producción observado

- Repositorio limpio en `main`, SHA `5b2a6bca`; contenedores backend, frontend, PostgreSQL, Redis, workers, gateway, media y Nginx saludables. Beat y Ollama en ejecución; no se reconstruyó ni reinició ninguno.
- Los hashes de los archivos críticos del backend (modelos, vistas y serializadores de e-commerce, ambos settings, tareas CRM y vistas de Usuarios) coinciden con los blobs de ese commit; no se tomó únicamente el HEAD del checkout como prueba del código en ejecución.
- `/`, `/admin/usuarios`, `/api/products`: HTTP 200.
- HTTP raíz, HTTPS raíz y HTTP www: redirección 301 al dominio canónico, conservando `/producto/7?deployment_audit=1`.
- Dominio canónico: `https://www.imporgasjj.com`. TLS verificado; certificado cubre raíz y www, vence el 20 de diciembre de 2026. Coolify/Traefik sigue gestionándolo.
- `nginx -t`: correcto. No se instaló otro proxy ni sistema de certificados.
- Logs agregados de los 30 minutos auditados: backend 4 líneas, worker 240 y Nginx 42; cero tracebacks y cero respuestas 5xx detectadas por el contador. No se mostraron líneas completas ni datos de clientes.
- Colas Redis `celery` y `chatbot`: cero entradas en la muestra; dos workers responden `pong`. CPU de los servicios muestreados inferior al 1%; memoria aproximada: backend 173 MiB, PostgreSQL 66 MiB, Redis 17 MiB, worker 211 MiB, chatbot worker 217 MiB y Ollama 150 MiB. Es una muestra previa al despliegue, no una prueba de carga.

No se afirma que pagos, mensajes externos o correos productivos se hayan enviado: solo se verificaron pruebas aisladas y consultas de lectura en producción.

## Puertas de despliegue y procedimiento

1. Revisar/aprobar/fusionar las dependencias y esta preparación; verificar que `main` contenga el SHA aprobado final. Resolver las bases de los PR apilados según se fusionen. No desplegar desde estas ramas pendientes.
2. Registrar nuevamente SHA y estado limpio del servidor. Revisar todos los commits y la lista de migraciones, repetir pruebas sobre ese SHA final y crear un respaldo nuevo verificable.
3. Conservar los IDs de imágenes actuales y etiquetas de rollback antes de construir; no purgar imágenes ni volúmenes. Mantener la configuración previa en respaldo privado.
4. Actualizar el checkout solo por avance rápido al `main` aprobado. Configurar el entorno privado sin habilitar despachos ni cotizaciones públicas.
5. Usar primero `docker-compose.prodData.yml` y después `docker-compose.prod.yml`; no cambiar nombres/redes/volúmenes existentes ni cargar el dump inicial sobre una base existente. No ejecutar scripts de importación de PostgreSQL en este despliegue.
6. Construir únicamente backend, frontend y procesos Python que comparten código; revisar `migrate --plan` con la imagen nueva. Ejecutar `docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm --no-deps backend python manage.py migrate_tcc_release` antes de arrancar la nueva aplicación. Las migraciones se aplican dentro del contenedor y en una sola transacción PostgreSQL. Actualizar workers/beat tras confirmar el esquema. Gateway y proxy solo requieren reinicio si el diff aprobado los afecta.
7. Repetir pruebas de humo de catálogo, producto histórico, edición, imágenes, usuarios, carrito, checkout protegido, PDFs, WebSockets, workers, media y TLS. Comparar conteos y campos históricos con el inventario previo.
8. Ejecutar preflight, completar productos controlados con medidas reales y revisar la cotización TCC solo para administradores. No generar despachos reales. Activar públicamente únicamente tras validar importes y el entorno productivo.
9. Monitorizar 5xx, `shipping_pending`, fallos de cotización/credenciales, totales de pago, reinicios, colas y recursos, sin guardar respuestas sensibles. No confundir el bloqueo intencional por logística incompleta con una caída general del checkout.

## Reversión y condiciones objetivas

Responsable operativo: administrador autorizado del servidor; ejecución acompañada por el agente solo dentro del alcance autorizado.

Detener activación o revertir ante discrepancias de productos/imágenes/inventario, totales incorrectos, 5xx generalizados, fallo de migración o servicios que no recuperen salud. Una tarifa incorrecta exige detener cobros/cotización inmediatamente.

1. Desactivar cotización TCC y mantener desactivados los despachos. Mantener la exigencia de confirmación para no convertir una falla en envío gratis.
2. Si el problema persiste en la aplicación, ejecutar las imágenes anteriores registradas en `image-ids.txt`, con su configuración privada anterior y los mismos volúmenes persistentes. No usar `git reset --hard`, no borrar volúmenes ni revertir las migraciones: el esquema aditivo y los defaults permiten el código previo, como se comprobó en el ensayo.
3. Volver a comprobar salud, catálogo, media, lectura de pedidos y escritura de datos con la versión anterior. Conservar logs y el SHA fallido.
4. Restaurar una base productiva solo si es necesario por corrupción y con autorización explícita adicional. El rollback de aplicación ensayado no requiere esa restauración.

El despliegue permanece pendiente hasta que las puertas anteriores se cumplan. Esta preparación no sustituye una aprobación de los PR ni de la activación del proveedor.
