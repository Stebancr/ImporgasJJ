# Revocación global de sesiones

Base: origin/dev `4cc209fcbb4e31cbfb2480bd63ed1a495f670cda`. Rama independiente; no incluye cambios funcionales de CRM, iconos, World Office ni del PR #15. Las dependencias del gateway se corrigen en otro PR.

## Autoridad persistente

PostgreSQL mantiene `GlobalAuthState`, fila única ID 1, versión inicial 1. No se usa una caché local para decidir autenticación. `AuthSession` identifica familias JWT y sesiones Django/DRF, con usuario, versión global, versión individual, fecha, expiración, tipo y revocación; nunca guarda el bearer ni su firma. `PersistentTokenVersion` vincula tokens DRF con esa metadata. `AuthRevocation` registra operación, versión, fecha, motivo codificado, actor administrativo y conteos.

JWT nuevos incluyen global_auth_version, password_version, session_id, user_id, iat, exp y token_type. Access y renovación comprueban versiones y sesión padre contra la base. Una versión ausente se rechaza: no existe compatibilidad que la considere cero. Se conservan contraseñas, roles y permisos.

Sesiones Django: login registra versiones, tipo, fecha y sesión padre; middleware verifica cada petición, incluido Django Admin. Las históricas sin versión se cierran. DRF: tokens sin metadata se rechazan; POST /auth/personal-token/ requiere autenticación JWT/Django y rota el anterior. Un token DRF no puede auto-renovarse. Los nuevos DRF expiran a los 30 días y están ligados a ambas versiones y sesión padre.

POST /auth/logout/ revoca la familia actual y la sesión Django si existe. El refresh anterior no restaura la familia cerrada. No modifica la contraseña ni otras sesiones independientes de la cuenta.

## Realtime y navegador

Channels verifica el JWT al conectar; cada mensaje/evento y una revisión cada 2 segundos comprueban usuario activo, permisos, versiones, sesión y expiración. La revisión periódica cierra conexiones inactivas. Un error de verificación cierra la conexión.

Socket.IO conserva HMAC con tipo gateway_realtime, usuario, fecha, vencimiento, versiones y sesión padre. Comprueba firma y estructura localmente. Cada handshake/reconexión y revisión periódica requiere POST /internal/whatsapp/realtime/validate/, con firma de petición, timestamp y replay protection existentes. El backend consulta PostgreSQL. Se revalida cada 2 segundos, sin retries y con timeout de 2 segundos; ante indisponibilidad o rechazo se cierra el transporte. Latencia normal de cierre aproximada: hasta 4 segundos más planificación. El gateway no recibe JWT_SIGNING_KEY: no valida JWT directamente.

El token Socket.IO dura 120 segundos. Al caducar, el frontend solicita autorización HTTP antes de reconectar; si el padre fue revocado, recibe 401 y no puede obtener otra credencial. El frontend centraliza limpieza de tienda y administración, notifica el cierre de transportes y sincroniza pestañas mediante storage. La limpieza es idempotente y cancela reconexiones antiguas. Una respuesta tardía compara la credencial de su petición y no borra un login nuevo. Monitores cada 15 segundos y al enfocar cubren páginas sin WebSocket. El backend sigue siendo la autoridad.

Se muestra «La plataforma fue actualizada. Por seguridad, inicia sesión nuevamente». Los clientes móviles que usen la misma API reciben igual rechazo; no hay aplicación móvil independiente en esta rama para verificar su interfaz.

## Comando

Dentro del contenedor backend, durante mantenimiento:

```sh
python manage.py revoke_all_sessions --reason=production_release --operation-id=release-IDENTIFICADOR --actor-id=ID_ADMIN_VALIDADO
```

Los dos identificadores del ejemplo son marcadores. Actor administrativo activo obligatorio en producción. Motivo y operación aceptan códigos acotados, sin datos personales. La transacción bloquea el estado global, incrementa versión, revoca familias, elimina tokens DRF y sesiones Django y registra conteos. No modifica usuarios, contraseñas, correo, rol ni perfiles.

Repetir el mismo operation-id y parámetros devuelve el primer resultado sin incrementar ni borrar sesiones posteriores. Reutilizarlo con parámetros diferentes falla. Otra operación deliberada usa otro ID. Sin operation-id se genera una operación independiente: es segura, pero incrementa otra vez. El contador de refresh corresponde a familias JWT persistidas; no cuenta access stateless. Salida limitada a resultado, versión y conteos.

## Firma y servicios

SimpleJWT utilizaba SECRET_KEY. Se introduce JWT_SIGNING_KEY; producción exige al menos 32 caracteres y que sea independiente de SECRET_KEY. Generarla con CSPRNG y guardar únicamente en configuración restringida/gestor de secretos. No imprimirla ni enviarla al navegador. Desarrollo mantiene compatibilidad para pruebas sintéticas.

No se rota SECRET_KEY: también protege sesiones, recuperación y firmas internas. Backend/ASGI y servicios Python que carguen settings productivos requieren la nueva variable. El gateway conserva su secreto de servicio para introspección y no necesita la clave JWT. Brevo, Wompi, Meta, World Office, Redis y PostgreSQL no dependen de ella para su propia autenticación. No se borra la sesión Baileys al cerrar sesiones humanas del panel.

No se detectó un consumidor productivo propio de TokenAuthentication que deba migrarse a personal-token; los scripts manuales no son cuentas de servicio. El administrador debe inventariar consumidores externos/móviles, que no pueden enumerarse completamente desde este repositorio, y preparar su reingreso.

## Migración y pruebas

usuarios.0010_global_auth_revocation crea cuatro tablas y una restricción de singleton. No renombra ni elimina columnas históricas, no cambia productos y no toca media. Probada en PostgreSQL QA nuevo tras pg_dump lógico verificado (888 bytes, base inicialmente vacía; no es respaldo de producción).

Docker: check, makemigrations --check, plan y migrate correctos; suite completa **527 aprobadas** (incluye cinco pruebas de saneamiento de scripts). Gateway de autenticación: **42 aprobadas**, incluyendo handshakes polling reales, dos transportes, revocación backend simulada y rechazo de reconexión. Frontend: pruebas de limpieza idempotente/credenciales antiguas, Wompi, lint, TypeScript y build.

Chromium contra Django/Redis/Nginx y arnés Socket.IO sin Baileys: login sintético, dos pestañas, comando real de revocación QA, access anterior 401 y reingreso con la misma contraseña en 1440, 768 y 390 px. El límite de cinco logins/minuto permanece; el arnés espera una ventana al ejecutar las tres resoluciones. El test solicita al controlador ejecutar la revocación y espera su confirmación, evitando confundir latencia de herramientas con latencia de cierre.

qa/security/gateway-harness.mjs no importa Baileys ni abre cuentas reales. browser.cjs restringe destinos y exige bandera de QA. No se prueban JWT históricos contra producción. El inventario histórico se entrega sin valores ni claims identificativos; no se declara revocación real hasta la intervención correspondiente.

## Despliegue y rollback seguro

1. Mantener PR #15 en borrador. Revisar los PR separados, CI, diffs y secretos nuevos. Excluir World Office experimental y cambios no aprobados.
2. Coordinar rotación de secretos históricos no JWT: la revocación global no invalida Wompi/Meta. No probarlos mediante autenticación. No reescribir historia compartida sin autorización independiente y respaldo completo de Git.
3. Definir mantenimiento y anunciar el nuevo login. Confirmar credenciales administrativas sin compartirlas. Respaldo PostgreSQL fresco verificado, configuración restringida, imágenes, commit, montajes y huellas de media.
4. Llevar únicamente código revisado a main; pull ff-only con árbol limpio. Configurar JWT_SIGNING_KEY antes de iniciar imágenes productivas nuevas. Revisar plan y aplicar migración aditiva.
5. Ejecutar el comando con operation-id de liberación y actor validado; guardar solo conteos. Reiniciar backend/ASGI, workers, Beat y gateway sin borrar volúmenes para cerrar transportes anteriores al mecanismo.
6. Utilizar credenciales sintéticas controladas previas al corte para comprobar rechazo. **Nunca utilizar los JWT históricos**. Comprobar login administrativo y cliente con las mismas contraseñas, reintento idempotente, salud y ausencia de cambios de usuarios, DB y media.
7. **No volver a imágenes que ignoren la versión global ni a claves comprometidas.** Rollback solo a una imagen compatible con el guard, preservando clave nueva y versión persistente. Si la única imagen anterior carece del mecanismo, mantener mantenimiento y corregir hacia adelante: volver a ella reabriría credenciales. No revertir esta migración ni restaurar automáticamente la base. Rollback de frontend no debe retirar el control backend/gateway.

No se ha ejecutado este despliegue ni revocado sesiones productivas. Los conteos y versiones QA no son valores de producción.
