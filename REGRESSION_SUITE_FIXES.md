# Corrección de los 96 resultados fallidos de la suite

Trabajo sobre `codex/fix-usuarios-trabajadores`, PR #8, dependiente de #7 (`dev`). La solicitud posterior del usuario amplía el alcance para resolver los fallos encontrados en la base. No se fusiona ningún PR ni se modifica producción.

## Causas y correcciones

| Grupo | Resultados fallidos iniciales | Causa y solución |
| --- | ---: | --- |
| Usuarios | 81 | Las pruebas aún creaban `Usuarios`/`Colaboradores`, autenticaban el modelo obsoleto y usaban nombres de rutas, argumentos y respuestas anteriores. Se migraron los fixtures a `Credenciales`/`Usuario`, los payloads al contrato actual y las aserciones a los datos persistidos. Se conservan las pruebas de autenticación, CRUD, búsquedas, paginación, permisos, CSV, roles, estado y Excel. |
| PDFs de visitas | 7 | El cierre manual de `FileResponse` emitía `request_finished` y cerraba la conexión PostgreSQL dentro de la transacción de `APITestCase`. Se cierran los recursos de archivo sin volver a emitir la señal. No se cambió la generación de PDF para hacer pasar estos tests. |
| Descripción de productos | 3 | Una edición parcial exigía completar el perfil de transporte de un producto histórico aunque solo cambiara su descripción. La validación completa se mantiene al crear/publicar un producto o modificar su transporte; editar una descripción no vuelve a exigir esos datos. Se agregó una regresión explícita con TCC habilitado para impedir publicaciones o cambios de transporte incompletos. |
| Checkout/Wompi | 4 | Los tests del flujo de transporte fijo heredaban `TCC_SHIPPING_ENABLED` del entorno, pero enviaban el payload del flujo fijo, sin cotización TCC. Ahora declaran explícitamente ese modo de prueba. Las pruebas específicas de TCC mantienen su propia configuración y comprueban cotizaciones, importes, vencimiento y despacho con proveedor simulado. No se deshabilitó TCC en la aplicación. |
| Script de diagnóstico | 1 | `test_ecommerce_api.py` ejecutaba peticiones HTTP y `sys.exit()` durante su importación por Django. El diagnóstico queda dentro de `main()` y solo se ejecuta explícitamente mediante `if __name__ == '__main__'`. Importarlo ya no realiza solicitudes ni aborta el runner. |
| **Total** | **96** | **56 fallos de aserción y 40 errores iniciales.** |

La revisión también identificó dos validaciones reales pendientes en Usuarios:

- `PATCH /user/perfil/<id>` podía alternar el estado sin aplicar la protección de la cuenta autenticada ni revocar sesiones. Ahora utiliza la misma operación transaccional de `AccountState`, con permisos de superadministrador, bloqueos, protección del último administrador y revocación de sesiones. Se prueban tanto el rechazo de autoinactivación como la actualización de otra cuenta y su versión de contraseña.
- La operación masiva podía aceptar una solicitud sin `estado` y responder sin realizar el cambio. Ahora exige explícitamente 0 o 1. Los identificadores inexistentes rechazan atómicamente la operación; los tests comprueban esa política vigente.

No se eliminaron pruebas para ocultar fallos ni se añadieron `skip` o `expectedFailure`. Las expectativas antiguas que contradecían las restricciones actuales se reemplazaron por comprobaciones de estas restricciones y de la persistencia real.

## Verificación

Todos los comandos de aplicación y pruebas se ejecutaron dentro de Docker, usando PostgreSQL temporal de pruebas, multimedia temporal, correo en memoria y proveedores simulados.

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps -T -e CRM_TEST_POSTGRES=1 backend python manage.py test --noinput
```

Primera ejecución completa después de las correcciones: 373 pruebas aprobadas, cero fallos y cero errores. Ejecución final incluyendo la regresión adicional de publicación/transporte: **374 pruebas aprobadas en 45,926 segundos; cero fallos y cero errores**.

Evidencias locales privadas: `.artifacts/fix96-first.log`, `.artifacts/fix96-full.log` y `.artifacts/fix96-final.log`. No se incluyen logs, secretos, `.env`, multimedia, bases de datos ni artefactos generados en el commit.

No hay migraciones nuevas. La rama base `dev` permanece en `e46de09cc7a5572f0d1f6c411cf6dd8226d54dc5`. Los cambios locales anteriores de la copia original de desarrollo siguen conservados fuera de esta rama de trabajo.
