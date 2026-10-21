# PR general dev → main, sin TCC ni cobro de envío

## Integración de Usuarios y Trabajadores

Rama de origen revisada: `codex/fix-usuarios-trabajadores`, commit local y remoto `88592f0c4d2e026e8da96519af9f564e7da65d03`.

- `cac808e0` se incorporó mediante cherry-pick como `1a850e03`: cuentas, permisos, estado, contraseña, filtros, interfaz y revocación de sesiones.
- Las correcciones generales de `88592f0c` se incorporaron como `540a3592`, excluyendo sus validaciones y pruebas de TCC.
- Conflictos resueltos: el consumer conserva el canal del cliente y las comprobaciones de revocación del CRM; productos conservan las validaciones actuales sin perfil logístico; las pruebas de visitas conservan el tratamiento seguro de streams.
- Se prueba expresamente que un cliente reciba sus propios eventos WebSocket, no acceda a conversaciones ajenas y pierda acceso tras inactivación o cambio de contraseña.
- El PR #8 original permanece abierto, sin fusionar. Su rama conserva una base anterior: no debe integrarse de nuevo sin revisar su diff. El PR #9 de TCC permanece intacto.

## Alcance incluido

Productos: editor transaccional, borradores, permisos, imágenes, principal, existencias y especificaciones, idempotencia, control de edición concurrente, validaciones y errores en el modal. Productos históricos y nuevos se guardan sin campos logísticos.

Direcciones: creación/edición/eliminación, propietario, predeterminada, reintentos sin duplicados, selectores locales separados y dependientes de departamento/ciudad o municipio, barrio, complemento e indicaciones. Se puede crear una dirección durante la compra sin perder el carrito. El checkout recupera el paso de pago al recargar con el mismo carrito. La orden conserva tanto una FK opcional a la dirección como sus datos y detalles congelados; eliminar la dirección pone la FK en NULL y conserva el histórico.

Usuarios/Trabajadores: filtros Todos/Activos/Inactivos, búsqueda/paginación, creación/edición, roles/permisos, estado, contraseñas con confirmación y validadores Django, revocación de sesiones, errores dentro del modal, prevención de solicitudes duplicadas, autoinactivación y pérdida del último administrador/superadministrador. No se eliminan usuarios. No se devuelve ni registra la contraseña; campos vacíos no la modifican.

CRM, chat y plantillas: filtros por canal, actualizaciones, prevención de duplicados, adjuntos protegidos, MIME/tamaño real, errores/reintentos, texto multilínea y formato seguro, variables y previews por canal. Se conserva la degradación de formato y la restricción de mensajería reactiva, sin mecanismos de pago de Meta.

Correos: compras y visitas, cola/reintentos controlados, idempotencia, PDFs, enlaces privados con vencimiento, configuración SMTP/Brevo por entorno y protección de documentos. Los correos y PDFs de compras nuevas tampoco afirman envío gratis ni muestran envío $0.

## Fórmula y pagos

```text
total_pagado = subtotal_productos + impuestos - descuentos
```

No existen tarifa fija, umbral gratuito, estimación geográfica, cotización ni cargo nuevo de transporte. `shipping_cost` es NULL en pedidos/intenciones nuevos y no se devuelve como cargo en la respuesta de creación de la intención Wompi. El widget recibe únicamente el importe firmado por el backend.

La UI indica: «El valor del envío no está incluido en esta compra. Las condiciones de entrega serán confirmadas posteriormente.» Se conservó `f5fdf28a` y se retiraron también el banner residual del carrito y las representaciones de envío gratuito en resúmenes.

Precios, impuestos, descuentos y total del navegador no se aceptan como fuente monetaria. No existe actualmente un motor de impuestos adicionales/cupones, por lo que se conserva su política autorizada de cero ajustes. La idempotencia valida usuario, artículos, importe y destino. Se conservan sin sobrescribir los importes de pedidos/intenciones históricos, incluida su comprobación contra pagos ya iniciados; esa compatibilidad no calcula tarifas ni se usa para crear compras nuevas.

## Exclusiones

`codex/dev-tcc` sigue en `749ccf56`, sin modificaciones. No hay aplicación `shipping`, cliente TCC, rutas, tareas, cotizaciones, guías, cuentas PQT/MSJ, perfiles logísticos, componentes ni migraciones exclusivos del proveedor en el árbol final de dev.

Las referencias restantes justificadas son documentación de exclusión, pruebas que comprueban ausencia, una compatibilidad condicional de direcciones históricas y las asignaciones **vacías** de tokens en el gateway autorizadas para impedir que herede secretos. No son credenciales ni variables requeridas para iniciar.

Los UUID y eventos internos de seguimiento de pedidos existentes se conservan; no son seguimiento de una transportadora. La biblioteca HTTP sigue siendo compartida por Meta/Wompi y no es una dependencia exclusiva de TCC.

## Migraciones del diff respecto de origin/main

1. `ecommerce.0014_useraddress_complement_and_more`: campos generales de direcciones; no crea códigos del proveedor en instalaciones nuevas.
2. `ecommerce.0015_order_discounts_order_paid_total_order_taxes_and_more`: contabilidad general.
3. `ecommerce.0016_producteditoroperation`: idempotencia del editor.
4. `ecommerce.0017_preserve_legacy_address_writes`: permite escribir direcciones si una base antigua conserva una columna extra; solo establece un default condicional, sin eliminar columnas/datos.
5. `ecommerce.0018_delivery_without_shipping`: FK/snapshot de dirección y envío nullable en pedidos/intenciones. No actualiza importes históricos.
6. `transactional_mail.0001_initial`: eventos/documentos de correo.
7. `transactional_mail.0002_delivery_max_attempts_alter_delivery_state`: reintentos/estado.

Usuarios usa `password_version`, ya existente en main. CRM y plantillas reutilizan su esquema compatible; no se crearon migraciones innecesarias.

Se ejecutaron dentro de Docker `makemigrations --check --dry-run`, `showmigrations`, `migrate --plan` y `migrate`. Se reprodujo la estructura de `origin/main` (`5b2a6bca`) con datos sintéticos en `test_general_pr_upgrade_20261019`: tras todas las migraciones permanecieron el producto, descripción, precio, imagen principal, stock, rol, contraseña, dirección y montos históricos. Un pedido nuevo conserva dirección y envío NULL. La base de producción no se consultó ni modificó en esta tarea.

Antes de migrar la base local se generó `.artifacts/general-pr/dev-before-migrate.dump`, inspeccionado con `pg_restore --list`; está excluido de Git. En la base de desarrollo solo quedaba pendiente 0018 y se aplicó correctamente.

## Resultados de pruebas

| Verificación Docker | Resultado |
|---|---|
| `python manage.py test --noinput`, PostgreSQL aislado | **382 aprobadas**, suite completa. |
| Gateway WhatsApp | **38 aprobadas**. |
| Usuarios en Playwright | Inactivos, edición, errores por campo, borrador conservado, guardado único, confirmación de contraseña y responsive aprobados. |
| Productos contra PostgreSQL sintético | Crear/editar, permisos, validación, imágenes/principal, fallo 503, reintento, persistencia y responsive aprobados. |
| Checkout contra PostgreSQL sintético | Dirección nueva dentro de checkout, carrito conservado, paso de pago recuperado al recargar, total $125.000, widget simulado con 12.500.000 centavos y ningún cargo de envío aprobados. |
| Adjuntos y plantillas en navegador | Texto/archivo, errores/reintentos, recarga, permisos, formato/variables/previews y responsive aprobados. |
| TypeScript y Vite | Aprobados; advertencia no bloqueante de chunks grandes. |
| Imágenes backend y frontend | Construidas localmente. |
| Arranque sin variables TCC | Django inicia y no registra aplicación/rutas/tareas TCC. Las pruebas de navegador no detectan requests al proveedor. |
| Migraciones desde estructura main | Compatibilidad y conservación verificadas. |

Comandos principales:

```powershell
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 backend python manage.py test --noinput
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py showmigrations
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py migrate --plan
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py migrate --noinput
docker compose -f docker-compose.dev.yml --profile test run --rm --no-deps -T whatsapp-gateway-test
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npx vite build --outDir /tmp/general-pr-verified'
```

Playwright se ejecutó en `docker-compose.qa.yml`; fixtures en PostgreSQL independiente y archivos temporales. Evidencias privadas: `.artifacts/general-pr/`.

## Publicación y límites

El PR dev → main ya existía como #7; se actualizará ese mismo PR, sin crear duplicados ni fusionarlo. La publicación autorizada afecta únicamente dev. No hay workflows de despliegue versionados en este repositorio. Se verificó que el PR no tiene fusión automática activada.

No se publican .env privados, credenciales, medios, bases, sesiones ni compilados. Los cambios antiguos de `frontend_U/dist` y el archivo local vacío `verify_live_meta_handshakes.py` se conservan sin incluirlos en los commits.

No se realizaron pagos, correos ni mensajes reales, ni pruebas contra Meta/TCC productivos. Las llamadas de proveedores están simuladas; persistencia, migraciones, permisos y WebSockets se probaron realmente en Docker. Sin análisis antivirus instalado, no se afirma que se hayan escaneado los archivos. No hubo despliegue ni fusión; la entrega no activa transporte y sus condiciones requieren confirmación posterior.
