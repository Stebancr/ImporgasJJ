# Ubicación, direcciones y checkout — validación de desarrollo

Fecha: 20 de octubre de 2026. Rama: codex/recover-tcc-on-current-dev. Base de esta tarea: 02157ad2. Se trabajó en el worktree aislado; dev/main, PR y producción no se modificaron. Todo frontend, backend, navegador, compilación y pruebas se ejecutó dentro de Docker.

## Problemas y correcciones

Los selectores ya estaban separados en la integración recuperada, pero eran controles nativos sin búsqueda. Ahora son Autocomplete de la versión MUI 9 instalada, con dos controles accesibles: Departamento de entrega y Ciudad o municipio de entrega. Ciudad queda deshabilitada hasta seleccionar departamento; cambiarlo borra ciudad/código y descarta la cotización anterior. Se filtra sin depender de mayúsculas o acentos, se ordena alfabéticamente, se quitan duplicados normalizados y se conserva el primer código canónico. Los códigos se usan internamente, nunca en etiquetas ni opciones visibles. Los desplegables se renderizan junto al campo para funcionar dentro de paneles/modales sin quedar detrás.

La sección de envío de producto ya era visible siempre en esta rama y se conservó cerca del precio, con precio del producto, aviso de que no incluye entrega, estado pendiente sin importe ficticio, selección/cambio de destino, tarifa y total estimado. La ubicación se conserva entre productos y ahora también al registrarse/iniciar sesión; solo se transfiere geografía desde el selector invitado al estado autenticado, sin copiar direcciones privadas de otras cuentas. Se muestra plazo solo si existe en la respuesta; no se inventan fechas.

El formulario compartido de /direcciones y checkout mantiene una única pareja departamento/ciudad. Se añadieron validación por campo, errores del backend junto al dato, etiquetas accesibles y conservación del borrador. Se reutilizan los mecanismos existentes de bloqueo de doble envío y deduplicación del backend. Las tarjetas del checkout ahora muestran también destinatario y complemento, además de barrio, teléfono, localidad y estado predeterminado. Se selecciona la predeterminada o la primera guardada cuando no hay una predeterminada disponible.

Durante la creación/edición de una dirección dentro del checkout se suspende y descarta la cotización activa. Al guardar o cancelar, se vuelve a cotizar con la dirección correspondiente; se conserva el carrito y el paso. Los errores de inicio de pago aparecen dentro del checkout. Un fallo transitorio mantiene la misma referencia de pago para permitir reintentos idempotentes, mientras que un cambio de carrito/destino/cotización genera una referencia acorde al nuevo contenido. La caducidad y la recotización explícita continúan invalidando la tarifa anterior.

Los errores de transporte se presentan con lenguaje sencillo y sin etiquetas técnicas del proveedor. El servicio API ahora adjunta el mapa de validaciones a Error para que el formulario pueda mostrar cada mensaje en su campo; las vistas existentes siguen recibiendo el mismo mensaje general.

## Modelo, endpoints y cálculo

No hubo cambios en modelos ni migraciones en esta tarea. No se crearon endpoints. Se usan las rutas existentes:

- GET /api/shipping/config y /api/shipping/cities.
- POST /api/shipping/estimate para producto/invitado.
- POST /api/shipping/quote para carrito/checkout y GET /api/shipping/destination para el destino anterior autenticado.
- GET/POST /api/ecommerce/user/addresses y GET/PUT/DELETE /api/ecommerce/user/addresses/{id}.
- POST /api/orders para la intención Wompi y el webhook existente para la confirmación oficial.

El servidor conserva la autoridad sobre productos, precios, cantidades, perfil logístico, destino, vigencia y tarifa. Revalida la cotización antes de aceptar el pago. Fórmula con transporte activado: subtotal de productos + transporte cotizado + impuestos - descuentos. Las direcciones se vinculan por propietario y se copian al pedido; el cliente no decide el importe a cobrar. No se añadieron impuestos, descuentos, tarifa fija ni promociones de envío gratis.

TCC permanece desactivable por bandera. Con la integración desactivada se mantiene explícitamente la política previa de envío fuera de la compra y NULL; no se interpreta como gratis. Las validaciones de cotización vigente y bloqueo de pago se prueban con transporte activado. En producción no se cambió ninguna bandera ni credencial.

## Archivos

- frontend_U/src/components/TCCAddressFields.tsx: búsqueda, dependencia, orden, deduplicación, códigos canónicos y accesibilidad.
- frontend_U/src/components/DeliveryAddressForm.tsx: validación local y por campo del servidor, mensajes accesibles y conservación de datos.
- frontend_U/src/components/ShippingCalculator.tsx: continuidad de geografía al iniciar sesión y mensajes comprensibles.
- frontend_U/src/app/pages/CheckoutPage.tsx: tarjetas completas, dirección inicial, pausa/recotización del editor, continuidad y error de pago idempotente.
- frontend_U/src/services/api.ts: mapa de errores por campo compatible con el mensaje existente.
- frontend_U/src/services/shipping.ts: traducción de errores de transporte para el cliente.
- Pruebas actualizadas: shipping-location.cjs, tcc-checkout.cjs, tcc-live-flow.cjs, recovery-completeness.cjs.
- Pruebas nuevas: location-select.cjs (helper compartido) y delivery-address-flow.cjs.

## Pruebas Docker

| Verificación | Resultado |
|---|---|
| Django: ecommerce shipping crmChat transactional_mail AppVisits gestion usuarios | 422 ejecutadas, aprobadas; sin fallos |
| TypeScript y construcción Vite/imagen frontend | Aprobadas |
| Búsqueda por departamento/ciudad, teclado, ciudad inicialmente deshabilitada | Aprobadas |
| Duplicados de localidad/departamento y orden alfabético | Aprobadas con catálogo sintético duplicado y variantes de escritura |
| Ubicación entre dos productos, recarga, registro y navegación | Aprobadas; se conserva la ciudad seleccionada |
| Producto sin destino, tarifa correcta, error temporal, sin cobertura y logística incompleta | Aprobadas; no se conserva tarifa anterior ni se muestra gratis |
| Checkout con una o varias direcciones | Aprobadas con API real de QA y fixtures |
| Sin direcciones, validación junto al campo y nueva dirección integrada | Aprobadas |
| Error al guardar, doble clic, cancelación y datos retenidos | Aprobadas; se crea una sola dirección |
| Edición, eliminación confirmada, predeterminada y deduplicación | Aprobadas con PostgreSQL sintético persistente |
| Recotización por cantidad/destino, carrito y paso de pago tras recarga | Aprobadas |
| Total de servidor y webhook duplicado | Aprobados: 250000 productos + 30000 transporte = 280000 COP; una orden/guía sintética |
| Fallo temporal de inicio de pago | Error dentro del checkout y misma referencia en el reintento; sin alertas del navegador |
| Responsive | 1280, 768 y 390 px, sin desbordamiento horizontal |
| Regresión de Usuarios, chats/archivos y plantillas | Aprobada en navegador y suite backend |

El flujo integral usa PostgreSQL real de QA, login, direcciones y carrito persistidos. Intercepta TCC, widget Wompi y confirmación firmada: no genera pagos, tarifas externas, guías ni mensajes reales. Los errores de las primeras pruebas correspondían al cambio de API de slots de MUI 9, a pruebas antiguas de select nativo y a seleccionar una opción nativa oculta en vez de la lista visible; fueron corregidos y las pruebas finales pasaron.

Logs ignorados dentro de .artifacts/: location-backend.log, location-ui-final.log, location-verified.log, delivery-final-persistence.log, location-regressions.log y location-release-build.log. En tcc-live-flow se comprueba que el nuevo domicilio queda guardado/seleccionado, el error conserva campos, el POST duplicado devuelve la misma dirección, se conserva cartKey/address_id/step tras recarga y Wompi recibe 28000000 centavos del servidor.

## Pendientes y límites

La prueba contra servidores externos de TCC y un pago real no se ejecutaron; la integración se validó con contratos sandbox simulados. El contrato disponible no aporta plazo de entrega ni API de seguimiento, así que no se inventaron. Para habilitar un entorno real hacen falta configuración privada, cuenta/origen válidos, bandera de activación y revisión independiente. Este trabajo queda local en la rama de recuperación; no se publicó ni se desplegó.