# Inventario previo a la segunda conciliación — 20 de octubre de 2026

Auditoría realizada con árbol limpio en 96ba8524 antes de cualquier restauración adicional. Fuentes d8c6d067, 749ccf56, 97f2bc96 y recuperación 96ba8524.

Se ejecutaron diff --name-status, --summary, --find-renames, log --left-right --cherry-pick y range-diff. Se compararon contenido, árboles, nombres de pruebas, migraciones, configuración, rutas y dependencias. No hay archivos del árbol d8c6d067 ausentes en 96ba8524. Las omisiones identificadas son fragmentos de interfaz, representación del envío y dos pruebas específicas del editor; no se trata de pérdida general de CRM/adjuntos/plantillas.

Clases: 1 funcionalidad anterior faltante; 2 mejora posterior conservada; 3 retirada/regla de separación descartada; 4 equivalente posterior; 5 conciliación de migración; 6 prueba adaptada; 7 generado excluido. Los archivos dist del checkout original son clase 7 y no forman parte de este diff ni se manipulan.

| Archivo | d8c6d067 | 749ccf56 | 97f2bc96 | Recuperación inicial | Clase | Acción | Justificación |
|---|---|---|---|---|---|---|---|
| .env.example | Sí | Sí | Sí | Sí | 4 | Conservar | Sandbox equivalente y cuentas privadas vacías, flags desactivados y dominios oficiales. No exponer valores. |
| .env.prod.example | Sí | Sí | Sí | Sí | 4 | Conservar | Sandbox equivalente y cuentas privadas vacías, flags desactivados y dominios oficiales. No exponer valores. |
| BACKEND/core/settings.py | Sí | Sí | Sí | Sí | 4 | Conservar | Sandbox equivalente y cuentas privadas vacías, flags desactivados y dominios oficiales. No exponer valores. |
| BACKEND/crmChat/consumers.py | Sí | Sí | Sí | Sí | 2 | Conservar | Autorización y revocación de WebSocket; mantiene los adjuntos y formato anteriores sin cambios. |
| BACKEND/crmChat/test_customer_websocket_access.py | No | No | Sí | Sí | 2 | Conservar | Autorización y revocación de WebSocket; mantiene los adjuntos y formato anteriores sin cambios. |
| BACKEND/crmChat/websocket_auth.py | Sí | Sí | Sí | Sí | 2 | Conservar | Autorización y revocación de WebSocket; mantiene los adjuntos y formato anteriores sin cambios. |
| BACKEND/ecommerce/e2e_server.py | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/ecommerce/migrations/0014_useraddress_complement_and_more.py | Sí | Sí | Sí | Sí | 5 | Conciliar | Conservar 0014/0017/0018 publicadas; 0019 reemplaza la variante de retorno y preserva códigos sin borrar datos. |
| BACKEND/ecommerce/migrations/0017_preserve_legacy_address_writes.py | No | No | Sí | Sí | 5 | Conciliar | Conservar 0014/0017/0018 publicadas; 0019 reemplaza la variante de retorno y preserva códigos sin borrar datos. |
| BACKEND/ecommerce/migrations/0018_delivery_without_shipping.py | No | No | Sí | Sí | 5 | Conciliar | Conservar 0014/0017/0018 publicadas; 0019 reemplaza la variante de retorno y preserva códigos sin borrar datos. |
| BACKEND/ecommerce/migrations/0019_restore_provider_address.py | No | No | No | Sí | 5 | Conciliar | Conservar 0014/0017/0018 publicadas; 0019 reemplaza la variante de retorno y preserva códigos sin borrar datos. |
| BACKEND/ecommerce/models.py | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| BACKEND/ecommerce/pricing.py | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| BACKEND/ecommerce/serializers.py | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| BACKEND/ecommerce/test_checkout_without_shipping.py | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/ecommerce/test_delivery_addresses.py | Sí | Sí | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/ecommerce/test_legacy_product_preservation.py | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/ecommerce/test_product_editor.py | Sí | Sí | Sí | Sí | 6 | Recuperar | Restaurar las dos pruebas de valor declarado y perfil manual eliminadas; mantener suite general. |
| BACKEND/ecommerce/test_shipping_independence.py | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/ecommerce/views.py | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| BACKEND/shipping/services.py | Sí | Sí | No | Sí | 2 | Conservar | Cotización anterior intacta; agrega guardia de cuenta y copia persistente de dirección al borrador. |
| BACKEND/shipping/tcc.py | Sí | Sí | No | Sí | 4 | Conservar | Sandbox equivalente y cuentas privadas vacías, flags desactivados y dominios oficiales. No exponer valores. |
| BACKEND/shipping/test_recovery.py | No | No | No | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/shipping/tests.py | Sí | Sí | No | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/test_ecommerce_api.py | Sí | Sí | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/transactional_mail/documents.py | Sí | Sí | Sí | Sí | 1 | Conciliar | Distinguir NULL fuera de compra de una tarifa real cero; no inferir ausencia de transporte ni promoción. |
| BACKEND/transactional_mail/service.py | Sí | Sí | Sí | Sí | 1 | Conciliar | Distinguir NULL fuera de compra de una tarifa real cero; no inferir ausencia de transporte ni promoción. |
| BACKEND/transactional_mail/tests.py | Sí | Sí | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| BACKEND/usuarios/admin_accounts.py | No | No | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| BACKEND/usuarios/test_admin_accounts.py | No | No | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| BACKEND/usuarios/tests.py | Sí | Sí | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| BACKEND/usuarios/urls.py | Sí | Sí | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| BACKEND/usuarios/views.py | Sí | Sí | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| DELIVERY_CHECKOUT_VALIDATION.md | Sí | Sí | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| GENERAL_PR_VALIDATION.md | No | No | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| PRODUCT_EDITOR_VALIDATION.md | Sí | Sí | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| REGRESSION_SUITE_FIXES.md | No | No | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| TCC_COMPLETION_VALIDATION.md | Sí | Sí | No | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| TCC_INTEGRATION.md | Sí | Sí | No | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| TCC_LOCAL_SEPARATION.md | No | No | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| TCC_LOCATION_TEMPLATES_VALIDATION.md | Sí | Sí | No | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| TCC_RECOVERY_VALIDATION.md | No | No | No | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| USERS_WORKERS_VALIDATION.md | No | No | Sí | Sí | 4 | Conservar/documentar | Informe histórico o validación posterior; marcar alcance y agregar inventario completo, sin tratar documentación como funcionalidad activa. |
| frontend_U/src/admin/pages/ProductsPage.tsx | Sí | Sí | Sí | Sí | 4 | Conservar | Editor transaccional conservado; omite perfiles no modificados para permitir edición histórica sin inventar logística. |
| frontend_U/src/admin/pages/UsersPage.tsx | Sí | Sí | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| frontend_U/src/admin/services/admin_users.ts | Sí | Sí | Sí | Sí | 2 | Conservar | CRUD y permisos de cuentas más recientes; contraseñas, inactivos, sesiones y protección de administradores. |
| frontend_U/src/admin/types/index.ts | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| frontend_U/src/app/pages/CartPage.tsx | Sí | Sí | Sí | Sí | 1 | Recuperar | Faltan aviso de error de configuración y desglose/total pendiente del carrito. No restaurar tarifa fija ni promoción. |
| frontend_U/src/app/pages/CheckoutPage.tsx | Sí | Sí | Sí | Sí | 1 | Conciliar | Restaurar ajustes de la cotización y estados pendientes; conservar dirección, referencia idempotente y progreso. |
| frontend_U/src/app/pages/HomePage.tsx | Sí | Sí | Sí | Sí | 3 | Conservar | Conservar eliminación de anuncios falsos f5fdf28a; descartar solo reglas de separación, no recuperar promociones. |
| frontend_U/src/app/pages/LoginPage.tsx | Sí | Sí | Sí | Sí | 3 | Conservar | Conservar eliminación de anuncios falsos f5fdf28a; descartar solo reglas de separación, no recuperar promociones. |
| frontend_U/src/app/pages/OrderDetailPage.tsx | Sí | Sí | Sí | Sí | 1 | Conciliar | Distinguir NULL fuera de compra de una tarifa real cero; no inferir ausencia de transporte ni promoción. |
| frontend_U/src/components/DeliveryLocationFields.tsx | No | No | Sí | Sí | 4 | Conservar | Catálogo general adicional conservado; TCC mantiene catálogo de códigos y normaliza dirección histórica cuando coincide inequívocamente. |
| frontend_U/src/components/TCCAddressFields.tsx | Sí | Sí | No | Sí | 4 | Conservar | Catálogo general adicional conservado; TCC mantiene catálogo de códigos y normaliza dirección histórica cuando coincide inequívocamente. |
| frontend_U/src/data/delivery-locations.json | No | No | Sí | Sí | 4 | Conservar | Catálogo general adicional conservado; TCC mantiene catálogo de códigos y normaliza dirección histórica cuando coincide inequívocamente. |
| frontend_U/src/services/orders.ts | Sí | Sí | Sí | Sí | 2 | Conservar | Compatibilidad NULL, dirección persistida, validación histórica y seguridad de pago; TCC ya reincorporado por fragmentos. |
| frontend_U/tests/product-editor-live.cjs | Sí | Sí | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| frontend_U/tests/shipping-without-carrier.cjs | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| frontend_U/tests/tcc-live-flow.cjs | Sí | Sí | No | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| frontend_U/tests/users-admin.cjs | No | No | Sí | Sí | 6 | Conservar | Pruebas posteriores/sintéticas adaptadas. APIs manuales protegidas contra ejecución al importar; pruebas sin TCC se aplican a modo desactivado. |
| frontend_U/vite.config.ts | Sí | Sí | Sí | Sí | 4 | Conservar | Caché configurable para QA Docker; configuración y dependencias originales mantenidas. |

Total de diferencias previas: 61. Archivos del snapshot ausentes: 0.

## Áreas idénticas y verificación funcional

El editor product_editor.py, ProductDescription, product_draft, galería y servicios de imágenes mantienen el contenido del snapshot. CRM conserva message_format, quick_replies, adaptadores Meta/WhatsApp, consumidores y vistas de medios, plantillas/editor/vista previa y chat del e-commerce; los únicos cambios del módulo frente al snapshot son mejoras de autorización WebSocket y sus pruebas. AppVisits, gateway, Docker Compose, Nginx, lockfiles y dependencias son idénticos. Sus rutas y endpoints siguen presentes. Las rutas de usuarios tienen ocho adiciones y seis modificaciones intencionales de seguridad; se validan con la suite actual.

## Pruebas antiguas retiradas o renombradas

- test_declared_price_distributed_without_rounding_inflation: faltante, restaurar prueba con editor completo y reparto exacto por paquete.
- test_manual_declared_value_and_existing_images_survive_edit: la prueba actual solo conserva imágenes; restaurar además perfil manual y persistencia logística.
- usuarios test_patch_alterna_estado_colaborador: reemplazado por test_patch_no_permite_autoinactivacion y test_patch_alterna_otra_cuenta_y_revoca_sesiones, por seguridad.
- usuarios test_post_masivo_por_colaborador_ids: reemplazado por test_post_masivo_por_usuario_ids: el original usaba idcolaborador, que no existe en el modelo Usuario vigente. Se conserva el contrato publicado usuario_ids y la atomicidad, sin reintroducir campos inválidos.
- usuarios test_post_masivo_id_inexistente_registrado_en_no_encontrados: reemplazado por test_post_masivo_id_inexistente_rechaza_operacion; no se acepta un éxito parcial silencioso.
- usuarios test_patch_sin_campo_tipousuario_retorna_400: reemplazado por test_patch_sin_campo_tipo_usuario_retorna_400.
- usuarios test_patch_respuesta_incluye_rol_anterior_y_nuevo: reemplazado por test_patch_respuesta_refleja_rol_guardado_sin_contrasena; se verifica estado guardado sin datos sensibles.

Las pruebas test_checkout_without_shipping y shipping-without-carrier se conservan para modo TCC desactivado. No son el comportamiento forzado de TCC activo. TCC dispone de sus suites restauradas tests, test_estimates y test_recovery.

## Causas y plan de conciliación

La recuperación anterior se concentró en restaurar módulos exclusivos y conciliar checkout; no generó un inventario de cada fragmento general ni comparó nombres de todas las pruebas antiguas. Así quedaron sin restaurar los avisos/desglose del carrito y cobertura del editor. NULL y cero se trataron juntos en correos/PDF, lo cual es incorrecto para una cotización real de cero. Se corregirán selectivamente, sin recuperar tarifas fijas ni anuncios de envío gratis, y se agregarán pruebas de regresión.

749ccf56: su condición de publicación valida también al reactivar un producto, mientras mantiene edición ordinaria de históricos. Se incorporará esa condición sin sustituir el serializador completo. Su migración 0017_resume_provider_address está sustituida por 0019, que preserva tanto bases nuevas como columnas históricas. No se restaurará el archivo antiguo porque chocaría con el historial ya publicado.

No existía API de seguimiento/cancelación/webhooks TCC en las fuentes. Se conserva enlace web e historial local; no se declara integración de estados remotos. Cotización sandbox se prueba mediante contrato simulado, no llamadas externas sin credenciales/autorización.
## Cierre de la conciliación

Las clases 1 del inventario inicial se corrigieron: aviso de configuración del carrito, total pendiente al faltar cotización, desglose de ajustes, valores de impuestos/descuentos cotizados y distinción entre tarifa cero y envío NULL. Las dos pruebas del editor fueron recuperadas con sus nombres originales. Se incorporó la condición exacta de publicación de 749ccf56 sin copiar el serializador completo.

Se recuperó además TCC_BRANCH_LOCAL.md, exclusivo de 749ccf56, como documento histórico rotulado. La comparación con esa rama deja únicamente su antigua 0017_resume_provider_address ausente de forma intencional, reemplazada por 0019. Se repusieron sus banderas TCC_SHIPPING_ENABLED=False para las pruebas generales Wompi/compra; las nuevas pruebas de compra sin transporte y editor general también las fijan para no depender de la configuración privada.

Los cinco nombres antiguos de pruebas de usuarios restantes están reemplazados por las pruebas de seguridad indicadas, no eliminados sin equivalente. No se reintrodujo el identificador inexistente idcolaborador ni la actualización masiva parcial silenciosa. No se retiraron mejoras de cuentas ni WebSocket.

| Archivo adicional frente al inventario previo | d8c6d067 | 749ccf56 | 97f2bc96 | Recuperación final | Clase | Acción/justificación |
|---|---|---|---|---|---|---|
| BACKEND/ecommerce/tests.py | Sí | Sí | Sí | Sí | 6 | Recuperadas las banderas explícitas de 749ccf56 para pruebas generales. |
| TCC_BRANCH_LOCAL.md | No | Sí | No | Sí | 4 | Documento histórico restaurado; se indica sustitución de migración. |
| RECOVERY_COMPLETENESS_INVENTORY.md | No | No | No | Sí | 4 | Inventario exhaustivo previo y conciliación documentada. |
| RECOVERY_COMPLETENESS_REPORT.md | No | No | No | Sí | 4 | Informe de resultados y matriz de servicios. |
| frontend_U/tests/recovery-completeness.cjs | No | No | No | Sí | 6 | Regresiones de fragmentos de interfaz recuperados. |
| frontend_U/tests/recovery-websocket.cjs | No | No | No | Sí | 6 | WebSocket por Nginx/ASGI/Redis con cuenta sintética de QA. |

El diff del documento mismo y los nuevos informes son adiciones de auditoría; no representan funcionalidades antiguas faltantes. Las 780 rutas de d8c6d067 están presentes en la recuperación. Los archivos iguales se verificaron mediante los árboles Git; no requieren restauración. Las dependencias y Docker/Nginx del repositorio no tienen diferencias respecto a d8c6d067. La configuración de servicios para QA permanece privada/ignorada, sin editar el Compose del proyecto ni sus credenciales.