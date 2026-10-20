# Separación local de TCC — 19 de octubre de 2026

## Referencias y alcance

| Referencia | Commit | Contenido |
|---|---|---|
| `dev` inicial | `e46de09cc7a5572f0d1f6c411cf6dd8226d54dc5` | Había trabajo legítimo sin commit y archivos compilados modificados. |
| `codex/safety-dev-before-tcc-split` | `e46de09c` | Referencia inicial, sin modificar el historial. |
| Snapshot común | `d8c6d067` | 100 archivos de código/configuración/documentación previamente pendientes, incluida toda la integración existente. |
| `codex/dev-tcc` | `749ccf5630251e6e33644a621070b6e4604ad05f` | Snapshot completo más compatibilidad de edición y retorno de migraciones. Worktree `.artifacts/dev-tcc-preserved`. |
| Separación de `dev` | `7351658f` | Retirada del proveedor, conservación de funcionalidades compartidas. |
| Protección de credenciales | `f332f3e3` | Asignaciones vacías del gateway conservadas con autorización explícita. |

Todos los commits son locales. No se utilizaron remotos, main, PR ni producción. No se hizo fetch, push, reset, clean, stash ni rebase. Las otras ramas locales preexistentes se conservaron sin integrar sus cambios.

## Implementación exclusiva conservada en TCC

- `BACKEND/shipping/`: cliente API, contratos disponibles, catálogo del proveedor, modelos, cotización, instantáneas, validación de checkout, creación de despachos posterior al pago, tareas y reintentos, serializadores, rutas y pruebas.
- Sus tres migraciones, perfiles logísticos de productos, cotizaciones, despachos y eventos.
- `ShippingCalculator`, `ShippingProfileFields`, `TCCAddressFields`, `ShipmentDetails`, `services/shipping`, `useShippingConfig` y pruebas exclusivas.
- Adaptación TCC de detalle de producto, administración, carrito, checkout, pedidos, correos y ejemplos de configuración.
- Documentación original de integración y validaciones. El seguimiento por API sigue pendiente del contrato de TCC; no se agregó una implementación inventada.

En `dev` no se registran la aplicación, rutas ni tareas del proveedor. Se retiraron sus imports, modelos activos, validaciones obligatorias y variables de ejemplo. Las dependencias compartidas como `requests` siguen disponibles para Wompi y Meta.

## Funcionalidades generales conservadas

Editor transaccional e idempotente de productos, precio, inventario, descripción, especificaciones, galería, imagen principal y recuperación de errores/borradores. La lectura de borradores utiliza únicamente los campos generales admitidos.

Direcciones por usuario, destinatario, teléfono, barrio, complemento, indicaciones, predeterminada y permisos de propietario. El selector compartido `DeliveryLocationFields` conserva los nombres geográficos en un catálogo local independiente, sin códigos ni solicitudes al proveedor. Conserva los valores de direcciones históricas aunque su escritura no coincida con el catálogo.

Contabilidad, impuestos/descuentos adicionales en cero según la política autorizada, validación de importes Wompi y procesamiento idempotente de órdenes pendientes. La confirmación manual de un pago Wompi se rechaza: requiere confirmación oficial. Si una referencia histórica impide eliminar un producto, se devuelve 409 y se permite desactivarlo, sin borrar sus datos.

CRM, chats, adjuntos, plantillas, usuarios/trabajadores, visitas, PDFs, correos, Meta y WhatsApp conservan su código general. Los módulos CRM/usuarios/visitas/gateway no tienen diferencias respecto del snapshot común; solamente se desacopló del proveedor el contenido específico de correos de envío.

## Envío temporal explícito

Se recuperó la regla previa de la aplicación: **$25.000 COP por debajo de $500.000 COP de subtotal; gratis desde $500.000 COP**. No es un fallback ante una cotización fallida. Django calcula el importe y la firma de Wompi. No se llama a TCC ni se crean guías.

## Migraciones y conservación de la base

- `ecommerce.0014_useraddress_complement_and_more`: conserva los campos generales. En una instalación nueva de dev ya no agrega el código exclusivo del proveedor. El efecto de cambiar esta migración compartida fue ensayado antes de aplicar la compatibilidad.
- `ecommerce.0015`: conserva la contabilidad general de pedidos e intenciones.
- `ecommerce.0016_producteditoroperation`: conserva la idempotencia del editor.
- `ecommerce.0017_preserve_legacy_address_writes` en dev: si una base PostgreSQL histórica conserva la columna del proveedor, establece únicamente su default vacío para permitir nuevas direcciones desde el modelo general. No borra columnas, tablas, filas ni códigos existentes. En una base nueva no crea esa columna.
- `ecommerce.0017_resume_provider_address` en la rama TCC: agrega esa columna únicamente si falta al retomar la integración desde una base nueva de dev.

Las tablas y los registros de migraciones TCC ya existentes permanecen en la base local, aunque no estén cargados por la aplicación dev. No se usó `--fake`, no se revirtieron migraciones ni se eliminaron volúmenes. El plan final de dev no tiene operaciones pendientes; ambos modelos pasan `makemigrations --check --dry-run`.

Se ensayaron dos bases exclusivamente sintéticas: `test_tcc_split_20261019` y `test_tcc_resume_20261019`. La primera conserva producto, precio, stock, perfil y código al alternar TCC → dev → TCC. La segunda demuestra dev nuevo → TCC con migraciones reales. Quedaron conservadas para inspección; los tests y navegadores gestionaron sus propias bases desechables.

## Respaldo y archivos excluidos

Respaldo privado local: `.artifacts/tcc-separation/dev-before-split.dump`, 426398 bytes; `pg_restore --list` terminó correctamente. SHA-256: `AC7726C91BACF34506CF1D99E3D35FF5EECE25F39660D7F9CB7F06E826B1FF0C`. No forma parte de Git. Solo se aplicó a la base de desarrollo la migración de compatibilidad de direcciones.

El diff previo y una copia de los archivos compilados existentes se conservan en `.artifacts/tcc-separation/`. Los cambios previos de `frontend_U/dist` y el archivo local vacío `verify_live_meta_handshakes.py` permanecen fuera de los nuevos commits. Por ello, el checkout principal puede seguir mostrando esos archivos previos; no representan cambios de código pendientes de esta separación.

No se editaron ni versionaron archivos privados de entorno, credenciales, sesiones, imágenes, bases de datos o volúmenes. Se revisaron nombres y patrones de secretos antes de los commits. Las variables vacías `TCC_API_TOKEN` y `TCC_PRODUCTION_API_TOKEN` permanecen exclusivamente como máscaras de seguridad del gateway en Compose, autorizadas expresamente; no son credenciales ni requisitos funcionales. El arranque de Django se verificó eliminando todas las variables `TCC_*` del proceso.

## Pruebas y resultados Docker

| Verificación | Resultado |
|---|---|
| Dev: `ecommerce crmChat transactional_mail AppVisits gestion usuarios.test_account usuarios.test_terms` | **276 aprobadas**, PostgreSQL aislado. |
| TCC: los módulos anteriores más `shipping`, sin tokens de entorno y con despacho desactivado | **307 aprobadas**; contratos sandbox simulados. |
| Gateway WhatsApp | **38 aprobadas**. |
| Editor de productos en navegador contra PostgreSQL sintético | Crear/editar, validaciones, dos imágenes, principal, error 503, reintento, persistencia y responsive aprobados. |
| `shipping-without-carrier.cjs` | Dirección persistida con selectores locales; carrito 1280/768/390; checkout $125.000 + $25.000 = $150.000; widget Wompi simulado recibe 15.000.000 centavos; cero solicitudes al proveedor. |
| `chat-media.cjs` y `template-preview.cjs` | Adjuntos, texto, error/reintento, no duplicación, vistas por canal y responsive aprobados. |
| TypeScript y Vite en ambas ramas | Aprobados; advertencia de tamaño de chunks, sin errores de compilación. |
| Imágenes backend y frontend de ambas ramas | Cuatro imágenes construidas localmente. |
| Django, migraciones y Compose | Checks sin errores; planes coherentes. |
| Celery | Dos workers responden; no registran tareas `shipping.tasks`. |
| Nginx y API | Sintaxis válida; `/api/`, `/api/products`, `/api/brands`, `/api/categories` responden 200 tras completar el arranque. |
| Servicios locales | Backend, frontend, workers, Beat, PostgreSQL, Redis, Nginx, media, Ollama, gateway y Mailpit en ejecución. |

Comandos base utilizados:

```powershell
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 backend python manage.py test ecommerce crmChat transactional_mail AppVisits gestion usuarios.test_account usuarios.test_terms --noinput
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml run --rm --no-deps -T backend python manage.py migrate --plan
docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npx vite build --outDir /tmp/dev-without-tcc-final-verified'
docker compose -f docker-compose.dev.yml --profile test run --rm --no-deps -T whatsapp-gateway-test
docker compose -f .artifacts/tcc-separation/build-images.yml build
```

Para la rama TCC se montó su `BACKEND` o frontend desde el worktree aislado. Playwright se ejecutó mediante `docker-compose.qa.yml`. Evidencias y logs privados quedan en `.artifacts/tcc-separation/`.

## Límites y continuación

No se certifican permisos reales de Meta, entrega a teléfonos, correos reales, tarifas TCC externas ni cobros reales: esas operaciones no se realizaron. Las pruebas de proveedores y Wompi utilizaron simulaciones; las verificaciones de persistencia usaron PostgreSQL real y aislado. Los scripts manuales que pueden operar datos o servicios reales no se ejecutaron.

Continuar el desarrollo general en el checkout principal, rama `dev`. Para retomar TCC, utilizar `.artifacts/dev-tcc-preserved` y revisar primero la configuración privada y la bandera de despacho. Al reintegrar las ramas en una tarea futura, resolver deliberadamente los cambios de modelos/migraciones/UI y repetir los dos ensayos; no copiar archivos de migración ni activar el proveedor automáticamente. No restaurar la base como método de cambio de rama.
