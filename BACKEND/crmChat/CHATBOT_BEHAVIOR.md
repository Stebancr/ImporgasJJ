# Chatbot comercial de IMPORGAS JJ

## Comportamiento

- Se identifica como **asesor comercial virtual de IMPORGAS JJ**.
- Usa el catálogo, marcas, existencias, especificaciones y sedes registradas como fuente comercial.
- Redirige preguntas generales fuera del negocio y no ejecuta órdenes, pagos, cotizaciones ni cambios administrativos.
- La intención de compra, cotización, volumen empresarial o solicitud de una persona cambia la conversación a `waiting` y detiene las respuestas automáticas.
- Ollama recibe el estado estructurado de la sesión y como máximo los ocho mensajes anteriores de la conversación activa.

## Sesiones

- Una sesión cerrada conserva su historial para trazabilidad.
- Un nuevo mensaje del mismo cliente crea otra sesión activa con estado y contexto vacíos.
- Sólo puede existir una sesión externa no cerrada por integración y destinatario.

## Mensajería Meta sin costos adicionales

- Los webhooks aceptan tanto `from`/`wa_id` como `from_user_id`/`user_id`.
- WhatsApp, Messenger e Instagram sólo responden a mensajes reales del cliente dentro de la ventana reactiva vigente.
- Las plantillas, campañas, mensajes promocionales y envíos proactivos están deshabilitados. Si la ventana está cerrada, el sistema registra la causa y espera una nueva interacción del cliente.
- Ollama genera como máximo una respuesta por mensaje entrante. Una respuesta fallida no se reenvía automáticamente.
- Las sesiones externas inactivas se cierran de forma local y no envían avisos automáticos de cierre.
- Los estados `sent`, `delivered`, `read` y `failed`, junto con los errores de Meta, quedan guardados en el mensaje.
- Los logs incluyen sesión, mensaje, contacto interno, canal, tipo, estado, destino enmascarado, código y detalle del error. Nunca incluyen tokens.

## Verificación

- Suite: `python manage.py test crmChat --noinput`.
- Modelos/migraciones: `python manage.py makemigrations --check --dry-run`.
- Frontend: `npm run build` en `frontend_U`.
