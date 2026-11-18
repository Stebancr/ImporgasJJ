# Auditoría de dependencias del frontend

La rama parte de main en fc76b383. En Docker, npm ci con Node 20.20.2 y npm 10.8.2 reprodujo dos avisos altos de producción y tres moderados de desarrollo.

- follow-redirects pasa de 1.16.1 a 1.16.3 dentro del rango ^1.16.0 de Axios 1.20.0. El aviso GHSA-mrwp-f3q8-3g9p afecta el tratamiento de cabeceras sensibles en ciertas redirecciones. El primer parche es 1.16.2. Axios conserva su versión.
- Zod 3.25.76 estaba declarado directamente. El aviso GHSA-mrhx-c7xc-m3w5 afecta el consumo de memoria al validar ciertas colecciones y se corrige desde 4.6.6. Se retiró Zod y @hookform/resolvers 3.10.0 del frontend porque carecen de consumidores en el código, componentes, pruebas y árbol instalado. El gateway WhatsApp es un proyecto npm independiente y conserva su propio Zod.

npm audit --omit=dev pasó con cero vulnerabilidades. La auditoría completa conserva tres avisos moderados en la cadena de desarrollo de ESLint alrededor de minimatch. No se cambió el flujo ni el umbral de auditoría.

Dos instalaciones limpias y builds Docker de Node 20 produjeron los mismos archivos y sumas SHA-256 que main anterior. El candidato pasó lint, TypeScript y cuatro pruebas unitarias de checkout. Se verificó además la combinación temporal con el PR de sedes y categorías, incluidas 508 pruebas de PostgreSQL y la prueba Chromium del mapa y las siete categorías.

El PR solo cambia las declaraciones npm y su lockfile, más este informe. El rollback consiste en volver a la imagen previa del frontend o revertir el commit mediante PR y reconstruir con npm ci. No requiere una migración de base de datos. Un rollback recuperaría las versiones vulnerables, por lo que debe limitarse a una recuperación temporal.
