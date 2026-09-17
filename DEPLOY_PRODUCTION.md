# Despliegue de producción de IMPORGAS JJ

La infraestructura se divide en `docker-compose.prodData.yml` (PostgreSQL y media) y
`docker-compose.prod.yml` (aplicación). Ambos usan la red externa
`imporgas_prod_network`. Nginx publica `81:80`: 81 es el puerto del host y 80 el
del contenedor. Django conserva el puerto interno 8001.

El dominio activo solicitado es `https://djsolutions.io`. El proxy existente de
Coolify/Traefik conserva 80/443 y termina HTTPS; únicamente Nginx se conecta
también a la red externa `coolify`. Los routers `imporgas-*` tienen prioridad
100 para dirigir ese dominio al proyecto. Esto sustituye la ruta del panel de
Coolify en ese dominio; el servicio administrativo conserva su puerto 8000.

El 16/09/2026 el DNS de djsolutions.io apuntaba a 2.57.91.91 (página aparcada de
Hostinger), mientras el VPS es 2.25.225.216. Su certificado público estaba en el
proveedor, no en el VPS. Hay que corregir DNS y suministrar el certificado
existente al proxy, o autorizar expresamente su emisión. Las etiquetas del
proyecto no configuran un certresolver ni solicitan certificados nuevos.
No debe eliminarse la validación TLS para dar por aprobada una prueba HTTPS.

Pruebas directas: `http://2.25.225.216:81/` y `/admin/`. Django mantiene la
redirección HTTPS: la API autenticada requiere completar DNS/SSL. Para probar
el enrutamiento interno desde el servidor se puede enviar `Host: djsolutions.io`
y `X-Forwarded-Proto: https` al puerto 81; esto no valida el certificado público.

## 1. Requisitos

- Servidor Linux con Docker Engine y Docker Compose v2.
- Registro DNS `A` de `djsolutions.io` hacia `2.25.225.216`.
- Puertos TCP 80 y 443 permitidos en el firewall.
- Recursos para PostgreSQL, Django, Celery y `qwen2.5:1.5b` de Ollama.
- Credenciales reales de PostgreSQL, SMTP, Wompi y Meta en el servidor.

## 2. Respaldar el origen

Ejecutar desde la raíz del proyecto. Estos comandos sólo leen los datos.

```bash
mkdir -p "backups/$(date +%F-%H%M%S)"
BACKUP_DIR="$(find backups -mindepth 1 -maxdepth 1 -type d | sort | tail -1)"

docker exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$BACKUP_DIR/postgres.dump"
docker run --rm -v media_data:/source:ro -v "$PWD/$BACKUP_DIR:/backup" alpine \
  sh -c 'cd /source && tar -czf /backup/media.tar.gz .'
cp .env "$BACKUP_DIR/env.backup"
chmod 600 "$BACKUP_DIR/env.backup"
git bundle create "$BACKUP_DIR/repository.bundle" --all

pg_restore --list "$BACKUP_DIR/postgres.dump" >/dev/null
tar -tzf "$BACKUP_DIR/media.tar.gz" >/dev/null
test -s "$BACKUP_DIR/repository.bundle"
```

Si el volumen de media no se llama `media_data`, obtener su nombre real con:

```bash
docker inspect backend --format '{{range .Mounts}}{{if eq .Destination "/app/media"}}{{.Name}}{{end}}{{end}}'
```

Guardar una copia cifrada de `.env.prod`, los respaldos y `/etc/letsencrypt`
fuera del VPS. No almacenar secretos en Git.

## 3. Variables, red y volúmenes

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Completar en `.env.prod`:

- `SECRET_KEY` con un valor nuevo y largo.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_USER` y `DB_PASSWORD`. Los dos pares
  deben coincidir.
- Las llaves de producción de Wompi. `VITE_WOMPI_PUBLIC_KEY` puede contener
  únicamente la llave pública.
- Credenciales de Meta y tokens de verificación.
- SMTP real. Mailpit no forma parte de producción.
- Firebase sólo si la integración está activa.

Validar los campos mínimos:

```bash
set -a
. ./.env.prod
set +a
test -n "$SECRET_KEY" && test -n "$POSTGRES_USER" && \
  test -n "$POSTGRES_PASSWORD" && test -n "$DB_USER" && test -n "$DB_PASSWORD"
test "$POSTGRES_USER" = "$DB_USER"
test "$POSTGRES_PASSWORD" = "$DB_PASSWORD"
```

Crear recursos externos de forma idempotente:

```bash
docker network inspect imporgas_prod_network >/dev/null 2>&1 || \
  docker network create imporgas_prod_network

for volume in imporgas_prod_postgres_data imporgas_prod_media_data \
  imporgas_prod_static_data imporgas_prod_redis_data imporgas_prod_ollama_data
do
  docker volume inspect "$volume" >/dev/null 2>&1 || docker volume create "$volume"
done
```

No usar `docker compose down -v`, `docker volume rm` ni
`docker system prune --volumes` en este proyecto.

## 4. Certificado HTTPS (proxy existente)

No ejecutar Certbot standalone: Coolify ya ocupa 80/443. Conservar el proxy y
sus certificados. La configuración de Nginx de este proyecto sirve HTTP
interno en 80 y recibe el protocolo original mediante X-Forwarded-Proto.
Nginx sólo acepta ese header desde la subred `172.16.1.0/24` de `coolify`,
verificada en el VPS; si se recrea esa red, comprobar su subred y actualizar
`nginxprod/nginx.conf`. La redirección pública HTTP a HTTPS se realiza en Traefik.

```bash
docker network inspect coolify
curl --fail --head https://djsolutions.io/
```

Comprobar la sintaxis del proxy de la aplicación después de iniciar `prod`,
como se indica en la sección de verificaciones.

## 5. Levantar datos

```bash
docker compose --env-file .env.prod -f docker-compose.prodData.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.prodData.yml pull
docker compose --env-file .env.prod -f docker-compose.prodData.yml up -d
docker compose --env-file .env.prod -f docker-compose.prodData.yml ps
docker exec imporgas-prod-postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker exec imporgas-prod-media wget -qO- http://127.0.0.1/health
```

### Restaurar la base inicial desde el dump del proyecto

`BACKEND/scripts/posgress.sql` es un archivo **custom** de `pg_dump`, no SQL
plano. Se creó con `pg_dump` 17.0 a partir de PostgreSQL 16.13 y contiene 54
tablas con sus entradas de datos. Por ello la restauración usa temporalmente
`pg_restore` 17 contra el servidor PostgreSQL 16. Ejecutarla una sola vez,
después de que `prodData` esté saludable y **antes** de arrancar `prod`.
Comprobar el archivo y confirmar que la base de destino está vacía:

```bash
docker run --rm \
  -v "$PWD/BACKEND/scripts/posgress.sql:/backup/posgress.sql:ro" \
  postgres:17 pg_restore --file=/dev/null /backup/posgress.sql
docker exec imporgas-prod-postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from pg_tables where schemaname = '\''public'\''"'
```

Sólo si el resultado es `0`, restaurar sin cambiar el propietario del dump ni
crear otra base llamada `imporgas_db`. El filtro elimina únicamente
`SET transaction_timeout = 0;`, una instrucción emitida por el cliente 17 que
el servidor 16 no reconoce. La transacción única revierte la restauración si
alguna instrucción falla. Cargar las variables con el shell es necesario porque
`docker run --env-file` conserva las comillas de `.env.prod` de manera distinta
a Compose:

```bash
bash -n .env.prod
set -a
. ./.env.prod
set +a
docker run --rm --network imporgas_prod_network \
  --env POSTGRES_USER --env POSTGRES_PASSWORD --env POSTGRES_DB \
  -v "$PWD/BACKEND/scripts/posgress.sql:/backup/posgress.sql:ro" \
  postgres:17 bash -euo pipefail -c '
    pg_restore --no-owner --no-privileges --file=- /backup/posgress.sql |
    sed "/^SET transaction_timeout = 0;$/d" |
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" -X -v ON_ERROR_STOP=1 --single-transaction >/dev/null
  '

docker exec imporgas-prod-postgres sh -ec '
  tables=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
    "select count(*) from pg_tables where schemaname = '\''public'\''")
  migrations=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
    "select count(*) from django_migrations")
  echo "Tablas: $tables; migraciones registradas: $migrations"
  test "$tables" -ge 54 && test "$migrations" -gt 0
'
```

No repetir la restauración sobre datos que ya estén en uso. Si el volumen ya
contiene tablas, inspeccionar su origen y preservar sus datos antes de decidir
si corresponde restaurar.

## 6. Construir y arrancar la aplicación

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.prod.yml build

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d redis ollama
docker compose --env-file .env.prod -f docker-compose.prod.yml exec ollama \
  ollama pull "${OLLAMA_MODEL:-qwen2.5:1.5b}"

docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm --user root backend \
  sh -c 'chown -R django:django /app/media /app/staticfiles'
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backend \
  python manage.py migrate --plan
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backend \
  python manage.py migrate --noinput
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backend \
  python manage.py collectstatic --noinput

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

El modelo se descarga sólo con el comando explícito anterior. Ollama conserva el
flujo reactivo: no crea campañas, recordatorios ni mensajes proactivos.

Crear un superusuario únicamente si no existe uno válido:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

## 7. Verificaciones

### Infraestructura

```bash
docker compose --env-file .env.prod -f docker-compose.prodData.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
  python manage.py check --deploy
docker compose --env-file .env.prod -f docker-compose.prod.yml exec nginx nginx -t
docker compose --env-file .env.prod -f docker-compose.prod.yml exec redis redis-cli ping
docker compose --env-file .env.prod -f docker-compose.prod.yml exec ollama ollama list
docker compose --env-file .env.prod -f docker-compose.prod.yml exec celery-worker \
  celery -A core inspect ping
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

Para esta aplicación la última salida sólo debe publicar 81. Coolify conserva
los puertos 80 y 443. Los puertos
8001, 5432, 6379 y 11434 deben permanecer privados.

### Sitio, API, admin y media

```bash
curl --fail --head http://djsolutions.io
curl --fail --head https://djsolutions.io/
curl --fail https://djsolutions.io/api/health/
curl --fail --head https://djsolutions.io/admin/
curl --fail --head https://djsolutions.io/admin/login/
curl --fail --head https://djsolutions.io/media/RUTA_DE_UN_ARCHIVO_REAL
```

Abrir `/admin/` en una sesión privada y confirmar la redirección a
`/admin/login`. Después, probar navegación y una operación autorizada.

### Wompi

Configurar en Wompi producción el evento:

```text
https://djsolutions.io/api/webhooks/wompi
```

Realizar una compra controlada de valor mínimo y verificar:

1. El widget usa una llave `pub_prod_*` y `https://production.wompi.co/v1`.
2. Antes de confirmar existe una intención pendiente, sin orden pagada.
3. El webhook firmado llega con estado `APPROVED`.
4. Sólo entonces se crea la orden pagada; un evento repetido no la duplica.

### Meta y chatbot

Registrar las URI aplicables:

```text
https://djsolutions.io/api/meta/callback/
https://djsolutions.io/api/meta/webhook/
https://djsolutions.io/api/meta/whatsapp/webhook/
https://djsolutions.io/api/meta/facebook/webhook/
https://djsolutions.io/api/meta/instagram/webhook/
https://djsolutions.io/api/meta/instagram/oauth/callback/
```

Confirmar el `verify token`, conectar cada canal y enviar un mensaje entrante de
prueba. Debe crearse una sola conversación y una sola respuesta cuando el bot
esté habilitado; debe detenerse cuando un asesor tome el chat. Esta configuración
no agrega plantillas, campañas, marketing, mensajes masivos ni envíos proactivos.

### Email

Ejecutar una función existente que envíe correo y comprobar la entrega con SMTP
real. No configurar `mailpit`, `localhost` ni el puerto 1025 en `.env.prod`.

## 8. Logs, actualización y backups

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 backend nginx
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 celery-worker celery-beat
docker compose --env-file .env.prod -f docker-compose.prodData.yml logs --tail=200 postgres media
```

Actualizar sin eliminar datos:

```bash
git pull --ff-only
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

Crear respaldos periódicos apuntando a `imporgas-prod-postgres` y
`imporgas_prod_media_data`. Validarlos con `pg_restore --list` y `tar -tzf`, y
copiarlos fuera del servidor.
