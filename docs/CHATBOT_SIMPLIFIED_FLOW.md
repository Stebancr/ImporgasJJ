# Chatbot comercial simplificado — validación 2026-10-13

## Alcance y estado

Trabajo en `dev`, con `origin/main` 9808b47b incluido y referencias actualizadas.
La base de esta tarea es 6cde63ac. El archivo local ajeno
`verify_live_meta_handshakes.py` se conserva sin seguimiento. Esta modificación
no toca frontend, modelos, migraciones, integraciones, gateway ni datos históricos.
Los cambios anteriores de 6cde63ac siguen pendientes de revisión en el PR #4;
el diff completo dev→main también los incluye. No deben confundirse con esta tarea.

## Diagnóstico y comportamiento

Antes, el flujo resolvía referencias y consultaba productos/precios antes de algunas
decisiones de transferencia. La nueva bandera se evalúa antes de cualquier regla
o consulta del catálogo. La implementación anterior queda completa en
`OllamaService._get_recommendation_response`, cubierta por sus pruebas originales.

Con la bandera apagada:

- Saludo oficial en la primera respuesta externa; no se repite en ecommerce,
  donde el frontend ya lo muestra. `greeting_shown` persiste en el estado existente.
- Compras, cotizaciones, disponibilidad, precios, reservas, repuestos, visitas,
  recomendaciones, compatibilidad, instalación, garantía y solicitud de asesor
  se transfieren mediante reglas rápidas. No hay acceso al catálogo.
- Horarios, sedes y teléfonos provienen únicamente de `Location` activa. No se
  inventan horarios faltantes. La información institucional no lista referencias
  comerciales, precios ni enlaces.
- Frases ambiguas usan un clasificador JSON de Ollama: hasta cuatro mensajes
  anteriores y la necesidad ya registrada, salida de 40 tokens, conexión de 3 s
  y lectura de 8 s. Su texto nunca se envía al cliente; solo se acepta una etiqueta
  de una lista cerrada. Error, timeout o etiqueta inválida derivan al asesor.
- Se conservan el resumen y los campos históricos; solo se añaden marcas al JSON
  de estado existente. No se vacía memoria ni se crean columnas.
- La transferencia conserva el mensaje entrante, pasa a espera/asignación con el
  mecanismo existente y notifica al CRM. La asignación se confirma antes de intentar
  enviar la respuesta. Un error del canal no deshace la transferencia.
- Reintentos no generan otra respuesta ni asignación. Las conversaciones ya
  transferidas no reciben avisos de inactividad ni se cierran por el bot.
- Se conservan la cola por sesión, la concesión PostgreSQL, la idempotencia por
  mensaje y los dos procesos de la cola chatbot. No se cambian permisos de Meta,
  ventanas de mensajería ni se añaden mensajes proactivos o mecanismos de pago.

## Configuración y reactivación

```env
CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=False
```

El valor predeterminado en Django y Compose es `False`, también en producción.
Para reactivar recomendaciones, establecer `True` en el entorno privado utilizado
por Compose y recrear backend y workers para que todos lean el mismo valor:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --no-deps backend celery-worker celery-chatbot celery-beat
```

Este comando presupone que se ha revisado y desplegado previamente el cambio de
colas del PR #4. La bandera no requiere migración. Las conversaciones transferidas
siguen a cargo del asesor hasta que el flujo existente cambie su estado.

## Archivos de esta tarea

- `BACKEND/crmChat/simple_chatbot.py`: reglas, clasificador limitado e información institucional.
- `BACKEND/crmChat/ollama_service.py`: selección del flujo; lógica anterior intacta.
- `BACKEND/crmChat/tasks.py`: asignación antes del envío y protección de la espera.
- `BACKEND/core/settings.py`, ejemplos de entorno y Compose dev/prod: bandera.
- `BACKEND/crmChat/test_simple_chatbot.py`: casos funcionales, errores, canales y concurrencia.
- `BACKEND/crmChat/tests.py`: pruebas anteriores ejecutadas con recomendaciones activadas.
- `BACKEND/scripts/verify_simple_chatbot.py`: prueba reproducible local de HTTP/colas/reinicio.
- Este informe.

## Pruebas ejecutadas dentro de Docker

```sh
docker compose -f docker-compose.dev.yml exec -T -e CRM_TEST_POSTGRES=1 backend python manage.py test crmChat --noinput
docker compose -f docker-compose.dev.yml exec -T backend python manage.py check
docker compose -f docker-compose.dev.yml exec -T backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.prod.yml config --no-env-resolution --no-interpolate --quiet
docker compose -f docker-compose.dev.yml exec -T backend python manage.py shell -c "exec(open('scripts/verify_simple_chatbot.py').read()); run('live')"
```

Resultado: **153 pruebas CRM aprobadas**, incluidos tests anteriores con bandera
activa, reglas comerciales sin consultas SQL, saludo, referencia contextual,
institucional, timeout, mensajes de agentes/celular, cuatro canales, reintentos,
asignación y recuperación. Django check correcto y ninguna migración nueva.

| Prueba local | Simultáneas | Promedio | Máximo | Pendientes | Duplicados |
|---|---:|---:|---:|---:|---:|
| Tareas con PostgreSQL y transporte simulado | 8 | 0,2096 s | 0,2191 s | 0 | 0 |
| HTTP → Nginx → Django → Celery → transferencia ecommerce | 8 | 0,588 s | 0,693 s | 0 | 0 |
| Cola con worker detenido y posterior arranque | 8 | 7,197 s | 7,293 s | 0 | 0 |

La última medición incluye deliberadamente la espera de arranque del worker.
Para reproducirla, detener **solo el worker local** `celery-chatbot`, ejecutar
`run('prepare')`, arrancarlo y ejecutar `run('check')` con el mismo comando de shell.
Los scripts exigen `DEBUG=True`, usan conversaciones ecommerce sintéticas y no
envían mensajes externos. No borran esas conversaciones.

Al finalizar: Redis `LLEN chatbot=0`, `LLEN celery=0`, Celery active/reserved=0.
Las rutas `/`, `/admin/chat`, `/admin/visitas` y `/api/` devolvieron 200.
Esto verifica disponibilidad; no constituye una nueva validación integral de
pagos, PDFs, Excel ni de todos los módulos ajenos a esta modificación.
Los transportes externos se simularon; no se enviaron mensajes a clientes reales.
La suite general tenía 49 fallos/33 errores heredados documentados en el informe
anterior; esta tarea ejecutó la suite CRM completa y las comprobaciones indicadas.

## Producción, integración y rollback

Inspección de solo lectura: servidor en `main` 9808b47b, sin cambios locales,
73 GB libres; backend, frontend, Nginx, Redis, Ollama y WhatsApp Gateway saludables;
Celery worker y beat en ejecución. Compose necesita `--env-file .env.prod`,
validado sin imprimir valores privados. No se fusionó ni desplegó esta modificación.

El PR #4 previo continúa abierto, en borrador y sin revisiones. Fusionar dev tal
como está también publicaría sus cambios anteriores de frontend, plantillas,
adjuntos, gateway y migraciones 0015/0016. Resolver ese alcance antes del despliegue,
según la restricción de esta solicitud de modificar únicamente el chatbot.

Una vez revisado el alcance y fusionado el PR: registrar commit e imágenes,
respaldar PostgreSQL y media con verificación, hacer pull de main, validar Compose
con el entorno privado, construir y recrear únicamente los servicios afectados.
No se puede tratar el PR anterior completo como si solo requiriera reiniciar Celery.
Para este cambio aislado bastan backend, workers y beat; no necesita nuevas
migraciones, cambios de modelo Ollama, ni reinicios de PostgreSQL, media o gateway.

Rollback del comportamiento: activar la bandera y recrear backend/workers.
Rollback del código: desplegar una versión revisada anterior o un commit de
reversión, conservando base y archivos. No usar reset de datos, flush, down -v
ni eliminar volúmenes. La prueba real posdespliegue requiere conversaciones
de prueba autorizadas y comprobación de restricciones de cada canal.
