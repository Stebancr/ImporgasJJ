import api from './api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ClienteVisita {
  id?: number
  nombre: string
  identificacion?: string
  telefono?: string
  correo?: string
  direccion: string
}

export interface Tecnico {
  id: number
  usuario: string
  nombre_completo: string
  correo: string
  telefono: string
}

export interface VisitaItem {
  id: number
  numero_tarea: string
  cliente_nombre: string
  cliente_direccion: string
  cliente_telefono: string
  tipo_tarea: string
  tipo_tarea_display: string
  fecha: string
  hora: string
  estado: 'pendiente' | 'en_proceso' | 'finalizada' | 'cancelada'
  estado_display: string
  tecnico_id: number | null
  tecnico_nombre: string | null
  tiene_reporte: boolean
  evidencias_count: number
  fecha_creacion: string
}

export interface VisitaDetalle extends VisitaItem {
  cliente: ClienteVisita
  tecnico: Tecnico | null
  descripcion: string
  observaciones_iniciales: string
  reporte?: ReporteVisita
  evidencias: EvidenciaFoto[]
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

export interface CreateVisitaData {
  cliente_nombre: string
  cliente_identificacion?: string
  cliente_telefono?: string
  cliente_correo?: string
  cliente_direccion: string
  tipo_tarea: string
  fecha: string
  hora: string
  descripcion?: string
  observaciones_iniciales?: string
  tecnico_id?: number | null
}

export interface UpdateVisitaData {
  tipo_tarea?: string
  fecha?: string
  hora?: string
  descripcion?: string
  observaciones_iniciales?: string
  estado?: string
  tecnico?: number | null
}

export type CalendarioData = Record<string, CalendarioItem[]>

export interface CalendarioItem {
  id: number
  numero_tarea: string
  cliente_nombre: string
  hora: string
  estado: string
  tipo_tarea: string
  tecnico_nombre: string | null
}

// ─── Service ──────────────────────────────────────────────────────────────────

export const visitsService = {
  // Technicians
  getTecnicos: () =>
    api.get<Tecnico[]>('/visits/tecnicos/').then((r) => r.data),

  // Visits list
  getAll: (params?: Record<string, string>) =>
    api.get<VisitaItem[]>('/visits/', { params }).then((r) => r.data),

  // Visit detail
  getById: (id: number) =>
    api.get<VisitaDetalle>(`/visits/${id}/`).then((r) => r.data),

  // Create
  create: (data: CreateVisitaData) =>
    api.post<VisitaDetalle>('/visits/', data).then((r) => r.data),

  // Update
  update: (id: number, data: UpdateVisitaData) =>
    api.patch<VisitaDetalle>(`/visits/${id}/`, data).then((r) => r.data),

  // Delete
  remove: (id: number) =>
    api.delete(`/visits/${id}/`),

  // Calendar
  getCalendario: (mes: string) =>
    api.get<CalendarioData>('/visits/calendario/', { params: { mes } }).then((r) => r.data),

  // PDF download
  getPDFUrl: (id: number) => `/api/visits/${id}/pdf/`,

  downloadPDF: async (id: number) => {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/visits/${id}/pdf/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
      throw new Error(`Error ${response.status}: ${response.statusText}`)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `reporte_visita_${id}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}
