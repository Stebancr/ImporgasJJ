# Editor de productos — validación en dev

Fecha: 2026-10-18. Trabajo local en `dev`, conservando los cambios anteriores. No publicado ni desplegado en producción.

## Precio y valor declarado

El precio es el importe de venta de una unidad del producto. El campo anterior `declared_value` representaba el valor de **cada paquete físico**. Para cotización, `quotation_payload` suma los valores de todos los paquetes en `valormercancia`; para despacho se envía el valor de cada paquete. Por eso, para productos de un paquete, el administrador terminaba escribiendo dos veces el mismo importe.

Se contrastó con el material TCC suministrado: `woocommerce-tcc-shipping/admin/class-tcc-shipping-admin.php` calcula `average_price = products_cost / units` y lo asigna a cada unidad; `includes/class-tcc-shipping-settings.php` utiliza el valor agregado en la liquidación. No se añadieron reglas comerciales de mínimos, seguros o recargos no documentadas.

Los productos nuevos ofrecen marcada «Usar el precio de venta como valor declarado». El backend deriva el valor del precio vigente, repartido entre paquetes por unidad, sin guardar una copia desactualizada. Los centavos restantes se distribuyen sin aumentar el total: 100 / 3 = 33,34 + 33,33 + 33,33. Dos unidades declaran 200, no 600. El modo manual conserva el significado anterior: valor por paquete. No cambia el precio de venta ni añade un cargo de envío fijo; TCC continúa calculando su tarifa.

Los perfiles históricos mantienen modo manual mediante `default=False`. No se inventaron pesos ni dimensiones para productos incompletos. El modelo existente no tiene SKU ni unidad comercial editable; no se añadieron campos sin soporte.

## Guardado y API

Nuevos endpoints administrativos multipart:

- `POST /api/products/editor`: crear.
- `POST /api/products/{id}/editor`: editar.

`payload` contiene clave UUID estable, producto, fecha de edición conocida, galería ordenada con índice principal, inventario por sede y características. Los archivos se identifican mediante `upload_N`. El backend valida pertenencia de imágenes y características, permisos, stock entero no negativo, precios y datos de transporte. No acepta una actualización basada en una versión anterior del producto.

Una transacción guarda todos los registros. Los reintentos con la misma clave y contenido recuperan el resultado; reutilizar una clave confirmada con contenido diferente produce 409. La clave del borrador de creación se conserva en el navegador. Los archivos recién escritos se eliminan si la transacción falla. Los archivos previamente existentes retirados de una galería se conservan físicamente; no se realiza una limpieza irreversible automática.

La galería ahora permite elegir la principal antes de guardar, ordenar, describir y retirar imágenes. Retirar la principal selecciona otra cuando existe. Los cambios de galería y características dejan de guardarse inmediatamente. Una restricción en PostgreSQL impide dos imágenes principales para un producto. Las rutas anteriores de imágenes se mantienen y conservan una principal cuando queda una galería no vacía.

Formulario con secciones, errores en el modal y junto a campos, resumen enfocable, encabezado y pie fijos, confirmación de cierre, bloqueo de guardados simultáneos, rechazo temprano de imágenes mayores a 5 MB o formatos no admitidos. Se rechaza guardar si no se pudieron cargar los datos completos del producto. El borrador de creación conserva texto, transporte, selección/orden/textos de imágenes y clave de reintento.

## Archivos de esta tarea

- Backend: `ecommerce/product_editor.py`, `ecommerce/models.py`, `ecommerce/serializers.py`, `ecommerce/urls.py`, `ecommerce/views.py`.
- TCC: `shipping/models.py`, `shipping/serializers.py`, `shipping/services.py`.
- Frontend: `src/admin/pages/ProductsPage.tsx`, `src/admin/services/admin_products.ts`, `src/admin/services/admin_api.ts`, `src/admin/services/product_draft.ts`, `src/components/ShippingProfileFields.tsx`, `src/services/shipping.ts`.
- Pruebas: `BACKEND/ecommerce/test_product_editor.py`, `frontend_U/tests/product-editor-live.cjs`, adaptación del contrato en `frontend_U/tests/tcc-checkout.cjs`.

## Migraciones y respaldo

Aplicadas únicamente en la base local de desarrollo `imporgas_db`:

- `ecommerce.0016_producteditoroperation`: registro de idempotencia, normalización de selección principal sin eliminar imágenes y restricción única condicional.
- `shipping.0003_productshippingprofile_declared_value_from_price`: indicador del modo automático, desactivado para datos históricos.

Antes de aplicar: `pg_dump -Fc`, listado verificado con `pg_restore --list`, y archivo multimedia TAR verificado con `tar -tzf`. Copias privadas, excluidas de Git:

- `.artifacts/product-editor-before-20261018.dump`
- `.artifacts/product-editor-media-before-20261018.tar.gz`

Comprobación antes/después: 4 productos y 5 imágenes. Ningún perfil histórico activado automáticamente. Se reiniciaron solamente `backend` y `celery-worker` de desarrollo para cargar código. Sin borrado de volúmenes.

## Verificaciones Docker

1. `docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 -e TCC_SHIPPING_ENABLED=False backend sh -c 'python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test shipping ecommerce crmChat usuarios.test_account --noinput'`: 245 pruebas aprobadas en esa ejecución.
2. Tras añadir dos casos más: mismo contenedor, `python manage.py test ecommerce.test_product_editor --noinput`: 9 pruebas aprobadas. Incluyen rollback tardío de DB/archivos, reintentos, permisos, conflictos, valor automático con redondeo, manual histórico, conservación de archivos y cambio de principal.
3. `docker compose -f docker-compose.dev.yml exec -T frontend-ecommerce sh -c 'npx tsc --noEmit && npm run build -- --outDir /tmp/product-editor-build'`: TypeScript y build; salida fuera de `dist` versionado.
4. Backend de prueba `python -m shipping.e2e_server --tcc-e2e`, con `CRM_TEST_POSTGRES=1`: PostgreSQL desechable, archivos de prueba, TCC y pagos simulados. Al finalizar, elimina únicamente su base de pruebas.
5. Playwright en `chat-ui-test`: `product-editor-live.cjs`, `shipping-location.cjs`, `tcc-checkout.cjs`, aprobados. Editor contra Django/PostgreSQL reales aislados: abrir → validar → completar → subir dos imágenes → elegir principal → simular fallo 503 → reintentar → guardar → reabrir → verificar persistencia → eliminar principal → cambiar precio → guardar → reabrir. Pruebas adicionales de ubicación y checkout con APIs simuladas.
6. Responsive verificado a 1280, 768 y 390 px sin desbordamiento del formulario. Capturas revisadas de escritorio y móvil en `.artifacts/product-editor-*.png`.
7. Acceso local tras reiniciar mediante solicitudes desde Docker a Nginx: catálogo `/api/products` responde 200; nuevo editor sin autenticación responde 401, como corresponde. Compilación final aprobada tras ajustar el tipo de la clave UUID restaurada del borrador.

Logs privados de verificación: `.artifacts/product-editor-regression.log`, `product-editor-targeted-final.log`, `product-editor-ui-final.log`, `product-editor-build.log`. No contienen credenciales de producción.

## Límites y despliegue posterior

- No se enviaron despachos, cobros ni mensajes reales. La fórmula y persistencia de TCC están probadas; no se certifica una tarifa real nueva del transportador en esta tarea.
- Los archivos retirados de galerías se retienen por seguridad. Una futura limpieza debe revisar referencias y respaldo antes de borrar físicamente.
- Build mantiene el aviso preexistente de paquetes JavaScript mayores a 500 kB.
- Los cambios están sin commit junto con el trabajo anterior. Producción necesita revisión, publicación y migraciones antes de desplegar este editor.
- Reversión preferente de código: conservar las columnas/tablas aditivas y los datos; no restaurar el dump sobre nuevas operaciones ni eliminar medios. Restaurar respaldos solo en una base aislada para recuperación revisada.
