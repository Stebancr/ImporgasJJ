# 🚀 Quick Reference - Sistema de Visitas Técnicas

## 📍 URLs Importantes

| Componente | URL | Acceso |
|------------|-----|--------|
| Backend API | `http://localhost:8000/visits/` | Admin/Técnico |
| Admin Django | `http://localhost:8000/admin/` | Superusuario |
| Frontend Web | `http://localhost/` | Admin (tipo_usuario >= 1) |
| Panel Visitas | `http://localhost/dashboard/visits` | Admin |
| API Docs | `http://localhost:8000/docs/` | Todos |

## 🎯 Comandos Esenciales

### Backend
```bash
# Ver contenedores corriendo
docker ps

# Logs en tiempo real
docker logs -f backend

# Shell de Django
docker exec -it backend python manage.py shell

# Migraciones
docker exec backend python manage.py makemigrations
docker exec backend python manage.py migrate

# System check
docker exec backend python manage.py check
```

### Frontend Web
```bash
cd frontend_S

# Instalar (primera vez)
pnpm install

# Dev server
pnpm run dev

# Build
pnpm run build
```

### App Móvil
```bash
cd "app intagas"

# Instalar (primera vez)
npm install

# Dev server
npm start

# Android Emulator
npm run android

# iOS Simulator (Mac)
npm run ios

# Limpiar cache
npm start -- --clear
```

## 📂 Archivos Clave

### Backend
```
BACKEND/AppVisits/
├── models.py           # 4 modelos
├── serializers.py      # 8 serializadores
├── views.py            # 7 vistas + PDF
├── urls.py             # 9 endpoints
├── permissions.py      # IsAdminOrReadOwn
└── admin.py            # Django admin
```

### Frontend Web
```
frontend_S/src/
├── services/visits.ts          # API client
└── app/pages/VisitsPage.tsx    # Lista + Calendario
```

### App Móvil
```
app intagas/src/
├── api/
│   ├── client.ts               # Axios + JWT
│   └── visits.ts               # Endpoints
├── navigation/index.tsx        # React Navigation
├── screens/
│   ├── LoginScreen.tsx         # Login
│   ├── DashboardScreen.tsx     # Stats
│   ├── VisitsListScreen.tsx    # Lista
│   ├── VisitDetailScreen.tsx   # Detalle
│   ├── VisitFormScreen.tsx     # Wizard 4 pasos
│   ├── CalendarScreen.tsx      # Calendario
│   └── ProfileScreen.tsx       # Perfil
└── store/auth.ts               # Zustand
```

## 🔑 Endpoints API

```
GET    /visits/tecnicos/              # Lista técnicos
GET    /visits/                       # Lista visitas
POST   /visits/                       # Crear visita
GET    /visits/{id}/                  # Detalle
PATCH  /visits/{id}/                  # Editar
DELETE /visits/{id}/                  # Eliminar
POST   /visits/{id}/iniciar/          # Iniciar
POST   /visits/{id}/finalizar/        # Finalizar + reporte
POST   /visits/{id}/fotos/            # Subir fotos
DELETE /visits/{id}/fotos/{foto_id}/  # Eliminar foto
GET    /visits/calendario/?mes=YYYY-MM # Calendario
GET    /visits/{id}/pdf/              # Descargar PDF
```

## 🎨 Estados de Visita

| Estado | Color | Acción Disponible |
|--------|-------|-------------------|
| `pendiente` | 🟡 Amarillo | Iniciar Visita |
| `en_proceso` | 🔵 Azul | Completar Formulario |
| `finalizada` | 🟢 Verde | Descargar PDF |
| `cancelada` | 🔴 Rojo | - |

## 👥 Tipos de Usuario

| tipo_usuario | Rol | Permisos |
|--------------|-----|----------|
| `0` | Técnico/Colaborador | Solo sus visitas, iniciar/finalizar |
| `1` | Admin Sede | CRUD completo, asignar visitas |
| `4` | Super Admin | CRUD completo + configuración |

## 🔐 JWT Tokens

```json
{
  "access": "eyJhbGciOi...",   // 12 horas
  "refresh": "eyJhbGciOi...",  // 1 día
  "is_admin": true,
  "location_id": 1,
  "location_name": "Sede Principal"
}
```

**Almacenamiento Móvil**: `SecureStore`
- `intagas_access` → Access token
- `intagas_refresh` → Refresh token
- `intagas_user` → User data

## 📱 Flujo de Usuario (Técnico)

1. **Login** → JWT tokens
2. **Dashboard** → Ver stats
3. **Visitas** → Lista filtrada
4. **Detalle** → Leer orden
5. **Iniciar** → `pendiente` → `en_proceso`
6. **Formulario** → Wizard 4 pasos:
   - Datos (cliente + equipo)
   - Servicio (motivo + solución)
   - Fotos (min 1, max 20)
   - Firma (canvas)
7. **Finalizar** → `en_proceso` → `finalizada`
8. **Admin descarga PDF**

## 🖼️ Evidencias Fotográficas

- **Máximo**: 20 fotos por visita
- **Formato**: JPEG, PNG
- **Compresión**: Automática (1200px width, 70% quality)
- **Tamaño**: Max 5MB por foto (recomendado)
- **Upload**: Multipart form-data

## ✍️ Firma Digital

- **Tipo**: Canvas signature
- **Formato**: Base64 PNG
- **Envío**: En el endpoint `finalizar`
- **Campo**: `firma_base64` (sin prefijo `data:`)

## 📄 Generación de PDF

**Contenido**:
1. Encabezado (logo + contacto)
2. Cliente (datos completos)
3. Actividad (técnico + orden)
4. Formulario (reporte técnico)
5. Condiciones y garantías
6. Firma del cliente
7. Evidencias fotográficas (grid 3 columnas)

**Librería**: `reportlab`
**Endpoint**: `GET /visits/{id}/pdf/`

## 🐛 Troubleshooting Rápido

### Backend 500
```bash
docker logs backend
# Ver error específico en traceback
```

### Frontend compile error
```bash
cd frontend_S
pnpm run build
# Ver errores TypeScript
```

### Móvil no conecta
```typescript
// Editar src/api/client.ts
export const API_BASE = 'http://192.168.1.XXX:8000'
```

Verificar conexión:
```bash
# Desde PC
ipconfig | Select-String "IPv4"

# Desde móvil (browser)
http://<ip-pc>:8000/visits/
```

### Expo cache issues
```bash
npm start -- --clear
rm -rf node_modules
npm install
```

## 📊 Campos de Reporte

| Campo | Tipo | Requerido |
|-------|------|-----------|
| `persona_atiende` | text | ✅ |
| `equipo` | choice | ✅ |
| `equipo_otro` | text | Si equipo="otro" |
| `ubicacion_equipo` | choice | ✅ |
| `ubicacion_equipo_otro` | text | Si ubicacion="otro" |
| `motivo_servicio` | textarea | ✅ |
| `solucion_realizada` | textarea | ✅ |
| `observaciones` | textarea | ❌ |
| `recomendaciones` | textarea | ❌ |
| `valor_servicio` | decimal | ❌ |
| `metodo_pago` | choice | ❌ |
| `firma_cliente` | image | ✅ |
| `inicio_desplazamiento` | datetime | Auto |
| `duracion_desplazamiento` | int | Auto (minutos) |

## 🎨 Diseño

**Colores**:
```typescript
primary: '#1e3a5f'    // Azul IMPORGAS
accent: '#f97316'     // Naranja
success: '#16a34a'    // Verde
warning: '#d97706'    // Amarillo
error: '#dc2626'      // Rojo
```

**Tipografía**:
- H1: 28px bold
- H2: 22px bold
- H3: 18px semibold
- Body: 15px regular

## 📚 Documentación

1. `SISTEMA_VISITAS_TECNICAS.md` - Docs completa
2. `GUIA_RAPIDA.md` - Quick start
3. `RESUMEN_IMPLEMENTACION.md` - Stats del proyecto
4. `QUICK_REFERENCE.md` - Esta tarjeta

## ✅ Checklist de Pruebas

- [ ] Backend corriendo (`docker ps`)
- [ ] Migraciones aplicadas (`migrate`)
- [ ] Frontend corriendo (`pnpm run dev`)
- [ ] Móvil instalado (`npm install`)
- [ ] Crear usuario admin (Django admin)
- [ ] Crear usuario técnico (tipo_usuario=0)
- [ ] Crear visita desde web
- [ ] Login en móvil como técnico
- [ ] Ver visita asignada
- [ ] Iniciar visita
- [ ] Completar formulario (4 pasos)
- [ ] Subir fotos
- [ ] Firmar
- [ ] Finalizar
- [ ] Descargar PDF desde web

---

## 🎉 Todo Listo

Sistema **100% funcional** y documentado.

**Contacto**: servicioimporgas@gmail.com
**Versión**: 1.0.0
**Fecha**: Mayo 2025
