# Sede Cali Norte y categorías del catálogo

La API pública devolvió la sede SEDE CALI NORTE con el número 30N-42. La ficha de Google Maps compartida por el negocio corresponde a ImporGas JJ | Cali Norte, Av. 6 Norte #30N-46, San Vicente, Cali, Valle del Cauca. Rinnai confirma el número y el piso 1. Waze confirma el barrio y el teléfono 321 654 6064. El código postal queda sin verificar.

- [Ficha de Google Maps](https://www.google.com/maps/dir/?api=1&destination=3.4718433%2C-76.5266492&destination_place_id=ChIJXf6b2uupMI4RNN6J4-rm_jo)
- [Waze](https://www.waze.com/es/live-map/directions/co/valle-del-cauca/cali/imporgas-jj-or-cali-norte?to=place.ChIJXf6b2uupMI4RNN6J4-rm_jo)
- [Rinnai Colombia](https://rinnai.co/donde-comprar-colombia/)

Google devolvió el registro 0x8e30a9ebda9bfe5d:0x3afee6eae389de34 con el punto 3.4718433, -76.5266492. El mapa usa coordenadas cuando no hay clave. Con VITE_GOOGLE_MAPS_EMBED_KEY en el entorno de compilación usa el ID con Maps Embed API. Restringir la clave pública al dominio y a Maps Embed API. El enlace de indicaciones sigue disponible si falla el iframe. El navegador no puede inspeccionar los errores que Google muestra dentro de un iframe de otro origen.

La migración 0022 agrega Electricidad (rayo), Medidor de gas (temporizador), Manómetro (indicador de presión), Regulador de gas (controles), Latón (conexión), Galvanizado (pieza industrial) y Tanque de acumulación (cilindro). Lucide conserva el estilo existente. Los equivalentes con acentos, mayúsculas o plurales conservan su ID, slug y relaciones. La categoría histórica que combina medidores y reguladores conserva su agrupación.

La migración 0023 identifica la sede Norte existente en Cali, incluyendo el nombre observado en producción. Conserva horarios y teléfonos y no modifica stock ni la sede Sur. Si coinciden dos sedes, falla antes de actualizar.

## Despliegue y recuperación

Tras aprobar el PR, registrar el commit productivo y las imágenes actuales. Verificar rama limpia, tomar respaldo lógico fuera del repositorio y verificarlo con pg_restore --list. Registrar la fila Norte y las categorías previas. Hacer pull --ff-only del commit aprobado. Revisar migrate --plan, construir las imágenes de backend y frontend y aplicar migrate --noinput de forma controlada. Verificar /api/locations, catálogo, administración, contacto, inicio y healthchecks. Conservar los volúmenes y media.

Para recuperar servicio se pueden volver a usar las imágenes anteriores, dejando las columnas y categorías aditivas. Las operaciones de datos inversas conservan categorías que ya puedan tener productos y la dirección validada. Para revertir la dirección, usar la fila respaldada mediante una corrección puntual. Mantener el esquema nuevo mientras el backend nuevo esté activo.
