// ─── Types shared across the mobile app ──────────────────────────────────────

export interface AuthTokens {
  access: string
  refresh: string
}

export interface AuthUser {
  id: number
  usuario: string
  nombre_completo: string
  correo: string | null
  telefono: string | null
  tipo_usuario: number
  location_id: number | null
  location_name: string | null
}

export type VisitaEstado = 'pendiente' | 'en_proceso' | 'finalizada' | 'cancelada'

export interface VisitaItem {
  id: number
  numero_tarea: string
  cliente_nombre: string
  cliente_direccion: string
  cliente_telefono: string
  tipo_tarea: string
  tipo_tarea_display: string
  fecha: string          // YYYY-MM-DD
  hora: string           // HH:MM:SS
  estado: VisitaEstado
  estado_display: string
  tecnico_id: number | null
  tecnico_nombre: string | null
  tiene_reporte: boolean
  evidencias_count: number
  fecha_creacion: string
}

export interface Cliente {
  id: number
  nombre: string
  identificacion: string
  telefono: string
  correo: string
  direccion: string
}

export interface Tecnico {
  id: number
  usuario: string
  nombre_completo: string
  correo: string
  telefono: string
}

export interface ReporteVisita {
  id: number
  persona_atiende: string
  equipo: string
  equipo_display: string
  equipo_otro: string
  ubicacion_equipo: string
  ubicacion_display: string
  ubicacion_otro: string
  motivo_servicio: string
  solucion_realizada: string
  observaciones: string
  recomendaciones: string
  valor_servicio: string | null
  metodo_pago: string
  metodo_pago_display: string
  firma_cliente: string | null
  inicio_desplazamiento: string | null
  duracion_desplazamiento: string
}

export interface EvidenciaFoto {
  id: number
  imagen: string
  descripcion: string
  orden: number
  subida_en: string
}

export interface VisitaDetalle extends VisitaItem {
  cliente: Cliente
  tecnico: Tecnico | null
  descripcion: string
  observaciones_iniciales: string
  reporte?: ReporteVisita
  evidencias: EvidenciaFoto[]
}

export interface ReporteFormData {
  persona_atiende: string
  equipo: string
  equipo_otro?: string
  ubicacion_equipo: string
  ubicacion_otro?: string
  motivo_servicio: string
  solucion_realizada: string
  observaciones?: string
  recomendaciones?: string
  valor_servicio?: string
  metodo_pago?: string
}

export interface CalendarioItem {
  id: number
  numero_tarea: string
  cliente_nombre: string
  hora: string
  estado: VisitaEstado
  tipo_tarea: string
  tecnico_nombre: string | null
}

export type CalendarioData = Record<string, CalendarioItem[]>

// ─── Navigation ───────────────────────────────────────────────────────────────

export type RootStackParamList = {
  Auth: undefined
  Main: undefined
}

export type AuthStackParamList = {
  Login: undefined
}

export type MainTabParamList = {
  Dashboard: undefined
  Visits: undefined
  Calendar: undefined
  Profile: undefined
}

export type VisitsStackParamList = {
  VisitsList: undefined
  VisitDetail: { id: number }
  VisitForm: { id: number }
}
