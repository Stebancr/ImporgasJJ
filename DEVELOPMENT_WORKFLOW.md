# Flujo de desarrollo y despliegue

El código se desarrolla en el PC, en la rama `dev`. El servidor ejecuta versiones revisadas de `main`; no se edita allí el código de la aplicación.

```text
PC, rama dev → commits y push → revisión e integración en main → despliegue en servidor
```

## Trabajo diario en el PC

```bash
git switch dev
git pull --ff-only origin dev
# Editar, revisar y probar usando los contenedores Docker del proyecto.
git add <archivos revisados>
git commit -m "descripción del cambio"
git push origin dev
```

No añadir archivos `.env`, credenciales, volcados de base de datos, archivos multimedia de clientes ni sesiones de WhatsApp. Los respaldos locales y los archivos temporales de recuperación están ignorados por Git.

## Integrar en `main`

Revisar el diff y las pruebas de `dev` antes de integrar. Abrir una solicitud de cambios de `dev` hacia `main` y fusionarla sin reescribir el historial. Si `dev` contiene trabajo todavía no aprobado para producción, crear una rama desde `main` y aplicar solo los commits aprobados mediante `git cherry-pick` antes de la revisión.

## Actualizar `dev` después de publicar cambios en `main`

```bash
git fetch origin
git switch dev
git pull --ff-only origin dev
git merge origin/main
# Resolver y probar cualquier conflicto antes de publicar.
git push origin dev
```

Si el historial permite un avance lineal, usar `git merge --ff-only origin/main`. Nunca forzar el push ni descartar cambios locales para sincronizar.

## Desplegar una versión revisada

En el servidor, confirmar que el árbol Git no tenga cambios de código pendientes. Respaldar PostgreSQL y archivos multimedia y verificar el respaldo antes de un despliegue. Después:

```bash
cd /root/ImporgasJJ
git switch main
git pull --ff-only origin main
docker compose --env-file .env.prod -f docker-compose.prodData.yml -f docker-compose.prod.yml build <servicios modificados>
docker compose --env-file .env.prod -f docker-compose.prodData.yml -f docker-compose.prod.yml up -d --no-deps --wait <servicios modificados>
docker compose --env-file .env.prod -f docker-compose.prodData.yml -f docker-compose.prod.yml ps
```

Ejecutar las migraciones necesarias solo dentro del contenedor backend, después de revisar el plan de migración y el respaldo. Mantener `.env.prod`, volúmenes y datos en el servidor, fuera de Git. Si el servidor contiene cambios de código manuales, incorporarlos y revisarlos en el PC antes del siguiente despliegue.
