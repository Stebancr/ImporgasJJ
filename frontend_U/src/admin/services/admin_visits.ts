import api from './admin_api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ClienteVisita {
  id?: number
  nombre: string
  identificacion?: string
  telefono?: string
  correo?: string
  direccion: string
  indicaciones_llegada?: string
}

export interface Tecnico {
  id: number
  usuario: string
  nombre_completo: string
  correo: string
  telefono: string
}

export interface TipoVisita {
  id: number
  codigo: string
  nombre: string
  activo: boolean
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
  valor_visita: number | null
  costo_inicial: number | null
  costo_final: number | null
  estado: 'pendiente' | 'en_proceso' | 'finalizada' | 'cancelada'
  estado_display: string
  tecnico_id: number | null
  tecnico_nombre: string | null
  tiene_reporte: boolean
  evidencias_count: number
  fecha_creacion: string
  creado_por_nombre?: string | null
}

export interface VisitaDetalle extends VisitaItem {
  cliente: ClienteVisita
  tecnico: Tecnico | null
  descripcion: string
  observaciones_iniciales: string
  reporte?: ReporteVisita
  evidencias: EvidenciaFoto[]
  whatsapp_notificacion_estado?: string
  whatsapp_notificacion_error?: string
  pdf_disponible?: boolean
  pdf_nombre?: string | null
  pdf_estado?: string
  pdf_error?: string
  pdf_bytes?: number | null
  pdf_sha256?: string
  pdf_generado_en?: string | null
  cambios_costo?: { valor_anterior: string | null; valor_nuevo: string | null; motivo: string; cambiado_en: string; usuario_nombre: string }[]
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
  cliente_indicaciones_llegada?: string
  tipo_tarea: string
  fecha: string
  hora: string
  descripcion?: string
  observaciones_iniciales?: string
  valor_visita?: number | null
  tecnico_id?: number | null
}

export interface UpdateVisitaData {
  motivo_cambio_costo?: string
  cliente_indicaciones_llegada?: string
  tipo_tarea?: string
  fecha?: string
  hora?: string
  descripcion?: string
  observaciones_iniciales?: string
  valor_visita?: number | null
  estado?: string
  tecnico?: number | null
}

export type CalendarioData = Record<string, CalendarioItem[]>

export interface CalendarioItem {
  id: number
  numero_tarea: string
  cliente_nombre: string
  hora: string
  valor_visita: number | null
  estado: string
  tipo_tarea: string
  tecnico_nombre: string | null
}

// ─── Service ──────────────────────────────────────────────────────────────────

export const visitsService = {
  getTipos: () => api.get<TipoVisita[]>('/visits/tipos/').then((r) => r.data),
  createTipo: (data: Pick<TipoVisita, 'codigo' | 'nombre'>) =>
    api.post<TipoVisita>('/visits/tipos/', data).then((r) => r.data),
  updateTipo: (id: number, data: Partial<Pick<TipoVisita, 'nombre' | 'activo'>>) =>
    api.patch<TipoVisita>(`/visits/tipos/${id}/`, data).then((r) => r.data),
  updateCost: (id: number, value: number | null, motivo: string) =>
    api.patch<VisitaDetalle>(`/visits/${id}/costo/`, { valor_visita: value, motivo_cambio_costo: motivo }).then((r) => r.data),
  retryPDF: (id: number) => api.post(`/visits/${id}/pdf/reintentar/`).then((r) => r.data),
  revokeLinks: (id: number) => api.post(`/visits/${id}/pdf/revocar/`).then((r) => r.data),
  exportExcel: async (params: Record<string, string>) => {
    const response = await api.get('/visits/exportar/', { params, responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'visitas.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  },
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
  create: (data: CreateVisitaData, photos: File[], completeNow: boolean, report: Record<string, string>, signature?: File | null) => {
    const body = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      if (value !== null && value !== undefined) body.append(key, String(value))
    })
    body.append('completar_ahora', String(completeNow))
    if (completeNow) body.append('reporte', JSON.stringify(report))
    photos.forEach((photo) => body.append('fotos', photo))
    if (signature) body.append('firma_cliente', signature)
    return api.post<VisitaDetalle>('/visits/', body, {
      headers: { 'Content-Type': undefined },
    }).then((r) => r.data)
  },

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

  getPDFBlob: async (id: number) => {
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
        localStorage.removeItem('adminUser')
        window.location.href = '/admin/login'
      }
      throw new Error(`Error ${response.status}: ${response.statusText}`)
    }

    return response.blob()
  },

  downloadPDF: async (id: number, name?: string | null) => {
    const blob = await visitsService.getPDFBlob(id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = name || `VIS-${id}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
  openPDF: async (id: number) => {
    const tab = window.open('', '_blank')
    try {
      const blob = await visitsService.getPDFBlob(id)
      const url = window.URL.createObjectURL(blob)
      if (tab) tab.location.href = url
      else window.open(url, '_blank')
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60000)
    } catch (error) {
      tab?.close()
      throw error
    }
  },
}
