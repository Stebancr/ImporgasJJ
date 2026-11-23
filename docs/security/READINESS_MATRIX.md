# Auditoría de ramas y bloqueos — 2026-11-23

Base remota dev: 4cc209fc. Main publicado: 9d1edf49. Corte previo a publicar el PR de autenticación; los JSON preservan las referencias del momento, no un historial reescrito. Inventario: 33 referencias locales/remotas, 16 PR existentes al corte. No se modificaron worktrees ajenos, dev ni main. No se eliminaron ramas.

| Rama / PR | Funcionalidad | Estado | Commits exclusivos al corte | Migraciones | Pruebas / acción |
|---|---|---|---:|---|---|
| security-global-session-revocation | Revocación global | Implementada; revisión pendiente | Backend y realtime en commits separados; ver JSON | usuarios.0010, aditiva | 527 backend, 42 gateway, navegador 3 resoluciones; PR independiente |
| security-gateway-dependencies / #16 | Dependencias del gateway | CI completo verde | 1 | Ninguna | Audit 12→0, 38 tests y build; revisar por separado |
| integration-production-readiness / #15 | Integración de trabajos terminados | Borrador bloqueado | 17 | Categoría icon_key y confirmación de correo de visita | No actualizar ni fusionar hasta revisar seguridad y revocar credenciales |
| improve-category-icons / #14 | 15 iconos de categorías | Ya incluido en #15 | 5 | Ninguna | No duplicar; repetir regresión integrada después de seguridad |
| crm-full-audit | CRM, colas y límites de pruebas | Ya incluido en #15 | 3; base atrasada 8 | Revisadas en #15 | No importar de nuevo toda la rama antigua |
| fix-frontend-audit-dependencies | Auditoría inicial frontend | Ya integrado | 0 | Ninguna | No repetir commits |
| fix-locations-product-categories / #10–11 | Norte y siete categorías | Ya integrado | 0 | Ya publicadas | No repetir datos ni migraciones |
| fix-usuarios-trabajadores / #8 | Administración anterior de usuarios | Reemplazada | 2; base atrasada 44 | Históricas | Excluir; correcciones funcionales posteriores ya publicadas |
| ramas TCC antiguas / #9 | Integración anterior de transporte | Reemplazadas o respaldo | Ver JSON | No reproducir migraciones antiguas | Mantener referencias y excluir código obsoleto |
| tcc-safe-production-rollout | TCC publicado | Ya integrado funcionalmente | 3 sobre base antigua | Ya publicadas | No duplicar |
| chatbot-simplificado | Bot simplificado | Ancestro integrado | 0 | Ninguna nueva | No repetir |
| world-office-inventory | Inventario experimental | Excluido | 7; base atrasada 8 | Incompatibilidades con publicación posterior | Empresa y stock sin contrato verificable; no producción |
| world-office-product-classification | Candidatos World Office | Excluido | 15; base atrasada 8 | En desarrollo aislado | No activar ni importar en esta liberación |
| backup / safety / preserved / reference | Respaldo y conservación | Excluidos de producción | Ver JSON | No aplicar | No borrar ni incorporar automáticamente |

Detalles exactos de SHA, base, ahead/behind, commits y migraciones: branch-inventory.json. Estado de todos los PR al corte: pull-request-inventory.json. Los commits documentales posteriores no están incluidos en esos conteos del corte.

## Módulos

| Módulo | Estado de esta revisión |
|---|---|
| Access/refresh, Django, DRF, Channels, Socket.IO | Corregido y probado localmente; falta liberación revisada |
| Frontend autenticación y múltiples pestañas | Corregido; cierre idempotente, caché privada y respuestas antiguas; responsive validado |
| Gateway transporte | 42 pruebas en seguridad; 38 con nuevas dependencias; combinación requiere regresión antes de integrar |
| Productos, stock, direcciones, checkout, Wompi, TCC | Suite backend completa sin fallos; operaciones de cobro/guías simuladas; no certifica proveedores productivos |
| CRM y plantillas | Regresión de API y transporte incluida en 527; nuevas mejoras preparadas en #15; falta validación conjunta de esa rama con seguridad |
| Chatbot/Ollama | Tests de contexto, concurrencia y caída incluidos; no se declara rendimiento real del modelo |
| Categorías y selector de iconos | Implementados/probados previamente en #15; no forman parte del diff de autenticación; falta regresión integrada |
| Visitas, PDFs y remitente técnico nuevo | Pruebas base incluidas; cambio visual/remitente de #15 pendiente de integración revisada |
| Correos | Backend de pruebas; no se enviaron correos reales en esta intervención |
| Meta y WhatsApp real | Sin envíos ni conexiones de clientes; adaptadores/arnés simulados |
| World Office | Excluido y sin escrituras; no habilitado productivamente |
| PostgreSQL / Redis QA | PostgreSQL saludable y PING Redis correcto; datos aislados |
| Producción | Sin despliegue ni revocación ejecutados; no se extrapola salud QA a producción |

## Hallazgos históricos

historical-findings.json clasifica las 31 detecciones sin valor, firma, token ni datos personales: 5 JWT únicos, 1 JWT duplicado, 10 detecciones de credenciales API, 9 secretos de firma, 2 claves de cifrado y 4 falsos positivos documentados. No se confirmó una contraseña ni una clave privada criptográfica PEM entre estas detecciones. Las claves privadas de API Wompi se clasifican como credenciales API, no como certificados privados.

Cada entrada conserva tipo, primer commit detectado por Gitleaks, snapshots inicial/final por fecha, commits coincidentes, referencias alcanzables, servicio, duplicado textual cuando corresponde, estado y acción. El seguimiento de archivos no garantiza ausencia de otras copias en forks, cachés, reflogs o ubicaciones no detectadas. No se publican las líneas comparadas ni huellas de credenciales.

Los JWT se invalidarán mediante versión global, rechazo de credenciales sin metadata y clave exclusivamente JWT durante la liberación. No se probaron los históricos contra producción. **Todavía no se declaran revocados**.

Los secretos Wompi/Meta requieren revisión de procedencia y revocación/rotación por los responsables. Cambiar la versión global no los invalida. Las claves de cifrado Meta requieren respaldo y recifrado, no sustitución a ciegas. No se utilizó ninguna credencial histórica para probar su vigencia. Los cuatro falsos positivos corresponden a fixtures sintéticos y placeholders de documentación, explicados específicamente; no se excluye todo el historial del escáner.

## Gates antes de producción

1. Revisar los PR independientes, CI y diff; validar conjuntamente los dos cambios de seguridad y después el contenido de #15 sin duplicar commits.
2. Confirmar revocación/rotación de credenciales históricas aplicables con sus responsables. Mantener #15 en borrador hasta resolver el bloqueo. Preparar plan coordinado de saneamiento histórico separado; no force push.
3. Revisar el orden de promoción: el mecanismo nuevo debe estar disponible para ejecutar el corte global. No declarar revocadas las credenciales antes de ese corte ni relajar silenciosamente el gate.
4. Acordar mantenimiento, confirmar reingreso administrativo y respaldos frescos, migraciones e imágenes compatibles con rollback seguro.
5. Desplegar exclusivamente main aprobado, ejecutar corte, verificar rechazo mediante credenciales sintéticas controladas y completar pruebas de humo sin mensajes ni pagos reales.

No hubo merge, despliegue, cambio de .env productivo, rotación de claves reales, ni modificación de contraseñas/permisos/datos personales. Los respaldos generados y las revocaciones ejecutadas aquí corresponden exclusivamente a QA.
