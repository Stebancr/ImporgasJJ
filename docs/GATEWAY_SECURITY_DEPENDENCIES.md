# Auditoría de dependencias del gateway — 2026-11-23

Base: origin/dev 4cc209fc. Rama independiente de autenticación y PR #15.

`npm ci` y `npm audit --json` iniciales: 12 hallazgos (4 moderados, 6 altos, 2 críticos); solo dependencias productivas: 7 (3 moderados, 4 altos). Se conserva npm y el lockfile; no se ejecuta audit fix --force ni se desactivan controles.

Cambios directos: Zod 4.1.11 → 4.6.7 (misma versión mayor) y Vitest 3.2.7 → 5.1.1 (herramienta de desarrollo, salto mayor necesario para corregir los avisos críticos). Vitest 5 requiere Node ^22.12.0, ^24 o >=26. El gateway se construye y prueba con Node 22 compatible; no se modifica la API del servicio. La versión de Baileys 7.0.0-rc14, Axios 1.20.0, Express 5.1.0 y TypeScript 5.9.2 se conserva.

Actualizaciones transitivas limitadas a los paquetes afectados y su cohorte de herramientas de prueba: body-parser, follow-redirects, ip-address, music-metadata, qs, sharp, source-map-js y Vite. Se respetan los rangos admitidos por sus paquetes padre; no se agregan overrides para forzar versiones incompatibles. Vite 8.3.8 es una dependencia de Vitest compatible con su peer dependency oficial; no cambia el Vite del frontend.

| Paquete afectado | Ámbito | Severidad inicial | Uso / resolución |
|---|---|---|---|
| Zod | Producción, directo | Alta | Validación de configuración, corregido 4.6.7 |
| follow-redirects | Producción, transitivo Axios | Alta | Transporte HTTP, corregido 1.16.3 |
| body-parser | Producción, transitivo Express | Alta | Parser HTTP, corregido 2.4.0 |
| sharp | Producción, transitivo Baileys | Alta | Procesamiento de imágenes, corregido 0.35.5 |
| ip-address | Producción, transitivo | Moderada | Dependencias de red, actualizada dentro de rango permitido |
| music-metadata | Producción, transitivo Baileys | Moderada | Adjuntos multimedia, actualizada dentro de rango permitido |
| qs | Producción, transitivo Express | Moderada | Parseo de consultas, actualizada dentro de rango permitido |
| Vitest | Desarrollo, directo | Crítica | Runner, corregido 5.1.1 |
| tinypool | Desarrollo, transitivo | Crítica | Runner anterior sustituido por la cohorte nueva de Vitest |
| @vitest/mocker | Desarrollo, transitivo | Moderada | Mocking, actualizado con Vitest |
| Vite | Desarrollo, transitivo Vitest | Alta | Herramienta de pruebas, corregido 8.3.8 |
| source-map-js | Desarrollo, transitivo | Alta | Mapas de código, actualización transitiva permitida |

Validación Docker: instalación limpia reproducible, **npm audit 0 en todas las severidades**, 40 pruebas aprobadas y TypeScript/build aprobado. Se prueban eventos de conexión y reconexión, persistencia de credenciales sintéticas, reinicio solicitado por Baileys, mensajes entrantes/salientes y adjuntos simulados, cola, idempotencia, logout y conservación de sesión inválida para diagnóstico. No se conectó una cuenta real ni se enviaron mensajes a proveedores.

La revocación global y Socket.IO versionado pertenecen al PR de autenticación. Deben probarse nuevamente al combinar ambas ramas; esta rama no pretende corregir por sí sola ese mecanismo.

CI: se habilita el mismo workflow para PR hacia dev y se añade audit al job del gateway, manteniendo los controles existentes. No se habilitan conexiones a clientes. Antes de producción, revisar todos los checks y las pruebas de integración con la rama de autenticación.

Rollback: restaurar únicamente los dos manifiestos del commit anterior en una rama correctiva y reconstruir una imagen aislada. Eso reintroduciría avisos conocidos y no debe promoverse a producción sin revisión. No borrar el directorio de autenticación Baileys ni volúmenes; nunca revertir la revocación de sesiones para solucionar una dependencia.

Validación adicional en node:22-bookworm-slim (base del Dockerfile): transformación PNG→JPEG con Sharp/libvips y generación QR sintética aprobadas, sin conectar una cuenta WhatsApp. Las 40 pruebas y el build pasan con audit 0.
