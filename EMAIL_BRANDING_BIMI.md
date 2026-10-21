# Identidad de correo y preparación BIMI

Auditoría y pruebas: 21 de octubre de 2026, entorno Docker de desarrollo, rama `dev`.

## Dos resultados distintos

- **Logo dentro del correo:** lo controla la aplicación. Compras, visitas finalizadas y recuperación comparten el encabezado y el mismo PNG.
- **Avatar junto al remitente:** lo decide el receptor. El HTML no cambia la fotografía del remitente. BIMI requiere autenticación y política de dominio adecuadas; Gmail exige además VMC o CMC. No existe garantía de visualización universal.

## Recursos y conservación de la marca

| Recurso | Estado |
|---|---|
| `frontend_U/public/logo_imporgas.svg` | Original intacto, 107457 bytes; contiene dos PNG embebidos, máscaras y filtros. No es SVG Tiny PS. |
| `frontend_U/public/email/logo-imporgas.png` | Derivado para correo: 600 × 432 px, 18333 bytes, fondo blanco, colores azul/naranja originales, sin deformación. |
| `BACKEND/transactional_mail/assets/logo-imporgas.png` | Copia binariamente idéntica para envío inline. |
| `frontend_U/public/email/bimi-logo.svg` | Copia específica: 1024 × 1024, 4282 bytes, fondo blanco y trazados vectoriales centrados. No sustituye el original. |

SHA-256 del original: `bc45b3bffe1951da7bb38478f52eb92229ac9d3d4b37bf28c0165b10634897ac`.

El PNG se presenta a 150 × 108 px, con `alt="ImporGas JJ"`. El fondo blanco conserva la legibilidad del azul en clientes claros y oscuros. La copia BIMI conserva los colores `#001475` y `#f58534`, añade `title`, `desc`, `version="1.2"` y `baseProfile="tiny-ps"`. No contiene imágenes raster, referencias externas, fuentes, scripts, animación, máscaras, filtros ni coordenadas x/y en el elemento raíz. Es menor de 32 KiB.

Se validó con **Jing y el esquema oficial SVG Tiny PS**, sin errores. SHA-256 del esquema utilizado: `21aa62ccf4c718c34d816435afec4630981d47490d36b85b96a61529dff82932`. También se renderizó y comparó visualmente con la marca original. Esta validación técnica no sustituye la aprobación gráfica de la empresa ni la revisión del emisor del certificado.

### Reproducir los recursos en Docker

`BACKEND/scripts/build_email_brand_assets.py` usa librsvg, Potrace y Pillow. Puede ejecutarse en una imagen de herramientas derivada de la imagen local del backend con `librsvg2-bin`, `potrace` y `jing` instalados. Estos paquetes son herramientas de generación, no nuevas dependencias de los servicios de correo.

Ejemplo dentro del contenedor, con la fuente montada de solo lectura y las salidas montadas explícitamente:

```sh
python /app/scripts/build_email_brand_assets.py \
  --source /brand-source/logo_imporgas.svg \
  --frontend-output /frontend-output \
  --backend-output /app/transactional_mail/assets \
  --evidence /evidence
jing -c /evidence/svg-ps.rnc /frontend-output/bimi-logo.svg
```

Obtenga el esquema únicamente desde el [recurso oficial](https://bimigroup.org/resources/SVG_PS-latest.rnc.txt). El generador verifica que no cambia el archivo fuente. No use una herramienta de generación contra archivos de producción.

## Configuración y envío

`EMAIL_LOGO_URL` es opcional y está centralizada en Django. Su valor vacío predeterminado utiliza un **Content-ID inline** (`cid:imporgas-logo`), adjuntando el PNG local dentro del MIME del mensaje. Así el logo no requiere publicar recursos ni hacer peticiones a localhost desde el cliente de correo.

Para optar por URL pública, configure una URL HTTPS ya publicada, estable y de un dominio propio declarado en `FRONTEND_PUBLIC_URL` o `EXTERNAL_PRODUCT_URL_TEMPLATE`. Se rechazan HTTP, destinos ajenos, privados, credenciales, parámetros temporales, fragmentos y URLs mal formadas. La configuración inválida utiliza el PNG inline y registra solamente un motivo sanitizado. Si falta incluso el recurso empaquetado, se muestra el nombre de la empresa en texto, sin `<img>` roto.

La aplicación no descarga la URL durante cada envío. Antes de configurarla, el operador debe verificar HTTP 200, `Content-Type: image/png`, acceso anónimo externo, ausencia de redirecciones privadas y que el recurso no expire.

URLs **previstas**, todavía no publicadas por esta tarea:

- `https://www.imporgasjj.com/email/logo-imporgas.png`
- `https://www.imporgasjj.com/email/bimi-logo.svg`

La auditoría pública observó HTTP 200 para el SVG original `/logo_imporgas.svg`, pero los dos recursos nuevos aún no estaban disponibles públicamente. En el Nginx aislado y en el proxy local se verificaron PNG/SVG con HTTP 200 y MIME correcto. Nginx establece caché de un día para `/email/`, permite lectura pública y devuelve 404 real cuando falta un recurso, sin entregar el HTML de la SPA.

No configure las URLs previstas como si ya estuvieran desplegadas. La configuración actual inline no depende de ellas. La accesibilidad pública de BIMI queda pendiente de un despliegue futuro autorizado.

### Qué permanece igual

- Remitente de compras: `ventas@imporgasjj.com`.
- Remitente de visitas: `Servicio Técnico ImporGas JJ <serviciotecnico@imporgasjj.com>`.
- Remitente de recuperación: `ImporGas JJ - No responder <noreply@imporgasjj.com>`.
- SMTP/Brevo, `EMAIL_HOST_USER`, contraseñas, destinatarios, Reply-To, asuntos, contenido funcional, enlaces/PDF, reintentos e idempotencia.
- Plantillas de texto plano: sin cambios y sin HTML del logo.
- Alertas de servidor que se envían en texto plano: sin convertirlas a HTML ni cambiar `SERVER_EMAIL`.

Los dos templates HTML de ejecución heredan `transactional_mail/base.html` e incluyen `transactional_mail/brand_header.html`. El cambio de encabezado se centralizó también en los servicios de envío. Una comparación semántica de las versiones anteriores y actuales confirmó textos y enlaces idénticos en compra, visita y recuperación.

## DNS observado: no equivale a autenticación recibida

Consultas públicas de solo lectura, sin modificaciones DNS:

| Elemento | Resultado observado | Alcance |
|---|---|---|
| SPF de `imporgasjj.com` | `v=spf1 include:zohomail.com ~all` | Autoriza la infraestructura declarada. No demuestra el SPF del Return-Path usado por Brevo. |
| DKIM Brevo selector `brevo1` | CNAME a `b1.imporgasjj-com.dkim.brevo.com`, con clave pública TXT resoluble | Registro publicado, no prueba de la firma de un mensaje recibido. |
| DKIM Brevo selector `brevo2` | CNAME a `b2.imporgasjj-com.dkim.brevo.com`, con clave pública TXT resoluble | Registro publicado; clave disponible. |
| DMARC | `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com` | Modo de observación; no cumple aplicación BIMI. |
| `default._bimi.imporgasjj.com` | NXDOMAIN | No hay registro BIMI publicado. |
| VMC / CMC | La empresa confirmó que no tiene ninguno | Pendiente si se quiere habilitar BIMI en Gmail. |
| Registro de marca | No acreditado en esta auditoría | La empresa debe consultar elegibilidad con el emisor del certificado. |

El SPF del dominio visible no permite concluir por sí solo que Brevo falle: debe examinarse el Envelope From/Return-Path real y la firma DKIM alineada. El usuario no pudo consultar ahora los encabezados recibidos, por lo que **SPF/DKIM/DMARC pass y su alineación siguen sin verificar para los tres remitentes**, aunque el transporte SMTP aceptó las tres pruebas.

Para verificar cada tipo de correo en Gmail, use «Mostrar original» y revise únicamente resultados SPF/DKIM/DMARC, dominio `d=` y Return-Path. No copie enlaces firmados, tokens de recuperación ni el cuerpo completo a logs o documentación.

## BIMI: preparación y pasos pendientes

No se entrega un registro listo para publicar: el recurso nuevo todavía no está disponible en HTTPS público, DMARC continúa en `p=none` y falta certificado. Publicar ahora una URL inexistente no resolvería el avatar.

1. Inventariar **todos** los emisores legítimos, incluidos Zoho y Brevo. Revisar reportes DMARC y comprobar alineación real antes de endurecer la política.
2. Evaluar y corregir SPF/DKIM según los emisores reales. No añadir ni reemplazar registros a ciegas; no publicar varios SPF.
3. Con autorización del administrador, alcanzar DMARC `p=quarantine` o `p=reject`, aplicado al 100 %. No reducir la política ni bloquear emisores legítimos.
4. Aprobar visualmente la copia BIMI con la empresa y consultar VMC/CMC con una autoridad compatible. VMC y CMC tienen requisitos diferentes; no se presupone marca registrada ni emisión garantizada.
5. Publicar el SVG y, cuando exista, el certificado **público** por HTTPS; comprobar desde fuera HTTP 200, MIME y ausencia de autenticación. No guardar claves privadas en Git.
6. Solo entonces preparar y autorizar la publicación del TXT `default._bimi.imporgasjj.com`.

**Sintaxis ilustrativa, no publicable tal cual**:

```text
v=BIMI1; l=<URL_HTTPS_PUBLICA_VERIFICADA_DEL_SVG>; a=<URL_HTTPS_PUBLICA_DEL_CERTIFICADO_EMITIDO>;
```

No existe una URL PEM verificada y no se inventó una. Un registro sin certificado puede tener utilidad en otros receptores, pero no satisface el requisito actual de Gmail; no se presenta como solución para Gmail.

La propagación, caché y decisión del receptor pueden retrasar o impedir el avatar. VMC/CMC no garantizan presentación universal; los distintivos y soporte difieren por proveedor. El destinatario observó la inicial «I» como avatar, no el logotipo. El avatar BIMI **no está implementado ni puede activarse mediante el HTML**.

## Pruebas y evidencias de desarrollo

- 503 pruebas Django ejecutadas y aprobadas en PostgreSQL aislado; 61 pruebas enfocadas de correo/cuentas también aprobadas. Incluyen nuevos casos de logo inline, MIME, URL pública válida, URLs inseguras/mal formadas, recurso ausente, adjuntos y encabezado compartido.
- Comparación antes/después: textos y enlaces idénticos en los tres tipos; archivos de texto plano intactos.
- 12 verificaciones Chromium: tres tipos × móvil/escritorio × claro/oscuro. Imagen cargada de 600 × 432, presentada a 150 × 108, sin desbordamiento horizontal. El modo oscuro de Chromium no emula todas las transformaciones de cada cliente de correo.
- Validación Jing contra esquema oficial: aprobada. PNG del backend y del frontend idénticos; SVG original sin cambios.
- Nginx aislado: 200 PNG/SVG, MIME correcto, caché de un día, lectura pública, 404 para archivo inexistente. Proxy local: 200 para ambos recursos con Host de desarrollo correcto. La imagen local del frontend se construyó con `Dockerfile.prod` y también sirvió ambos recursos con HTTP 200 y MIME correcto, sin montajes de los assets desde el host.
- TLS real previo: Python verifica el certificado; OpenSSL código cero. No se deshabilitó la validación.
- Tres correos controlados, datos sintéticos, sin CC/BCC: compra, visita y recuperación. Brevo los aceptó mediante los servicios reales en un worker exclusivo a las 19:56:40–19:56:42 UTC del 21/10/2026. No hubo pagos, despachos ni clientes reales. No se modificó la contraseña de la cuenta de prueba.
- Recepción real: el destinatario confirmó que llegaron los tres correos. Indicó que el avatar muestra la inicial «I»; esto no es el logo del cuerpo. Después confirmó expresamente que el logo azul y naranja sí se ve dentro del mensaje abierto en Gmail.
- No se registraron credenciales, tokens ni URLs de recuperación en las evidencias compartidas. Las vistas sintéticas usan enlaces sin tokens.

Evidencia privada local en `.artifacts/email-branding/` (no versionar): capturas, validación de esquema, resultados DNS/HTTP/TLS, suite y estados SMTP. No contiene claves privadas. No adjuntar logs completos a un PR.

## Servicios verificados

Backend y los tres servicios Celery se reconstruyeron y recrearon. PNG presente y configuración compartida disponible. API/proxy: HTTP 200; workers: `inspect ping` responde. PostgreSQL y Redis permanecen saludables (`pg_isready` y `PONG`). Nginx valida su configuración; frontend sirve los recursos nuevos. Los contenedores de prueba exclusivos se detuvieron después del envío.

Backend, workers, frontend, Nginx y media no tienen health check declarado: se informa esa ausencia, no se inventa un estado «healthy». Sus verificaciones funcionales y reinicios se comprobaron por separado. Todos los servicios revisados estaban en ejecución con cero reinicios; Mailpit dispone de health check saludable. Una consulta al índice de media devolvió 404, coherente con no exponer listados; no se cambió su almacenamiento.

En los logs recientes de backend/workers/Nginx: cero errores TLS, cero Traceback/CRITICAL, cero 404 del logo y cero patrones de URL de recuperación con token. Las peticiones de diagnóstico con Host interno recibieron 403 de Vite; al utilizar el Host autorizado `localhost`, recursos y página respondieron 200. No se amplió la lista de hosts por esa prueba.

## Prueba controlada futura

Primero ejecute pruebas con el backend local de correo y vistas sintéticas. Para SMTP real: valide TLS estricto, active únicamente el destinatario autorizado en las listas privadas del entorno de desarrollo y use una cola aislada que no consuma mensajes de clientes. Envíe como máximo un mensaje por tipo necesario y compruebe destinatario único, ausencia de CC/BCC, From, HTML y MIME. Si el estado es incierto, revise la entrega antes de reintentar. No versionar direcciones privadas, tokens, logs ni fixtures sensibles.

No repetir los tres envíos de esta auditoría: ya fueron aceptados por Brevo. La recepción de los tres ya fue confirmada. El logo dentro del mensaje también fue confirmado. Quedan pendientes los encabezados reales de autenticación, la aprobación de marca, publicación autorizada de recursos, aplicación DMARC y certificado.

## Referencias oficiales

- [Requisitos BIMI de Google Workspace/Gmail](https://knowledge.workspace.google.com/admin/security/set-up-bimi).
- [BIMI Group: crear SVG Tiny PS](https://bimigroup.org/creating-bimi-svg-logo-files/).
- [BIMI Group: guía de implementación](https://bimigroup.org/implementation-guide/).
- [Esquema oficial SVG PS](https://bimigroup.org/resources/SVG_PS-latest.rnc.txt).

No se modificó DNS, producción, main ni PR; no se hizo push. Los recursos públicos y el avatar quedan preparados para una intervención posterior autorizada, separados del logo inline ya implementado.
