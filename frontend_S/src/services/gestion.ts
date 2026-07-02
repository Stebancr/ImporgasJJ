import api from './api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface StockEntry {
  id: number
  producto_id: number
  producto_name: string
  producto_slug: string
  precio: string
  quantity: number
  updated_at: string
}

export interface DocumentoItem {
  id?: number
  producto_id: number
  producto_name?: string
  descripcion: string
  cantidad: number
  precio_unitario: number
  descuento_item: number
  subtotal?: number
}

export interface Cotizacion {
  id: number
  numero: string
  location_id?: number
  location_name: string
  creado_por_usuario: string
  cliente_nombre: string
  cliente_cedula: string
  cliente_correo: string
  cliente_telefono: string
  estado: 'borrador' | 'enviada' | 'aprobada' | 'rechazada' | 'vencida' | 'convertida'
  fecha_emision: string
  fecha_vencimiento: string | null
  subtotal: string
  descuento_pct: string
  descuento_monto: string
  impuesto_pct: string
  impuesto_monto: string
  total: string
  notas: string
  items: DocumentoItem[]
  items_count?: number
  tiene_factura?: boolean
  created_at: string
  updated_at?: string
}

export interface Factura {
  id: number
  numero: string
  cotizacion_numero?: string | null
  location_id?: number
  location_name: string
  creado_por_usuario: string
  cliente_nombre: string
  cliente_cedula: string
  cliente_correo: string
  cliente_telefono: string
  estado: 'emitida' | 'anulada'
  fecha_emision: string
  subtotal: string
  descuento_pct: string
  descuento_monto: string
  impuesto_pct: string
  impuesto_monto: string
  total: string
  notas: string
  items: DocumentoItem[]
  items_count?: number
  created_at: string
}

export interface CotizacionPayload {
  location_id?: number
  cliente_nombre: string
  cliente_cedula?: string
  cliente_correo?: string
  cliente_telefono?: string
  fecha_vencimiento?: string | null
  descuento_pct?: number
  impuesto_pct?: number
  notas?: string
  items: Omit<DocumentoItem, 'id' | 'producto_name' | 'subtotal'>[]
}

export interface FacturaPayload {
  location_id?: number
  cliente_nombre: string
  cliente_cedula?: string
  cliente_correo?: string
  cliente_telefono?: string
  descuento_pct?: number
  impuesto_pct?: number
  notas?: string
  items: Omit<DocumentoItem, 'id' | 'producto_name' | 'subtotal'>[]
}

interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// ─── Stock ────────────────────────────────────────────────────────────────────

export const gestionService = {
  // Stock
  async getStock(params?: { location_id?: number; search?: string; page?: number }): Promise<PaginatedResponse<StockEntry>> {
    const res = await api.get('/gestion/stock', { params })
    return res.data
  },

  async updateStock(product_id: number, quantity: number, location_id?: number): Promise<StockEntry> {
    const res = await api.patch(`/gestion/stock/${product_id}`, { quantity, location_id })
    return res.data
  },

  async getMiSede(): Promise<{ tipo_usuario: number; location: { id: number; name: string; address: string; city: string } | null }> {
    const res = await api.get('/gestion/mi-sede')
    return res.data
  },

  // Cotizaciones
  async getCotizaciones(params?: { estado?: string; search?: string; location_id?: number; page?: number }): Promise<PaginatedResponse<Cotizacion>> {
    const res = await api.get('/gestion/cotizaciones', { params })
    return res.data
  },

  async getCotizacion(id: number): Promise<{ data: Cotizacion }> {
    const res = await api.get(`/gestion/cotizaciones/${id}`)
    return res.data
  },

  async createCotizacion(payload: CotizacionPayload): Promise<{ data: Cotizacion }> {
    const res = await api.post('/gestion/cotizaciones', payload)
    return res.data
  },

  async updateCotizacion(id: number, payload: Partial<CotizacionPayload> & { estado?: string }): Promise<{ data: Cotizacion }> {
    const res = await api.put(`/gestion/cotizaciones/${id}`, payload)
    return res.data
  },

  async deleteCotizacion(id: number): Promise<void> {
    await api.delete(`/gestion/cotizaciones/${id}`)
  },

  async convertirCotizacion(id: number): Promise<{ data: Factura }> {
    const res = await api.post(`/gestion/cotizaciones/${id}/convertir`)
    return res.data
  },

  // Facturas
  async getFacturas(params?: { estado?: string; search?: string; location_id?: number; page?: number }): Promise<PaginatedResponse<Factura>> {
    const res = await api.get('/gestion/facturas', { params })
    return res.data
  },

  async getFactura(id: number): Promise<{ data: Factura }> {
    const res = await api.get(`/gestion/facturas/${id}`)
    return res.data
  },

  async createFactura(payload: FacturaPayload): Promise<{ data: Factura }> {
    const res = await api.post('/gestion/facturas', payload)
    return res.data
  },

  async updateFactura(id: number, payload: Partial<FacturaPayload>): Promise<{ data: Factura }> {
    const res = await api.put(`/gestion/facturas/${id}`, payload)
    return res.data
  },

  async anularFactura(id: number): Promise<{ data: Factura }> {
    const res = await api.post(`/gestion/facturas/${id}/anular`)
    return res.data
  },
}

export default gestionService
