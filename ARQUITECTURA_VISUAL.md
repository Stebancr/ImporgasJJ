# 🏗️ Arquitectura Visual del Sistema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SISTEMA DE VISITAS TÉCNICAS                      │
│                              IMPORGAS JJ                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────────────┐          ┌────────────────────────┐
│   📱 APP MÓVIL EXPO    │          │   🖥️ PANEL WEB ADMIN   │
│   (React Native)       │          │   (React + Vite)       │
├────────────────────────┤          ├────────────────────────┤
│ • LoginScreen          │          │ • VisitsPage           │
│ • DashboardScreen      │          │   - Vista Lista        │
│ • VisitsListScreen     │  HTTP    │   - Vista Calendario   │
│ • VisitDetailScreen    │ ◄────────┤ • Formularios          │
│ • VisitFormScreen      │  JSON    │ • Detalle + Evidencias │
│ • CalendarScreen       │          │ • Descarga PDF         │
│ • ProfileScreen        │          │                        │
│                        │          │                        │
│ Técnicos (tipo=0)      │          │ Admins (tipo>=1)       │
└────────────┬───────────┘          └──────────┬─────────────┘
             │                                  │
             │  JWT Auth (access + refresh)     │
             │  GET/POST/PATCH/DELETE           │
             └─────────────┬────────────────────┘
                           │
                           ▼
             ┌─────────────────────────────┐
             │   🐳 DOCKER BACKEND         │
             │   Django REST Framework     │
             ├─────────────────────────────┤
             │  nginx :80 (reverse proxy)  │
             │    ▼                         │
             │  backend :8000               │
             └─────────────┬───────────────┘
                           │
                           ▼
             ┌─────────────────────────────┐
             │   📦 AppVisits API          │
             ├─────────────────────────────┤
             │ ENDPOINTS:                  │
             │ • GET /visits/              │
             │ • POST /visits/             │
             │ • GET /visits/{id}/         │
             │ • PATCH /visits/{id}/       │
             │ • DELETE /visits/{id}/      │
             │ • POST /visits/{id}/iniciar/│
             │ • POST /visits/{id}/finalizar/│
             │ • POST /visits/{id}/fotos/  │
             │ • DELETE /visits/{id}/fotos/{foto_id}/│
             │ • GET /visits/calendario/   │
             │ • GET /visits/{id}/pdf/     │
             └─────────────┬───────────────┘
                           │
                           ▼
             ┌─────────────────────────────┐
             │   🗄️ PostgreSQL DB          │
             ├─────────────────────────────┤
             │ TABLAS:                     │
             │ • ClienteVisita             │
             │ • VisitaTecnica             │
             │ • ReporteVisita             │
             │ • EvidenciaFotografica      │
             │ • Credenciales (usuarios)   │
             └─────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### 1️⃣ Creación de Visita (Admin Web)

```
Admin Web                Backend API              Base de Datos
    │                        │                          │
    │  POST /visits/         │                          │
    ├───────────────────────►│                          │
    │  {                     │  Validar permisos        │
    │    cliente_nombre,     │  (tipo_usuario >= 1)     │
    │    tipo_tarea,         │          │               │
    │    tecnico_id,         │          ▼               │
    │    fecha,              │  Crear ClienteVisita     │
    │    ...                 │  Crear VisitaTecnica     │
    │  }                     │  (estado=pendiente)      │
    │                        ├─────────────────────────►│
    │                        │                          │
    │  ◄─────────────────────┤  INSERT INTO ...         │
    │  201 Created           │  RETURNING id            │
    │  {                     │◄─────────────────────────┤
    │    id: 123,            │                          │
    │    numero_tarea: "1234567",                      │
    │    estado: "pendiente",│                          │
    │    ...                 │                          │
    │  }                     │                          │
```

### 2️⃣ Iniciar Visita (Técnico Móvil)

```
App Móvil               Backend API              Base de Datos
    │                        │                          │
    │  POST /visits/123/iniciar/                        │
    ├───────────────────────►│                          │
    │  Authorization:        │  Validar permisos        │
    │  Bearer eyJhbG...      │  (técnico asignado)      │
    │                        │          │               │
    │                        │          ▼               │
    │                        │  estado → en_proceso     │
    │                        │  Crear ReporteVisita     │
    │                        │  inicio_desplazamiento   │
    │                        │  = datetime.now()        │
    │                        ├─────────────────────────►│
    │                        │  UPDATE visita SET ...   │
    │  ◄─────────────────────┤  INSERT INTO reporte ... │
    │  200 OK                │◄─────────────────────────┤
    │  {                     │                          │
    │    estado: "en_proceso",│                         │
    │    reporte: {...}      │                          │
    │  }                     │                          │
```

### 3️⃣ Completar Formulario (Técnico Móvil)

```
App Móvil               Backend API              Base de Datos
    │                        │                          │
    │  1. Captura 5 fotos    │                          │
    │  2. Comprime (1200px, 70%)                        │
    │  3. POST /visits/123/fotos/                       │
    │     multipart/form-data│                          │
    ├───────────────────────►│                          │
    │  [                     │  Validar max 20 fotos    │
    │    foto1.jpg (Base64), │          │               │
    │    foto2.jpg,          │          ▼               │
    │    ...                 │  Guardar en media/       │
    │  ]                     │  Crear EvidenciaFoto     │
    │                        ├─────────────────────────►│
    │  ◄─────────────────────┤  INSERT INTO evidencia   │
    │  201 Created (x5)      │◄─────────────────────────┤
    │                        │                          │
    │  4. Cliente firma      │                          │
    │  5. POST /visits/123/finalizar/                   │
    ├───────────────────────►│                          │
    │  {                     │  Validar campos required │
    │    persona_atiende,    │          │               │
    │    equipo,             │          ▼               │
    │    motivo_servicio,    │  Actualizar ReporteVisita│
    │    solucion_realizada, │  estado → finalizada     │
    │    valor_servicio,     │  duracion_desplazamiento │
    │    firma_base64        │  = (now - inicio)        │
    │  }                     ├─────────────────────────►│
    │                        │  UPDATE reporte SET ...  │
    │  ◄─────────────────────┤  UPDATE visita SET ...   │
    │  200 OK                │◄─────────────────────────┤
```

### 4️⃣ Descargar PDF (Admin Web)

```
Admin Web               Backend API              Base de Datos
    │                        │                          │
    │  GET /visits/123/pdf/  │                          │
    ├───────────────────────►│                          │
    │  Authorization:        │  Validar permisos        │
    │  Bearer eyJhbG...      │  (admin only)            │
    │                        │          │               │
    │                        │          ▼               │
    │                        │  SELECT visita, cliente, │
    │                        │  reporte, evidencias     │
    │                        │◄─────────────────────────┤
    │                        │                          │
    │                        │  Generar PDF (reportlab) │
    │                        │  - Logo + header         │
    │                        │  - Datos cliente         │
    │                        │  - Reporte técnico       │
    │                        │  - Firma cliente         │
    │                        │  - Grid fotos            │
    │                        │          │               │
    │  ◄─────────────────────┤          ▼               │
    │  200 OK                │  BytesIO stream          │
    │  Content-Type:         │                          │
    │  application/pdf       │                          │
    │  Content-Disposition:  │                          │
    │  attachment; filename="visita_1234567.pdf"       │
```

---

## 🔐 Flujo de Autenticación

```
Cliente                 Backend Auth             SecureStore (Móvil)
   │                         │                          │
   │  POST /auth/token/      │                          │
   ├────────────────────────►│                          │
   │  {                      │  Validar credenciales    │
   │    usuario: "tecnico1", │  (Django Auth)           │
   │    password: "****"     │          │               │
   │  }                      │          ▼               │
   │                         │  SELECT * FROM usuarios  │
   │                         │  WHERE usuario=...       │
   │                         │          │               │
   │  ◄──────────────────────┤          ▼               │
   │  {                      │  Generar tokens JWT      │
   │    access: "eyJhbG...", │  access (12h)            │
   │    refresh: "eyJhbG...",│  refresh (1d)            │
   │    is_admin: false,     │                          │
   │    tipo_usuario: 0,     │                          │
   │    location_id: 1       │                          │
   │  }                      │                          │
   │          │              │                          │
   │          ▼              │                          │
   │  Almacenar tokens       │                          │
   ├─────────────────────────┼─────────────────────────►│
   │                         │  SecureStore.setItem(    │
   │                         │   'intagas_access', ...  │
   │                         │  )                       │
   │                         │                          │
   │  GET /visits/           │                          │
   ├────────────────────────►│◄─────────────────────────┤
   │  Authorization:         │  SecureStore.getItem()   │
   │  Bearer eyJhbG...       │                          │
   │                         │  Validar JWT             │
   │  ◄──────────────────────┤  Decodificar payload     │
   │  200 OK                 │  Verificar exp           │
   │  [visitas...]           │                          │
   │                         │                          │
   │  GET /visits/ (12h después)                        │
   ├────────────────────────►│                          │
   │  Bearer expired_token   │                          │
   │                         │  JWT expired             │
   │  ◄──────────────────────┤                          │
   │  401 Unauthorized       │                          │
   │          │              │                          │
   │          ▼              │                          │
   │  Interceptor detecta 401│                          │
   │  POST /auth/token/refresh/                         │
   ├────────────────────────►│◄─────────────────────────┤
   │  {                      │  SecureStore.getItem(    │
   │    refresh: "eyJhbG..." │   'intagas_refresh'      │
   │  }                      │  )                       │
   │                         │  Validar refresh token   │
   │  ◄──────────────────────┤                          │
   │  {                      │                          │
   │    access: "NEW_TOKEN"  │                          │
   │  }                      │                          │
   │          │              │                          │
   │          ▼              │                          │
   │  Actualizar token       │                          │
   ├─────────────────────────┼─────────────────────────►│
   │  Reintentar petición    │  Update SecureStore      │
   │  con nuevo token        │                          │
```

---

## 📊 Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA DE UNA VISITA                  │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────┐
        │   CREACIÓN   │  Admin crea orden desde panel web
        │  (Admin Web) │  • Datos del cliente
        └──────┬───────┘  • Tipo de tarea
               │          • Técnico asignado
               │          • Fecha y hora
               ▼
        ┌──────────────┐
        │  PENDIENTE   │  Orden visible para técnico
        │   (Estado)   │  • Espera inicio
        └──────┬───────┘  • Botón "Iniciar Visita"
               │
               │ POST /visits/{id}/iniciar/
               │
               ▼
        ┌──────────────┐
        │ EN PROCESO   │  Técnico está en terreno
        │   (Estado)   │  • Timer de desplazamiento
        └──────┬───────┘  • Botón "Completar Formulario"
               │
               │ Técnico llena formulario (4 pasos):
               │ 1. Datos cliente + equipo
               │ 2. Motivo + solución
               │ 3. Fotos (min 1, max 20)
               │ 4. Firma digital
               │
               │ POST /visits/{id}/fotos/ (x N)
               │ POST /visits/{id}/finalizar/
               │
               ▼
        ┌──────────────┐
        │  FINALIZADA  │  Reporte completo
        │   (Estado)   │  • Admin puede descargar PDF
        └──────────────┘  • Visita cerrada

               ❌ Cancelación posible en cualquier momento
               │  (solo admin)
               │
               ▼
        ┌──────────────┐
        │  CANCELADA   │  Orden cancelada
        │   (Estado)   │  • No se puede editar
        └──────────────┘
```

---

## 🗂️ Diagrama de Base de Datos

```
┌─────────────────────────┐
│   Credenciales (User)   │
├─────────────────────────┤
│ id (PK)                 │
│ usuario                 │
│ tipo_usuario            │  0=técnico, 1=admin, 4=super
│ location_id             │
│ ...                     │
└───────────┬─────────────┘
            │ FK
            │ tecnico_id
            ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   ClienteVisita         │       │   VisitaTecnica         │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ nombre                  │       │ numero_tarea (unique)   │
│ identificacion          │◄──────┤ cliente_id (FK)         │
│ telefono                │       │ tecnico_id (FK)         │
│ correo                  │       │ tipo_tarea              │
│ direccion               │       │ fecha                   │
│ creado_en               │       │ hora                    │
└─────────────────────────┘       │ descripcion             │
                                  │ observaciones_iniciales │
                                  │ estado                  │
                                  │ creado_por_id (FK)      │
                                  │ creado_en               │
                                  └───────────┬─────────────┘
                                              │ FK
                                              │ visita_id
                                              ▼
                        ┌─────────────────────────────────────┐
                        │   ReporteVisita (OneToOne)          │
                        ├─────────────────────────────────────┤
                        │ id (PK)                             │
                        │ visita_id (OneToOne, FK)            │
                        │ persona_atiende                     │
                        │ equipo                              │
                        │ equipo_otro                         │
                        │ ubicacion_equipo                    │
                        │ ubicacion_equipo_otro               │
                        │ motivo_servicio                     │
                        │ solucion_realizada                  │
                        │ observaciones                       │
                        │ recomendaciones                     │
                        │ valor_servicio                      │
                        │ metodo_pago                         │
                        │ firma_cliente (ImageField)          │
                        │ inicio_desplazamiento               │
                        │ duracion_desplazamiento (minutos)   │
                        │ creado_en                           │
                        └─────────────────────────────────────┘
                                              │ FK
                                              │ visita_id
                                              ▼
                        ┌─────────────────────────────────────┐
                        │   EvidenciaFotografica              │
                        ├─────────────────────────────────────┤
                        │ id (PK)                             │
                        │ visita_id (FK)                      │
                        │ imagen (ImageField)                 │
                        │ descripcion                         │
                        │ orden                               │
                        │ subida_en                           │
                        └─────────────────────────────────────┘
```

---

## 🎯 Componentes y Responsabilidades

```
┌─────────────────────────────────────────────────────────────────┐
│                            BACKEND                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  models.py (188 líneas)                                         │
│  • Define 4 modelos + estados + choices                         │
│  • Genera numero_tarea único (7 dígitos)                        │
│  • Relaciones: Cliente → Visita ← Reporte ← Evidencias         │
│                                                                  │
│  serializers.py (165 líneas)                                    │
│  • TecnicoSerializer (nested usuario_rel)                       │
│  • VisitaListSerializer (flat, optimizado para lista)           │
│  • VisitaDetailSerializer (nested completo)                     │
│  • VisitaCreateSerializer (crea cliente + visita)               │
│  • VisitaUpdateSerializer (solo campos editables)               │
│  • ReporteCreateSerializer (validaciones custom)                │
│                                                                  │
│  views.py (487 líneas)                                          │
│  • TecnicosView → lista técnicos (tipo_usuario=0)              │
│  • VisitaListCreateView → GET (filtros) + POST                 │
│  • VisitaDetailView → GET/PATCH/DELETE con permisos            │
│  • IniciarVisitaView → estado → en_proceso, crea reporte       │
│  • FinalizarVisitaView → actualiza reporte, estado → finalizada│
│  • FotosView → upload multipart, max 20, delete foto           │
│  • CalendarioView → agrupa por fecha, filtro mes               │
│  • PDFReporteView → genera PDF con reportlab (logo+firma+fotos)│
│                                                                  │
│  permissions.py (32 líneas)                                     │
│  • IsAdminOrReadOwn: admin full, técnico solo sus visitas      │
│  • IsAdminUser: solo admin (tipo_usuario >= 1)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND WEB                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  services/visits.ts (106 líneas)                                │
│  • API client con axios                                         │
│  • Tipos TypeScript completos                                  │
│  • Métodos: getTecnicos, getAll, create, update, delete, etc   │
│                                                                  │
│  app/pages/VisitsPage.tsx (614 líneas)                          │
│  • Tabs: Lista / Calendario                                     │
│  • Lista: tabla + filtros + búsqueda + acciones                │
│  • Calendario: grid mensual + detail panel                      │
│  • Modals: crear, editar, detalle, eliminar                    │
│  • Integración shadcn/ui + date-fns                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          APP MÓVIL                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  api/client.ts (114 líneas)                                     │
│  • Axios instance con base URL                                 │
│  • Interceptor request: agrega Bearer token                    │
│  • Interceptor response: refresh en 401 con queue              │
│  • SecureStore para persistencia                               │
│                                                                  │
│  api/visits.ts (110 líneas)                                     │
│  • authApi: login, logout, getStoredTokens, refreshProfile     │
│  • visitsApi: getAll, getById, iniciar, finalizar, fotos       │
│                                                                  │
│  store/auth.ts (54 líneas)                                      │
│  • Zustand store global                                        │
│  • initializeAuth: carga tokens + user de SecureStore          │
│  • login: guarda tokens + user                                 │
│  • logout: limpia SecureStore                                  │
│                                                                  │
│  navigation/index.tsx (107 líneas)                              │
│  • RootStack: Auth / Main                                      │
│  • AuthStack: Login                                            │
│  • MainTab: Dashboard, Visits (stack), Calendar, Profile       │
│  • VisitsStack: List, Detail, Form                             │
│                                                                  │
│  screens/VisitFormScreen.tsx (402 líneas)                       │
│  • Wizard de 4 pasos con barra de progreso                     │
│  • Step 1: Datos cliente + equipo + ubicación                  │
│  • Step 2: Motivo + solución + valor + pago                    │
│  • Step 3: Fotos (captura/galería, compresión)                 │
│  • Step 4: Firma digital (signature-canvas)                    │
│  • Validación + submit completo                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**Documentación generada**: Mayo 2025  
**Versión**: 1.0.0  
**Contacto**: servicioimporgas@gmail.com
