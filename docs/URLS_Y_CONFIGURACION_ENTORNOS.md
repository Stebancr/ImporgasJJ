# URLs y configuración de entornos

Esta guía describe la configuración **del repositorio en `dev`**, no certifica el estado del servidor. Los Compose de desarrollo y producción son independientes. No copiar archivos de entorno entre ellos.

## Origen público y rutas

DEV usa Nginx en `http://localhost` (también `http://localhost:81`). PROD tiene `https://djsolutions.io` configurado como entrada HTTPS en las etiquetas de Traefik; Nginx también acepta `imporgasjj.com`, `www.imporgasjj.com`, `www.djsolutions.io`, subdominios de `djsolutions.io` y `2.25.225.216`. La publicación HTTPS efectiva de esos otros hosts depende del proxy y DNS externos y no puede deducirse del repositorio. El ejemplo de configuración Meta PROD usa `https://djsolutions.io`.

| Servicio | DEV | PROD configurado |
| --- | --- | --- |
| Ecommerce | `http://localhost/` | `https://djsolutions.io/` |
| Admin React | `http://localhost/admin/login` | `https://djsolutions.io/admin/login` |
| API | `http://localhost/api/` | `https://djsolutions.io/api/` |
| Django admin | `http://localhost/api/admin/` | `https://djsolutions.io/api/admin/` |
| Chatbot del ecommerce | `http://localhost/api/crm-chat/bot/chat/` | `https://djsolutions.io/api/crm-chat/bot/chat/` |
| Sesiones CRM | `http://localhost/api/crm-chat/sessions/` | `https://djsolutions.io/api/crm-chat/sessions/` |
| Mensajes CRM | `http://localhost/api/crm-chat/sessions/<id>/messages/` | `https://djsolutions.io/api/crm-chat/sessions/<id>/messages/` |
| Media | `http://localhost/media/` | `https://djsolutions.io/media/` |
| Login | `http://localhost/login` | `https://djsolutions.io/login` |
| Registro | `http://localhost/login?mode=register` | `https://djsolutions.io/login?mode=register` |
| Recuperar contraseña | `http://localhost/login` (opción en pantalla) | `https://djsolutions.io/login` (opción en pantalla) |
| Checkout | `http://localhost/checkout` | `https://djsolutions.io/checkout` |
| Rastreo de pedido | `http://localhost/seguimiento` | `https://djsolutions.io/seguimiento` |
| Meta Login (inicio OAuth) | `http://localhost/api/meta/connect/` | `https://djsolutions.io/api/meta/connect/` |
| Meta Callback | valor de `META_REDIRECT_URI` en `.envdev`: túnel DEV + `/api/meta/callback/` | `https://djsolutions.io/api/meta/callback/` en `.env.prod.example` |
| Meta Webhook unificado | túnel DEV + `/api/meta/webhook/` | `https://djsolutions.io/api/meta/webhook/` |
| WhatsApp Webhook | túnel DEV + `/api/meta/whatsapp/webhook/` | `https://djsolutions.io/api/meta/whatsapp/webhook/` |
| Instagram/Facebook Webhook | túnel DEV + `/api/meta/instagram/webhook/` y `/api/meta/facebook/webhook/` | `https://djsolutions.io/api/meta/instagram/webhook/` y `/api/meta/facebook/webhook/` |
| Instagram OAuth Callback | `INSTAGRAM_OAUTH_REDIRECT_URI` en `.envdev`: túnel DEV + `/api/meta/instagram/oauth/callback/` | `https://djsolutions.io/api/meta/instagram/oauth/callback/` en `.env.prod.example` |
| Wompi API | `https://sandbox.wompi.co/v1` | `https://production.wompi.co/v1` en `.env.prod.example` |
| Wompi webhook | túnel DEV + `/api/webhooks/wompi` | `https://djsolutions.io/api/webhooks/wompi` |

El túnel DEV está definido en `.envdev` mediante `META_REDIRECT_URI` e `INSTAGRAM_OAUTH_REDIRECT_URI`; puede caducar y debe actualizarse allí y en Meta. El túnel tiene que reenviar a Nginx DEV o a Django con su alias `/api/meta/`. No registrar la URL PROD en una aplicación Meta DEV. Los webhooks de Meta no usan OAuth para cada POST: GET compara `META_WEBHOOK_VERIFY_TOKEN`; POST valida `X-Hub-Signature-256` con el App Secret. Un POST 401 significa firma ausente o inválida en la implementación actual; no se debe quitar esa validación. Nginx elimina `/api/` al enviar al backend, que también dispone de alias `/api/meta/` para túneles que conservan el prefijo.

## Puertos y redes

| Servicio | DEV | PROD | Alcance |
| --- | ---: | ---: | --- |
| Frontend y admin React | 3000 | 80 | DEV enlazado a `127.0.0.1`; PROD solo red Docker |
| Nginx aplicación | 80 y 81 | 81 del host → 80 del contenedor | DEV enlazado a `127.0.0.1`; PROD publicado también mediante Traefik HTTPS |
| Backend | 8000 | 8001 | DEV enlazado a `127.0.0.1`; PROD interno |
| PostgreSQL | 5432 | 5432 | DEV enlazado a `127.0.0.1`; PROD interno |
| Ollama | 11434 | 11434 | DEV enlazado a `127.0.0.1`; PROD interno; backend usa `http://ollama:11434/api/chat` |
| Redis | 6379 | 6379 | Solo red Docker |
| Media | 8001 → 80 | 80 | DEV enlazado a `127.0.0.1`; PROD interno vía Nginx |
| Mailpit DEV | 8025 web; 1025 SMTP | no presente | DEV enlazado a `127.0.0.1` |

Los números internos provienen de `docker-compose.dev.yml`, `docker-compose.data.yml`, `docker-compose.prod.yml` y `docker-compose.prodData.yml`. El puerto HTTPS externo de Traefik depende de su instalación, fuera de estos Compose.

**Estado del contenedor DEV existente:** el archivo `docker-compose.data.yml` ya limita PostgreSQL a `127.0.0.1:5432`, pero el contenedor `postgres` que estaba en ejecución antes de este cambio conserva su enlace anterior a todas las interfaces. Se intentó aplicar el nuevo enlace conservando el volumen `frontend_postgres_data`; Docker Compose quiso reemplazar la red `frontend_shared_net`, todavía usada por backend, Celery y SMTP. Se restauró el mismo contenedor y se verificó una consulta a la base. Para aplicar el enlace nuevo hay que coordinar una ventana de reinicio de todos los servicios que comparten esa red, sin eliminar `frontend_postgres_data`. No ejecutar `down -v` ni `--remove-orphans`.

## Bases de datos

**DEV:** iniciar primero `docker compose -f docker-compose.data.yml up -d` y luego `docker compose -f docker-compose.dev.yml up -d`. Servicio `postgres`, host Docker `postgres`, puerto 5432, base `imporgas_db`. El Compose de datos declara `POSTGRES_USER=ImporgasJJ` y toma `POSTGRES_PASSWORD` del `.env` local; Django usa `DB_USER` y `DB_PASSWORD` de `.envdev`, alineados con la instalación local existente. Estas dos contraseñas son variables distintas y no deben sustituirse una por otra. Para abrir `psql` dentro del contenedor: `docker compose -f docker-compose.data.yml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`. Si el rol indicado por `DB_USER` de Django es distinto, usar ese rol solo cuando exista en la base actual. Para un cliente del host, usar `127.0.0.1:5432`, la base `imporgas_db` y un rol válido. Obtener las credenciales del archivo local protegido; no copiarlas a documentación.

**PROD:** iniciar primero `docker compose --env-file .env.prod -f docker-compose.prodData.yml up -d` y después el Compose de aplicación. Servicio `postgres` (`imporgas-prod-postgres`), host interno `postgres`, puerto interno 5432. La base y el usuario son `POSTGRES_DB`/`POSTGRES_USER` del archivo seguro del servidor; `.env.prod.example` deja el usuario sin valor y propone `imporgas_db` como nombre. Acceso desde el servidor: `docker compose --env-file .env.prod -f docker-compose.prodData.yml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`. No hay puerto PostgreSQL publicado en PROD. `DB_NAME`/`DB_USER`/`DB_PASSWORD` de Django deben corresponder a la base existente. **Ninguno de estos comandos crea ni reinicializa la base.**

## Variables por entorno

| Variable real | DEV | PROD |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `core.settings` (predeterminado) | `core.settings_production` (Compose) |
| `DEBUG` | habilitado en `.envdev` | `False` forzado por Compose |
| `ALLOWED_HOSTS` | localhost, servicios Docker y host del túnel en `.envdev` | lista explícita en `settings_production.py` |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | orígenes locales con esquema | HTTPS explícitos en `settings_production.py`; CSRF admite `https://*.djsolutions.io` |
| `VITE_API_URL` | `/api` | `/api` en el build de PROD |
| `VITE_WOMPI_PUBLIC_KEY`, `WOMPI_PUBLIC_KEY` | llaves públicas de prueba | llave pública de producción; la privada nunca se pasa a Vite |
| `WOMPI_API_URL` | sandbox explícito en Compose | producción en `.env.prod.example` |
| `META_REDIRECT_URI`, `INSTAGRAM_OAUTH_REDIRECT_URI` | HTTPS del túnel DEV | HTTPS del dominio registrado en Meta PROD |
| `META_OAUTH_FRONTEND_REDIRECT` | admin DEV | ruta relativa `/admin/chat/integraciones` recomendada |
| `META_APP_ID`, `META_APP_SECRET`, `META_WEBHOOK_VERIFY_TOKEN` | credenciales Meta DEV | credenciales Meta PROD; no intercambiarlas |
| `OLLAMA_API_URL` | `http://ollama:11434/api/chat` | `http://ollama:11434/api/chat` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | acceso Django a la base DEV | acceso Django a la base PROD |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | inicialización del servicio DEV; solo `POSTGRES_PASSWORD` viene de `.env` | inicialización del servicio PROD desde `.env.prod` |

El frontend construye llamadas a la API con `VITE_API_URL=/api`, por lo que usa el host desde el que se abrió. Las URLs para compartir productos usan `window.location.origin`. Las direcciones de Meta Graph, Instagram y del checkout alojado de Wompi son endpoints externos del proveedor, no orígenes de la aplicación. La estructura antigua `BACKEND/core/config/dev.py` no es el módulo de settings seleccionado por estos Compose; `nginx/nginx.prod.conf` es una configuración antigua y tampoco está montada en el Compose PROD activo.

En DEV se corrigió la carga accidental de `.env` por el backend y Celery: ahora leen `.envdev`. El archivo `.envdev` local debe contener únicamente las llaves Wompi de prueba, la contraseña de la **base DEV existente** y callbacks al túnel DEV. El ejemplo PROD es una plantilla; verificar los valores reales de `.env.prod` en el servidor antes de desplegar. El repositorio no permite comprobar que Meta haya registrado las URLs correctas o que el proxy público enrute `imporgasjj.com`.

**Separación Meta aún pendiente de credenciales externas:** al auditar los archivos locales, `.env` y `.envdev` tenían el mismo `META_APP_ID` y `META_APP_SECRET`. El callback DEV ya usa el túnel DEV, pero esto no equivale a dos aplicaciones Meta independientes. Configurar un App ID, App Secret y token de verificación exclusivos para DEV en `.envdev` y registrar sus callbacks/webhooks en esa aplicación; conservar los secretos PROD en el servidor. No se cambiaron tokens ni se publican sus valores aquí. Comprobar también que el túnel siga activo y que el token registrado en Meta coincida exactamente con el que recibe Django.

## Dominios y seguridad

`ALLOWED_HOSTS` PROD acepta `imporgasjj.com`, `www.imporgasjj.com`, `.djsolutions.io`, `djsolutions.io`, `www.djsolutions.io` y `2.25.225.216`. CORS permite únicamente los orígenes HTTPS de los dominios web configurados; CSRF exige esquema HTTPS. La IP está en `ALLOWED_HOSTS` para las solicitudes directas previstas, no se añade a CORS/CSRF sin una interfaz HTTPS válida en esa IP. No se usa `*` en `ALLOWED_HOSTS` ni CORS. Ollama, PostgreSQL y Redis no tienen puertos publicados en PROD.

El pago contra entrega propio del ecommerce está deshabilitado en el backend y oculto en React. El método de efectivo en corresponsal **dentro del widget alojado de Wompi** (`BANCOLOMBIA_COLLECT`, distinto de `BANCOLOMBIA_TRANSFER`) depende de la cuenta comercial y **no está confirmado como desactivado**. No hay parámetro verificado para ocultar solo ese medio en el widget actual. Se requiere desactivarlo en la cuenta de Wompi y comprobar el widget; véase [WOMPI_CORRESPONSAL.md](WOMPI_CORRESPONSAL.md). El backend acepta únicamente `wompi` o `cash` como tipo de checkout y rechaza `cash` mientras esté deshabilitado; tampoco acepta un valor de corresponsal manipulado. No rechazar pagos ya aprobados en el webhook.

Este documento no contiene contraseñas, tokens, secretos, claves privadas de Wompi ni `META_APP_SECRET`.
