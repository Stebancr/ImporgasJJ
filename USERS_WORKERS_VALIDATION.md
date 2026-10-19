# Usuarios y trabajadores: validación de la rama dependiente

Base: PR #7, https://github.com/Stebancr/ImporgasJJ/pull/7, `dev` → `main`.
Commit base: `e46de09cc7a5572f0d1f6c411cf6dd8226d54dc5`.
Rama de esta tarea: `codex/fix-usuarios-trabajadores`; destino inicial: `dev`.

Este Pull Request depende de #7. Debe revisarse después o junto con el PR anterior.
No debe fusionarse en main antes de resolver esa dependencia. Ningún PR fue fusionado.

## Problemas y correcciones

- `ListaUsuarios` filtraba obligatoriamente `estado=1`: los inactivos nunca llegaban a la interfaz. El listado ahora admite `estado=todos|1|0`, búsqueda por nombre/documento/correo/teléfono/usuario y paginación acotada.
- La edición no guardaba documento y ocultaba errores al actualizar la sede. Las rutas de cuentas ahora usan `admin_accounts.py`, con validación compartida de tipos, longitud, correo, duplicados y relaciones. Los campos omitidos se conservan; contraseñas no vacías se rechazan en la edición general.
- El permiso histórico `IsSuperAdmin` admite roles 1, 2, 3 y 4. No se cambió ese permiso global, para evitar efectos en otros módulos: las rutas de esta tarea tienen comprobaciones explícitas. Administradores 1 y 4 pueden listar; el administrador 1 puede editar cuentas no administrativas y sus propios datos. Solo el superadministrador 4 cambia estados, roles o contraseñas y crea administradores. No puede retirarse el último administrador ni el último superadministrador activo.
- Las mutaciones de seguridad bloquean las credenciales administrativas en orden estable antes de comprobar las restricciones. La operación masiva es atómica y rechaza identificadores/documentos inválidos; máximo 1000 cuentas por operación. No se eliminan perfiles ni registros históricos.
- Contraseña: endpoint separado con confirmación, validadores configurados de Django y `set_password()`. Incrementa `password_version` y elimina tokens DRF antiguos. El mismo mecanismo revoca tokens al cambiar estado o rol; reactivar requiere un inicio de sesión nuevo.
- La autenticación WebSocket del CRM ahora valida `password_version`. Las conexiones abiertas vuelven a comprobar estado, rol y versión antes de responder o entregar eventos; se cierran con 4403 si fueron revocadas.
- La interfaz incorpora Todos/Activos/Inactivos, confirmación de cambios de estado, cambio de contraseña separado, errores por campo dentro del modal y bloqueo de solicitudes duplicadas. Los borradores se conservan al fallar. Las respuestas antiguas de búsqueda no sobrescriben una búsqueda más reciente.

## Archivos y API

- Backend: `usuarios/admin_accounts.py`, `usuarios/urls.py`, `usuarios/test_admin_accounts.py`.
- Seguridad de sesiones del CRM: `crmChat/websocket_auth.py`, `crmChat/consumers.py`.
- Frontend: `src/admin/pages/UsersPage.tsx`, `src/admin/services/admin_users.ts`, `tests/users-admin.cjs`.
- No se crean migraciones: se utiliza el campo `password_version` existente en el PR base. No se alteraron datos de desarrollo ni producción para implementar la función.

Se conservan las rutas existentes bajo `/api/user/`: `register`, `register/<perfil_id>`, `lista-usuarios`, `cambiar-estado-usuario[/<perfil_id>]`, `actualizar-rol-usuario/<perfil_id>`.
Nueva ruta: `POST /api/user/register/<perfil_id>/password` con `new_password` y `confirm_password`.
La creación administrativa requiere `password` y `confirm_password`. Los identificadores de estas rutas son del perfil Usuario, no de Credenciales.
Las respuestas nunca incluyen la contraseña ni su hash.

## Pruebas realizadas el 19 de octubre de 2026

Todo se ejecutó en Docker. Las pruebas usan una base PostgreSQL temporal `test_crm_upgrade`, archivos temporales, transporte simulado para proveedores y correo en memoria. No se enviaron mensajes a clientes ni se modificó producción.

1. Backend: 230 pruebas aprobadas con:

   ```sh
   docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 backend python manage.py test usuarios.test_admin_accounts usuarios.test_account usuarios.test_terms crmChat shipping AppVisits.tests_offline --noinput
   ```

   Incluye creación/edición, documento y cargo, conservación de contraseña, duplicados, sede inválida, filtros, paginación, política y confirmación de contraseña, revocación de access/refresh, inactivación/login/reactivación, restricciones de permisos, autoinactivación y actualización masiva atómica. También incluye autenticación, CRM/chat/plantillas/Meta/Baileys, TCC y sincronización de visitas. La nueva prueba de WebSocket verifica revocación de conexiones abiertas y rechazo de reconexiones antiguas por contraseña, estado y rol.

2. Frontend: TypeScript y Vite build aprobados dentro de `users-frontend-qa`. Advertencia existente de tamaño de algunos bundles; no hay errores de compilación.
3. Playwright en contenedor: `tests/users-admin.cjs`, aprobado. Verifica filtro de inactivos, documento editable, error junto al campo y dentro del modal, conservación del formulario después de un 400, doble clic sin duplicar solicitudes, confirmación de contraseña y tamaños 1280/768/390. API simulada; persistencia y permisos se comprueban en las pruebas Django.
4. Suite completa del commit base: **366 pruebas, 56 fallos de aserción y 40 errores**.
5. Suite completa con los seis primeros tests de esta tarea: **372 pruebas, los mismos 56 fallos y 40 errores**. La comparación de los nombres de los tests fallidos coincide exactamente; los nuevos tests pasan. La prueba adicional de revocación WebSocket forma parte de las 230 regresiones aprobadas.

Los fallos preexistentes incluyen tests de `usuarios.tests` que todavía usan modelos/rutas antiguos, importación de `test_ecommerce_api`, generación PDF de visitas y expectativas anteriores de presentación/checkout/Wompi. Están presentes también al ejecutar el código original de #7: no se declaran aprobadas estas áreas ni la suite completa. Deben resolverse en el PR base o en una tarea específica antes de dar por cumplido el criterio de suite íntegramente verde.

Evidencia local privada (fuera del commit): `.artifacts/users-base-tests.log`, `users-final-all-tests.log`, `users-passing-regressions.log`, `users-ui-tests.log`, `users-final-frontend-build.log`.

## Estado y límites

Los numerosos cambios locales anteriores de chat, productos, TCC y correo se conservaron en la copia original de `dev`; esta tarea se desarrolló en un worktree limpio e independiente desde el SHA remoto del PR #7. No se incluyeron esos cambios locales en este PR, ni `.env`, credenciales, multimedia, bases de datos, dependencias ni archivos compilados.

Se volvió a ejecutar `fetch`: la rama base permanece en el SHA indicado. GitHub informa que #7 es fusionable sin conflictos; no tiene check-runs ni contextos de CI publicados, por lo que su estado combinado `pending` no significa que existan pruebas de CI aprobadas.

Este PR debe permanecer en revisión/borrador mientras se resuelven los fallos preexistentes de la suite completa. Después de fusionar #7, actualizar desde la rama vigente sin reescribir historial, cambiar la base del nuevo PR a `main` y repetir las pruebas. No desplegar ni fusionar automáticamente.
