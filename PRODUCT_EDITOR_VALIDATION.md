# Editor general de productos en dev

La integración logística queda conservada en `codex/dev-tcc`. Este documento describe únicamente el editor disponible en `dev`.

Se conserva el guardado transaccional de producto, existencias por sede, especificaciones, galería e imagen principal. La clave de operación permite reintentos sin crear copias; la versión del producto impide sobrescribir ediciones concurrentes. Se validan precio positivo, precio original, cantidades enteras y archivos JPG/PNG/WebP de hasta 5 MB en frontend y backend.

El formulario conserva los datos ante errores, muestra validaciones dentro del modal y bloquea solicitudes duplicadas. El borrador conserva texto y archivos mediante almacenamiento local e IndexedDB. Las imágenes retiradas de la galería no se borran del almacenamiento histórico.

Los productos se crean y editan sin perfil logístico. No se inventan pesos, dimensiones ni valores declarados.

## Verificación dentro de Docker

- `python manage.py test ecommerce.test_product_editor ecommerce.test_product_presentation`: persistencia, permisos, idempotencia, galería, principal, rollback y conflictos.
- `python -m ecommerce.e2e_server --isolated-e2e`, con `CRM_TEST_POSTGRES=1`: PostgreSQL sintético independiente, almacenamiento temporal y tráfico externo bloqueado.
- Playwright `product-editor-live.cjs`: crear, validar, subir dos imágenes, elegir principal, simular error 503, reintentar, recargar, editar y cambiar principal. Vistas 1280/768/390.
- TypeScript y Vite ejecutados en el contenedor frontend.

Migración general conservada: `ecommerce.0016_producteditoroperation`.
