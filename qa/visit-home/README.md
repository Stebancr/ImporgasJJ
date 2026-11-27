# Fichas de clientes y portada de productos

La ficha y la copia de cada visita reutilizan el modelo ClienteVisita. La copia continúa en VisitaTecnica.cliente. La ficha opcional queda en VisitaTecnica.cliente_registrado y permite consultar el historial sin cambiar los datos de ningún PDF. La migración AppVisits.0012 agrega tres campos opcionales y sus restricciones. No modifica ni vincula filas históricas. Las integraciones anteriores pueden seguir enviando los datos de una visita sin ficha.

En Nueva visita, busca por nombre, teléfono o correo y selecciona la ficha correcta. Puedes usar una dirección e indicaciones distintas para la visita. Para registrar un cliente, selecciona Registrar cliente nuevo y guarda la visita. Son escrituras atómicas y no crean una cuenta de acceso. La ficha se puede consultar y editar desde el selector. Solo tienen acceso los administradores que ya pueden crear visitas. Los técnicos siguen recibiendo la copia de las visitas asignadas.

Las fichas tienen dos claves únicas. El correo se compara sin espacios exteriores ni distinción de mayúsculas. El teléfono conserva sus dígitos y unifica números colombianos de diez dígitos con prefijos 57 y 0057. La búsqueda y la edición de fichas admiten separadores comunes. El formulario de visitas mantiene su validación de teléfono numérico. Si cualquiera de las claves coincide, se muestran las fichas para revisión y se requiere una selección explícita, incluso si ambas claves apuntan a la misma ficha. Las restricciones de la base cubren solicitudes concurrentes. Los datos anteriores a esta función siguen siendo copias de visitas, no fichas de un directorio retrospectivo.

La portada muestra hasta cuatro productos publicados según is_available y con stock positivo. El orden existente da prioridad a los productos marcados como destacados, seguido por los más recientes. Conserva las tarjetas del catálogo y sus datos reales, un enlace al catálogo completo, categorías y servicios. El filtro de stock es opcional y el resto del catálogo conserva su comportamiento, incluidos los productos disponibles para pedido.

## Verificación en Docker

- En PostgreSQL aislado, revisar el plan antes de migrar. Ejecutar Django check, makemigrations --check --dry-run, migrate --plan y la suite completa con el backend de correo en memoria, servicios externos desactivados y datos sintéticos.
- En Node 20, ejecutar npm ci, npx tsc --noEmit, npm run lint y npm run build.
- Los guiones de este directorio usan Playwright 1.58.2 instalado dentro del contenedor de Chromium correspondiente. Un contenedor de Node llamado visit-home-ui-qa sirve ambas versiones, base en 3000 y propuesta en 3001, y comparte red con Chromium. Copiar los guiones al directorio que contiene node_modules de Playwright dentro de Chromium. Ejecutar node home.cjs before, node home.cjs after y node contacts.cjs. Las imágenes de evidencia se generan en /qa con catálogo y usuarios sintéticos. Las rutas externas se bloquean. Las escrituras y los permisos reales se comprueban en la suite Django.

Si se revierte el código, conservar la migración aplicada y sus datos. El código anterior sigue leyendo las copias de visita. Revertir físicamente la migración eliminaría los vínculos y las claves de fichas creadas, por lo que no es necesario para volver a la portada o al formulario anterior.
