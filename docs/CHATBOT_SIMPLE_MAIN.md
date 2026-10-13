# Simplificación independiente del chatbot

Base: `main` 9808b47b. Rama: `codex/chatbot-simplificado`.
Fecha de verificación: 2026-10-13.

## Alcance

Este cambio puede revisarse e integrarse sin el PR #4. Conserva el frontend,
el contrato síncrono del chat ecommerce, el modelo Ollama, las colas existentes,
los modelos de datos y las integraciones de main. No incorpora plantillas,
adjuntos, cambios del gateway, nuevas tablas ni migraciones del PR #4.
`dev` y su trabajo pendiente se conservan sin reescribir historial.

## Comportamiento

`CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=False` es el valor predeterminado en
Django y Compose, incluido producción. La bandera se comprueba antes de acceder
al catálogo. El flujo anterior permanece intacto en
`OllamaService._get_recommendation_response`.

- Saludo oficial externo una sola vez. En ecommerce se conserva el saludo del frontend.
- Intenciones comerciales claras se transfieren mediante reglas sin consultar
  productos ni Ollama. Incluye precio, disponibilidad, repuestos, reservas,
  instalaciones, recomendaciones, compatibilidad, garantía y asesor.
- Horarios, sedes y teléfonos utilizan únicamente datos de sedes activas existentes.
  Si falta información confirmada, se deriva al asesor.
- Para frases ambiguas, Ollama clasifica una etiqueta JSON con contexto acotado;
  su texto nunca se usa como respuesta comercial. Timeout de conexión 3 s y
  lectura 8 s. Un error o resultado inválido transfiere al asesor.
- La transferencia se persiste y asigna antes del envío externo. Si el envío falla,
  la conversación continúa disponible para el asesor. Reintentos no duplican
  respuesta ni asignación. No hay avisos/cierre automático mientras espera al asesor.
- Se conservan memoria y conversaciones. El historial del flujo simplificado
  excluye mensajes posteriores a la consulta que está procesando.

## Reactivación y rollback

Establecer `CHATBOT_PRODUCT_RECOMMENDATIONS_ENABLED=True` en el entorno privado
que utiliza Compose y recrear backend y worker. No necesita migración:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --no-deps backend celery-worker celery-beat
```

Las conversaciones ya transferidas siguen bajo atención humana; la bandera no
las devuelve automáticamente al bot. Para revertir código, desplegar el commit
anterior revisado o un commit de reversión, conservando datos y volúmenes.

## Validación independiente en Docker

Se montó únicamente el BACKEND de este checkout en contenedores temporales
`docker compose run --rm --no-deps`, sin sustituir los servicios locales de dev.
Se utilizó PostgreSQL en una base de pruebas aislada `test_crm_simple_main` mediante
`CRM_TEST_POSTGRES=1`. El valor solo afecta al comando `manage.py test`.

Comando reproducible desde el proyecto local con su Compose y entorno privados:

```sh
docker compose -f docker-compose.dev.yml run --rm --no-deps -e CRM_TEST_POSTGRES=1 -v RUTA_CHECKOUT/BACKEND:/app:ro backend python manage.py test crmChat --noinput
```

Resultados:

- **140 pruebas CRM aprobadas**, incluidas las pruebas originales con
  recomendaciones activadas, errores de proveedor, cuatro canales con transporte
  simulado, webhook/eco, permisos, contrato ecommerce y preservación de mensajes.
- Ocho sesiones con tareas ejecutadas en paralelo: promedio **0,0980 s**, máximo
  **0,1059 s**, una transferencia por sesión y contextos separados.
- Ocho peticiones al endpoint ecommerce mediante el cliente de pruebas Django:
  promedio **0,0565 s**, máximo **0,0607 s**, respuestas HTTP 200 compatibles con
  el frontend de main, cero duplicados. No incluyen latencia de red pública.
- Dos consultas comerciales simultáneas de una misma sesión: una respuesta,
  una asignación y marcas de procesamiento liberadas.
- `manage.py check`: correcto. `makemigrations --check --dry-run`: sin cambios.
- Sintaxis Compose dev/prod válida con `config --no-env-resolution --no-interpolate --quiet`.

No se probaron envíos a clientes reales. Las mediciones no son un SLA de producción.
Este PR conserva la arquitectura de colas de main; no incluye la recuperación
automática ni la cola dedicada nuevas del PR #4. La suite general de módulos
ajenos no se presenta como aprobada por estas pruebas del CRM.

## Archivos

- `BACKEND/crmChat/simple_chatbot.py`, `ollama_service.py` y `tasks.py`.
- `BACKEND/crmChat/test_simple_chatbot.py` y `tests.py`.
- `BACKEND/core/settings.py`, ejemplos de entorno y Compose dev/prod.
- Este documento. Ningún frontend, modelo, migración, gateway, secreto o dato privado.

## Despliegue posterior a revisión

El PR independiente se entrega sin fusionar ni desplegar. Tras aprobarlo:
registrar commit/imágenes del servidor, comprobar trabajo local, crear y verificar
respaldos de PostgreSQL y media, actualizar main y validar Compose con el entorno
privado. Reconstruir y recrear solo backend, celery-worker y celery-beat.
No requiere reiniciar PostgreSQL, Redis, Ollama, media ni WhatsApp Gateway.
Verificar saludo, transferencia, estados del CRM y servicios; los envíos reales
requieren conversaciones de prueba autorizadas. No eliminar datos ni volúmenes.
