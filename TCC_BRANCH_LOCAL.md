> Documento histórico recuperado de 749ccf56. La migración 0017_resume_provider_address está sustituida por 0019_restore_provider_address en esta recuperación. Consulta RECOVERY_COMPLETENESS_REPORT.md para el estado vigente.

# Integración TCC preservada localmente

Esta rama `codex/dev-tcc` parte de `d8c6d067`, que guarda el código completo de `dev` y los cambios legítimos sin commit existentes al iniciar la separación. No contiene archivos privados de entorno, sesiones WhatsApp, datos de clientes ni artefactos compilados nuevos.

Se conservan cliente HTTP, contratos disponibles, catálogo del proveedor, perfiles de productos, cotización, instantáneas, integración de checkout/Wompi, guías posteriores al pago, reintentos, tareas, UI, pruebas y documentación. Seguimiento por API sigue pendiente del contrato del proveedor; se conserva su documentación y enlace web, sin inventar un contrato.

Las operaciones productivas requieren las protecciones ya existentes y permanecen desactivadas por defecto. Los ejemplos no incluyen tokens. Para iniciar el desarrollo no se requieren credenciales productivas. Las verificaciones de esta separación utilizaron contratos sandbox simulados, sin cotizaciones externas ni despachos reales.

## Compatibilidad

- Ediciones de productos históricos sin cambios logísticos no exigen completar el perfil.
- Pruebas del checkout anterior desactivan explícitamente el proveedor para no depender del entorno privado.
- `ecommerce.0017_resume_provider_address` permite volver desde una base creada con `dev`: agrega el código de dirección únicamente si la columna no existe. No borra columnas ni modifica códigos históricos. No requiere migraciones falsas.
- La secuencia `shipping.0001`–`0003` queda íntegra.

## Verificación Docker

307 pruebas: `shipping ecommerce crmChat transactional_mail AppVisits gestion usuarios.test_account usuarios.test_terms`.
`makemigrations --check --dry-run`: sin cambios pendientes de modelos.
TypeScript, Vite e imágenes backend/frontend construidos localmente.
Ensayos PostgreSQL: TCC → dev → TCC conserva producto, stock, perfil y códigos; una base nueva de dev puede migrar nuevamente a esta rama.

Esta rama está seleccionada en el worktree local `.artifacts/dev-tcc-preserved`. El checkout principal permanece en `dev`. Ningún commit de esta separación se publica ni se despliega.
