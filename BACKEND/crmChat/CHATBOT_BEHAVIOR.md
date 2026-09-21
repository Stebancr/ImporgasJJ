# Chatbot comercial de IMPORGAS JJ

## Comportamiento

- Se identifica como **asesor comercial virtual de IMPORGAS JJ**.
- Usa el catálogo, marcas, existencias, especificaciones y sedes registradas como fuente comercial.
- Redirige preguntas generales fuera del negocio y no ejecuta órdenes, pagos, cotizaciones ni cambios administrativos.
- La selección concreta de compra, el volumen empresarial o la solicitud de una persona cambia la conversación a `waiting` y detiene las respuestas automáticas.
- Ollama recibe el estado estructurado, el resumen persistente y como máximo los doce mensajes anteriores de la conversación activa.
- Una recomendación general de calentador pregunta progresivamente uso, puntos simultáneos, inmueble, energía, tipo, marca y restricciones. Omite cada dato que ya conoce.
- Los productos se filtran mediante categoría, descripción, marca, modelo, especificaciones, uso, gas, capacidad, stock y compatibilidad. Un producto específico se valida directamente.
- La memoria conserva intención, categoría, producto, selección, productos mostrados, baños, inmueble, uso, gas, capacidad, marca, presupuesto, pregunta pendiente y última respuesta.
- Ecommerce genera `[Ver producto →](URL)` y React muestra sólo el texto navegable. WhatsApp, WhatsApp Web, Facebook e Instagram generan `Ver producto → URL` usando `EXTERNAL_PRODUCT_URL_TEMPLATE`.
- El saludo oficial es: “Muchas gracias por comunicarse con ImporGas JJ, especialistas en Gas y Climatización. Soy el asesor comercial virtual de ImporGas JJ. ¿Cómo podemos ayudarte?”. Los canales externos lo envían al iniciar una conversación; el ecommerce lo muestra una sola vez en React y no lo vuelve a guardar desde el backend.

## Sesiones

- Una sesión cerrada conserva su historial para trazabilidad.
- El ecommerce crea una sesión nueva cuando la anterior está cerrada. WhatsApp Web recupera la última sesión del mismo hilo para conservar el historial sincronizado.
- Sólo puede existir una sesión externa no cerrada por integración y destinatario.

## Mensajería Meta sin costos adicionales

- Los webhooks aceptan tanto `from`/`wa_id` como `from_user_id`/`user_id`.
- WhatsApp, Messenger e Instagram sólo responden a mensajes reales del cliente dentro de la ventana reactiva vigente.
- Las plantillas, campañas, mensajes promocionales y envíos proactivos están deshabilitados. Si la ventana está cerrada, el sistema registra la causa y espera una nueva interacción del cliente.
- Ollama genera como máximo una respuesta por mensaje entrante. Una respuesta fallida no se reenvía automáticamente.
- Los mensajes enviados desde el CRM o el celular se registran como `agent/outbound` y nunca activan Ollama.
- Las sesiones externas inactivas se cierran de forma local y no envían avisos automáticos de cierre.
- Los estados `sent`, `delivered`, `read` y `failed`, junto con los errores de Meta, quedan guardados en el mensaje.
- Los logs incluyen sesión, mensaje, contacto interno, canal, tipo, estado, destino enmascarado, código y detalle del error. Nunca incluyen tokens.

## Entornos y Ollama

- Desarrollo: `FRONTEND_PUBLIC_URL=http://localhost` y `PRODUCT_URL_TEMPLATE=http://localhost/producto/{id}`.
- Producción: `FRONTEND_PUBLIC_URL=https://www.imporgasjj.com` y `PRODUCT_URL_TEMPLATE=https://www.imporgasjj.com/producto/{id}`.
- Canales externos en ambos entornos: `EXTERNAL_PRODUCT_URL_TEMPLATE=https://www.imporgasjj.com/producto/{id}`. Debe ser HTTPS y no acepta hosts locales o internos.
- Modelo: `qwen:4b`, `OLLAMA_NUM_CTX=4096`, `OLLAMA_TIMEOUT=90`, `OLLAMA_NUM_PARALLEL=2` y `OLLAMA_MAX_QUEUE=64`.
- Ollama procesa hasta dos inferencias en paralelo y administra su propia cola. Las conversaciones no comparten un bloqueo global en Django o Redis.

## Verificación

- Suite: `python manage.py test crmChat --noinput`.
- Modelos/migraciones: `python manage.py makemigrations --check --dry-run`.
- Frontend: `npm run build` en `frontend_U`.
