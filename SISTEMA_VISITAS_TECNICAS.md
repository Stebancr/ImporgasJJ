# 📋 Sistema de Gestión de Visitas Técnicas

Sistema completo de gestión de visitas técnicas integrado en IMPORGAS JJ, con backend Django, panel de administración web y aplicación móvil para técnicos.

---

## 🏗️ Arquitectura del Sistema

### 1. **Backend Django** (`BACKEND/AppVisits/`)

#### Modelos de Datos

- **ClienteVisita**: Información del cliente (nombre, identificación, teléfono, correo, dirección)
- **VisitaTecnica**: Orden de visita técnica (número de tarea, cliente, técnico asignado, tipo de tarea, fecha/hora, estado, observaciones)
- **ReporteVisita**: Reporte completo post-visita (persona que atiende, equipo asistido, ubicación, motivo, solución, valor, pago, firma digital, tiempos)
- **EvidenciaFotografica**: Fotografías de evidencia (hasta 20 por visita)

#### Estados de Visita

- `pendiente`: Creada por admin, esperando técnico
- `en_proceso`: Técnico inició la visita
- `finalizada`: Técnico completó reporte y firma
- `cancelada`: Visita cancelada

#### Tipos de Tarea

- Mantenimiento Preventivo
- Instalación
- Reparación
- Revisión Técnica
- Visita Técnica Perímetro Urbano
- Garantía

#### Endpoints API (`/visits/`)

| Método | Ruta                   | Descripción                                   | Permisos      |
|--------|------------------------|-----------------------------------------------|---------------|
| GET    | `/visits/tecnicos/`    | Lista de técnicos (tipo_usuario == 0)         | Admin         |
| GET    | `/visits/`             | Lista de visitas (filtros: estado, técnico, fecha, mes, search) | Admin/Técnico |
| POST   | `/visits/`             | Crear nueva visita                             | Admin         |
| GET    | `/visits/{id}/`        | Detalle de visita                              | Admin/Técnico |
| PATCH  | `/visits/{id}/`        | Editar visita (fecha, hora, técnico, etc.)     | Admin         |
| DELETE | `/visits/{id}/`        | Eliminar visita                                | Admin         |
| POST   | `/visits/{id}/iniciar/`| Cambiar estado a `en_proceso`                  | Admin/Técnico |
| POST   | `/visits/{id}/finalizar/` | Enviar reporte y cambiar a `finalizada`     | Admin/Técnico |
| POST   | `/visits/{id}/fotos/`  | Subir evidencias (multipart/form-data)         | Admin/Técnico |
| DELETE | `/visits/{id}/fotos/{foto_id}/` | Eliminar evidencia                  | Admin/Técnico |
| GET    | `/visits/calendario/`  | Visitas agrupadas por fecha (param: mes=YYYY-MM) | Admin/Técnico |
| GET    | `/visits/{id}/pdf/`    | Descargar PDF del informe técnico               | Admin         |

#### Permisos

- **Admin (tipo_usuario >= 1)**: Acceso completo (crear, editar, eliminar, ver todas las visitas)
- **Técnico (tipo_usuario == 0)**: Solo ve sus propias visitas asignadas, puede iniciarlas y completar reportes

---

### 2. **Panel Web de Administración** (`frontend_S/`)

#### Nueva página: `/dashboard/visits`

**Características:**

- **Vista Lista**: Tabla completa con búsqueda, filtros por estado y técnico, acciones rápidas
- **Vista Calendario**: Calendario mensual interactivo con puntos de color por estado, clic para ver visitas del día
- **Formulario de Creación**: Crea visita con datos de cliente, tipo de tarea, fecha/hora, técnico asignado
- **Detalle de Visita**: Muestra toda la información, reporte técnico, evidencias fotográficas
- **Descarga PDF**: Genera informe técnico profesional con logos, evidencias y firma

**Tecnologías:**

- React + TypeScript
- React Router v7
- React Hook Form + Zod (validación)
- date-fns (manejo de fechas)
- Axios (HTTP)
- shadcn/ui components

**Navegación:**

Agregada al sidebar principal:
```tsx
{ name: 'Visitas', href: '/dashboard/visits', icon: Wrench, roles: ['admin'] }
```

---

### 3. **Aplicación Móvil para Técnicos** (`app intagas/`)

#### Stack Tecnológico

- **Framework**: Expo ~52.0
- **Lenguaje**: TypeScript
- **Navegación**: React Navigation (Stack + Bottom Tabs)
- **Estado**: Zustand
- **HTTP**: Axios con interceptores JWT
- **Almacenamiento**: expo-secure-store
- **Cámara/Galería**: expo-image-picker + expo-image-manipulator
- **Firma Digital**: react-native-signature-canvas
- **Calendario**: react-native-calendars

#### Pantallas

1. **Login** (`LoginScreen.tsx`)
   - Autenticación con usuario/contraseña
   - Almacenamiento seguro de tokens JWT
   - Refresh token automático

2. **Dashboard** (`DashboardScreen.tsx`)
   - Resumen de visitas: pendientes, en proceso, finalizadas, visitas hoy
   - Bienvenida personalizada con avatar

3. **Visitas** (`VisitsListScreen.tsx`)
   - Lista de visitas asignadas al técnico actual
   - Filtros: Todas, Pendientes, En Proceso, Finalizadas
   - Búsqueda por cliente, dirección o número de tarea
   - Pull-to-refresh

4. **Detalle de Visita** (`VisitDetailScreen.tsx`)
   - Información completa del cliente y orden
   - Botón "Iniciar Visita" (cambia estado a `en_proceso`)
   - Botón "Completar Formulario" (si está en proceso)
   - Muestra reporte y evidencias si ya fue completada

5. **Formulario Técnico** (`VisitFormScreen.tsx`)
   - **4 pasos con barra de progreso:**
     1. **Datos**: Persona que atiende, equipo a asistir, ubicación
     2. **Servicio**: Motivo, solución, observaciones, valor, método de pago
     3. **Fotos**: Captura con cámara o selección de galería (hasta 20 fotos), compresión automática
     4. **Firma**: Canvas de firma digital
   - Validación en cada paso
   - Subida de imágenes con compresión (resize + jpeg 70%)
   - Envío completo a backend (reporte + firma base64 + fotos multipart)

6. **Calendario** (`CalendarScreen.tsx`)
   - Vista mensual con dots de colores por estado
   - Toca un día para ver sus visitas
   - Navegación rápida a detalle de visita

7. **Perfil** (`ProfileScreen.tsx`)
   - Datos del técnico: nombre, correo, teléfono, sede, tipo de acceso
   - Botón cerrar sesión

#### Configuración

**app.json:**
```json
{
  "expo": {
    "name": "IntagasApp",
    "slug": "intagas-app",
    "plugins": [
      "expo-secure-store",
      "expo-image-picker",
      ["expo-camera", { "cameraPermission": "..." }]
    ]
  }
}
```

**src/api/client.ts:**

- Base URL por defecto: `http://10.0.2.2:8000` (Android Emulator)
- Variable de entorno: `EXPO_PUBLIC_API_URL`
- Interceptores:
  - **Request**: Agrega `Authorization: Bearer {access}`
  - **Response**: Refresca token en 401 automáticamente

**Zustand Store** (`src/store/auth.ts`):
- Estado global de autenticación
- Tokens en SecureStore
- Perfil de usuario
- Logout callback para API interceptor

---

## 🚀 Instalación y Despliegue

### Requisitos Previos

- Docker y Docker Compose
- Node.js 20+ y pnpm (frontend)
- Expo Go o Android Studio / Xcode (móvil)

### Backend

```bash
# Levantar servicios
docker compose -f docker-compose.data.yml up -d
docker compose -f docker-compose.dev.yml up -d

# Aplicar migraciones (ya ejecutadas automáticamente)
docker exec backend python manage.py makemigrations AppVisits
docker exec backend python manage.py migrate AppVisits

# Verificar sin errores
docker exec backend python manage.py check
```

**URL Backend**: `http://localhost:8000/visits/`
**Admin Django**: `http://localhost:8000/admin/`

### Frontend Admin (React/Vite)

```bash
cd frontend_S
pnpm install
pnpm run dev
```

**URL**: `http://localhost:3001` (proxeado en `http://localhost/` via nginx)

### Mobile App (Expo)

```bash
cd "app intagas"
npm install  # o pnpm install

# Desarrollo
npm start

# Dispositivo físico (escanea QR con Expo Go)
# Emulador Android
npm run android

# Configurar URL del backend en .env local:
# EXPO_PUBLIC_API_URL=http://<tu-ip-lan>:8000
```

**Nota**: En dispositivo físico, cambiar `API_BASE` en `src/api/client.ts` a tu IP LAN (ej. `http://192.168.1.100:8000`).

---

## 📂 Estructura de Archivos

```
BACKEND/
├── AppVisits/
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── models.py           # ClienteVisita, VisitaTecnica, ReporteVisita, EvidenciaFotografica
│   ├── serializers.py      # List, Detail, Create, Update serializers
│   ├── permissions.py      # IsAdminOrReadOwn, IsAdminUser
│   ├── views.py            # Endpoints API + generación de PDF
│   ├── urls.py
│   └── migrations/
│       └── 0001_initial.py
│
├── core/
│   ├── settings.py         # INSTALLED_APPS += 'AppVisits'
│   └── urls.py             # path('visits/', include('AppVisits.urls'))
│
└── ...

frontend_S/
├── src/
│   ├── app/pages/
│   │   ├── VisitsPage.tsx         # Lista + Calendario completo
│   │   └── calendar.tsx           # Redirect a VisitsPage
│   ├── services/
│   │   └── visits.ts               # API client para visitas
│   ├── components/
│   │   └── layout/
│   │       └── DashboardLayout.tsx # Nuevo nav item "Visitas"
│   └── App.tsx                      # Nueva ruta /dashboard/visits
└── ...

app intagas/
├── src/
│   ├── api/
│   │   ├── client.ts       # Axios con JWT + auto refresh
│   │   └── visits.ts       # API endpoints
│   ├── constants/
│   │   └── theme.ts        # Colors, Spacing, Radius, Typography
│   ├── navigation/
│   │   └── index.tsx       # Root, Auth, Main, Visits stacks
│   ├── screens/
│   │   ├── LoginScreen.tsx
│   │   ├── DashboardScreen.tsx
│   │   ├── VisitsListScreen.tsx
│   │   ├── VisitDetailScreen.tsx
│   │   ├── VisitFormScreen.tsx   # 4-step wizard
│   │   ├── CalendarScreen.tsx
│   │   └── ProfileScreen.tsx
│   ├── store/
│   │   └── auth.ts         # Zustand auth store
│   ├── types/
│   │   └── index.ts        # TypeScript types
│   └── ...
├── app.json
├── package.json
├── tsconfig.json
├── babel.config.js
└── App.tsx
```

---

## 🎨 Diseño y UX

### Colores

- **Primario**: `#1e3a5f` (azul corporativo IMPORGAS)
- **Acento**: `#f97316` (naranja)
- **Éxito**: `#16a34a`
- **Advertencia**: `#d97706`
- **Error**: `#dc2626`

### Tipografía

- Heading 1: 28px bold
- Heading 2: 22px bold
- Heading 3: 18px semibold
- Body: 15px regular
- Small: 13px regular

### Estados Visuales

| Estado       | Color (Badge) | Descripción               |
|--------------|---------------|---------------------------|
| Pendiente    | Amarillo      | Creada, esperando inicio  |
| En Proceso   | Azul          | Técnico ya inició         |
| Finalizada   | Verde         | Reporte completo y firma  |
| Cancelada    | Rojo          | Orden cancelada           |

---

## 📱 Flujo de Usuario (Técnico Móvil)

1. **Login** → Ingresa con credenciales (`tipo_usuario == 0`)
2. **Dashboard** → Ve resumen de visitas
3. **Visitas → Lista** → Filtra y selecciona una visita pendiente
4. **Detalle** → Lee información del cliente y orden
5. **Iniciar Visita** → Cambia estado a `en_proceso`, inicia cronómetro de desplazamiento
6. **Completar Formulario** →
   - **Paso 1**: Persona que atiende, equipo, ubicación
   - **Paso 2**: Motivo, solución, valor, método de pago
   - **Paso 3**: Toma/selecciona fotos (mínimo 1, máximo 20)
   - **Paso 4**: Cliente firma en el canvas
7. **Enviar** → API actualiza a `finalizada`, sube fotos, guarda firma base64
8. **Listo** → Visita completa. El admin puede descargar PDF del informe

---

## 🔐 Seguridad

- **JWT Authentication**: Access token (12 horas) + Refresh token (1 día)
- **Secure Store**: Tokens almacenados de forma segura en dispositivo móvil
- **Permisos granulares**: Admin vs Técnico controlados en backend
- **Validación de datos**: Backend valida campos obligatorios, límites de fotos, estados permitidos
- **CORS configurado**: Permitido desde `localhost`, `127.0.0.1`, ngrok

---

## 📊 Generación de PDF (Backend)

**Librería**: ReportLab

**Estructura del PDF:**

1. **Encabezado**: Logo, nombre de empresa, contacto
2. **Cliente**: Nombre, identificación, teléfono, correo, dirección
3. **Actividad**: Técnico, tipo de tarea, fecha, descripción, reporte
4. **Formulario**:
   - Persona que atiende
   - Equipo y ubicación
   - Motivo y solución
   - Valor y método de pago
5. **Condiciones y garantías**: Texto legal
6. **Firma del cliente**: Imagen embebida
7. **Fotos**: Grid de evidencias (hasta 20 fotos en grid 3 columnas)

**Endpoint**: `GET /visits/{id}/pdf/`

---

## 🧪 Pruebas

### Backend

```bash
docker exec backend python manage.py test AppVisits
```

### Frontend

```bash
cd frontend_S
pnpm run build
```

### Mobile

```bash
cd "app intagas"
npm run android
```

---

## 📈 Roadmap Futuro

- [ ] Notificaciones push (asignación de visita, recordatorio)
- [ ] Chat en tiempo real técnico ↔ admin
- [ ] Mapa con ubicación de visitas del día
- [ ] Firma con huella digital
- [ ] Export Excel de reportes
- [ ] Dashboard analytics para admin (KPIs)
- [ ] Modo offline con sincronización posterior
- [ ] Reconocimiento de voz para reporte

---

## 🤝 Equipo

Desarrollado por el equipo de IMPORGAS JJ.

**Tecnologías usadas:**
- Django + DRF + PostgreSQL
- React + TypeScript + Vite
- React Native + Expo
- Docker + nginx
- ReportLab + Pillow
- Axios + Zustand + React Navigation

---

## 📄 Licencia

© 2025 IMPORGAS JJ. Todos los derechos reservados.

---

## 📞 Soporte

Para problemas o consultas:
- **Email**: servicioimporgas@gmail.com
- **Teléfono**: 3165266734 / 3176467820
