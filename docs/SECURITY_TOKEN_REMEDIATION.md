# Credenciales históricas y revocación preventiva

Revisión: 23 de noviembre de 2026, America/Bogota. Estado: **bloquea merge y despliegue**.

## Límites de la intervención

No se ha enviado, validado ni autenticado ningún JWT histórico contra producción. Los antiguos helpers privados de comprobación remota quedaron deshabilitados. Los selectores se obtuvieron únicamente del payload local, sin verificar su firma: los seis artefactos apuntan al mismo selector de cuenta, pero esto no demuestra titularidad, que sea una cuenta personal, ni correspondencia con producción. No se publican esos selectores. No se ha modificado ninguna cuenta de producción, su contraseña, permisos, sesiones ni versiones.

Se necesita confirmación administrativa de titularidad y uso no compartido antes de cualquier revocación. Un ID contenido en un token histórico no basta para confirmar que sea la misma persona en otra base de datos.

## Cobertura comprobada

| Mecanismo | Versión de cuenta | Resultado |
|---|---|---|
| JWT access, configuración activa `core.settings` | `PasswordVersionJWTAuthentication.get_user` compara con base de datos; ausencia equivale a versión 0 | Invalida access anterior tras incremento |
| JWT refresh y access derivado | Emisión incluye versión; `PasswordVersionRefreshSerializer` compara usuario activo y versión antes de renovar | Invalida renovación anterior |
| WebSockets Django, CRM y cliente | Middleware usa autenticación versionada; consumidores consultan estado/versión en mensajes y eventos | Conexión antigua se cierra; reconexión antigua se rechaza |
| Socket.IO del gateway WhatsApp | Solo firma HMAC, rol y vencimiento durante handshake | **Brecha: sin consulta de versión ni revocación por cuenta; conexión abierta no se revalida** |
| DRF TokenAuthentication | Token persistido independiente del JWT | Requiere revocar filas de la cuenta expresamente |
| Django SessionAuthentication | Hash de sesión depende de contraseña, no de `password_version` | Requiere eliminar únicamente sesiones persistidas de la cuenta |
| Configuración alternativa `core.config.base` | Conserva JWTAuthentication sin versión | No es la configuración activa revisada; debe alinearse o retirarse antes de utilizarla |

No se declara cobertura universal. El bloqueo solicitado por el usuario sigue vigente.

Prueba nueva `core.test_token_revocation`: credenciales sintéticas, login válido, access y refresh válidos, renovación válida, incremento transaccional con bloqueo de fila, rechazo del access original y del access renovado y del refresh anterior, login con la misma contraseña y nuevos tokens válidos. Comprueba que hash de contraseña, rol y estado no cambian. Las pruebas existentes de WebSocket cubren conexiones abiertas y reconexión tras incremento.

## Mecanismo adicional necesario

1. Incorporar identidad y versión a tokens de Socket.IO y verificar ambas contra una fuente backend autorizada. No basta con añadir un claim sin compararlo.
2. Revalidar conexiones abiertas y desconectarlas por revocación o expiración; comprobar el rechazo de reconexión y nuevas emisiones con credenciales antiguas. Cubrir indisponibilidad del validador con cierre seguro.
3. Preparar revocación por usuario de tokens DRF y sesiones Django. Las sesiones deben identificarse por `_auth_user_id`, sin borrar sesiones ajenas ni imprimir su contenido. No hay blacklist SimpleJWT activa: el control de versión debe seguir cubriendo todos los puntos de aceptación y renovación.
4. Confirmar configuración efectiva del servidor y titularidad mediante un canal administrativo; no utilizar el token expuesto para ello.
5. Solo después: respaldo restringido del registro y persistencias afectadas, transacción con `select_for_update`, incremento de versión, revocación de persistencias y cierre de conexiones. Comparar que contraseña, permisos y otros campos no cambian. Probar reingreso autorizado sin registrar contraseñas ni tokens.

La rotación global de la clave JWT es último recurso y no está ejecutada ni propuesta como sustituto de la revocación por cuenta.

## Localización de los seis artefactos

| Artefacto | Archivo |
|---|---|
| JWT-1 | `BACKEND/scripts/decode_jwt.py` |
| JWT-2 | `BACKEND/scripts/decode_jwt copy.py` |
| JWT-3 | `BACKEND/scripts/pruebas/probar_certificado.py` |
| JWT-4 | `BACKEND/scripts/pruebas/test_cargar_csv.py` |
| JWT-5 | `BACKEND/scripts/pruebas/test_certificado.py` |
| JWT-6 | `BACKEND/scripts/test_perfil_capacitacion.py` |

JWT-1 y JWT-2 son copias exactas: seis apariciones, cinco valores distintos. No se incluyen valores, firmas ni claims identificativos.

Introducción original común: `79bc35f81bff55663a753c94f3ce7dce76e33ae8`. También aparecen en raíces de historia independientes: `189c2e7d98eafe1f23f9c891f172e7ac315bb83b`, `04e31c200b643d60cb39249eefee680bb53d9440`, `5dce239254468c2bf80dbeec30c4264a647d2231`, `8ca6b8b3bd408a5fdd2ba73991c2970c354a2229`, `4e68bfc691e4ccf5e973dd1cb5b38969540bfd16`, `7c69aeed845582281caf5284c013903d9a40dcee`, `f76b80d4e4387b34ae801a86947fd6e85567c35c`.

El inventario exacto de snapshots y referencias está en [readiness/jwt-history-inventory.json](readiness/jwt-history-inventory.json). Corte anterior a publicar el saneamiento: 196 commits accesibles mediante las referencias locales obtenidas por fetch; cada aparición permanece en 194 snapshots y 29 referencias. Incluye `origin/main`, `origin/dev`, la rama remota de integración, ramas remotas codex, ramas locales de respaldo y `server/main`. Las referencias locales de seguimiento son evidencia del último fetch; no se inspeccionan clones ajenos, forks, reflogs remotos ni cachés del proveedor.

La eliminación del árbol se realiza en `fb28c1d662cfd19b357e23a6bdee48ffa28c9d6e`. Esto **no elimina los blobs ni commits antecesores**, incluso después del push.

## Gitleaks y alcance adicional

Gitleaks 8.24.3, contenedor sin red, reportes redactados:

- Árbol completo de `fb28c1d6`: **0 hallazgos**.
- Delta explícito `origin/dev..fb28c1d6`: **0 hallazgos**, 14 commits analizados.
- Historial completo alcanzable desde `fb28c1d6`: **31 hallazgos**, 104 commits analizados. No está saneado.
- Seis hallazgos corresponden a JWT. Los demás requieren triage: dos cabeceras de autorización, posibles secretos en antiguos `.env`/`.envdev`/ejemplos/Compose, valores ficticios de guías y dos fixtures sintéticos documentados. No se excluyen hallazgos históricos para aparentar un resultado limpio.

Referencias adicionales relevantes:

| Commit | Ruta | Acción pendiente |
|---|---|---|
| `126c67316f57091d76c1781fdad8fd8e17f3749f` | `.env` | Revisar privadamente y rotar credenciales Wompi/Meta expuestas que sigan vigentes |
| `61b4ab8413881c7bc62a70d76e4051dffe71e0b7` | `.envdev` | Mismo tratamiento, incluyendo entornos de prueba |
| `f4eda49a5b4a18742d57d2f4a12548bfeeb6ae7d` | `.env`, `docker-compose.dev.yml` | Clasificar y revocar valores reales |
| `875c140a31afec1c3f7c0a95f8aa39a5fe1ad157` | `.env.example` | Revisar posible secreto Meta; un ejemplo no debe contener secretos reales |
| `d78bc6fd5325530e3ba75473849649fc92b69e76` | `apis_grapApiMetea.md` | Revisar y revocar autorizaciones reales |

Nunca utilizar esos valores para probar si todavía son válidos. Rotar la clave de cifrado Meta requiere un plan de recifrado de datos y respaldo: no cambiarla a ciegas.

## Plan coordinado para sanear historia compartida

No se ha reescrito ninguna rama ni ejecutado force push. Se necesita autorización separada, responsables y ventana coordinada:

1. Congelar temporalmente pushes; inventariar ramas, tags, PR, forks, cachés y clones. Confirmar hashes de referencias.
2. Crear respaldo completo verificable de Git y referencias fuera del repositorio, cifrado, acceso restringido y retención definida; contiene secretos históricos. Respaldar también configuración y datos necesarios para rotaciones. El respaldo de PostgreSQL de preparación de despliegue no sustituye un respaldo completo de Git.
3. Revocar credenciales identificadas y confirmar cobertura de sesiones antes de considerar segura una copia pública. El vencimiento declarado sin firma validada no es prueba de revocación.
4. Ensayar filtrado en un clon aislado: eliminar secretos por contenido y rutas donde corresponda, preservando código útil. Filtrar todas las raíces y referencias afectadas; no basta reconstruir la rama de integración desde un `dev` contaminado.
5. Ejecutar Gitleaks sobre árbol e historia resultantes, revisar diff funcional y ejecutar suites completas. Guardar correspondencia de commits antes/después sin secretos.
6. Presentar el resultado, el respaldo y las referencias exactas para autorización específica de actualización coordinada del remoto. Coordinar con GitHub purga de vistas/cachés de PR si procede; no se garantiza borrar copias ya descargadas.
7. Actualizar clones/worktrees de colaboradores sin sobrescribir cambios, renovar referencias y repetir escaneo. Mantener respaldo restringido y plan de recuperación.

## Pruebas de esta revisión

- Docker/PostgreSQL aislados: **540 pruebas backend aprobadas**.
- Selección explícita de revocación, seguridad de scripts, cuentas y WebSockets: **15 aprobadas**.
- Docker frontend: instalación limpia, **0 vulnerabilidades npm audit**, lint, **10 pruebas**, TypeScript y build aprobados.
- Docker gateway: instalación limpia, **38 pruebas** y build aprobados; no conexiones a clientes.
- Estas pruebas prueban mecanismos locales, no revocación de la cuenta real ni saneamiento del remoto.

El PR #15 debe permanecer en borrador. CI verde no autoriza merge: faltan titularidad, cobertura de revocación, revocación real autorizada y saneamiento coordinado del historial compartido.
