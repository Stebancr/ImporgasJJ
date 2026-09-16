import api from './api'

// ─── Backend types ────────────────────────────────────────────────────────────

export interface BackendOrderItem {
  id: number
  order_id: number
  product_id: number
  product_name: string
  quantity: number
  unit_price: string
  subtotal: string
  primary_image: string | null
}

export interface BackendTrackingEvent {
  id: number
  order_id: number
  status: string
  description: string
  location: string
  timestamp: string
}

export interface BackendOrder {
  id: number
  order_number: string
  tracking_code: string
  status: 'pending' | 'paid' | 'preparing' | 'shipping' | 'delivered' | 'installed' | 'cancelled'
  customer_name: string
  customer_email: string
  customer_phone: string
  shipping_address: string
  city: string
  department: string
  postal_code: string
  subtotal: string
  shipping_cost: string
  total: string
  payment_method: 'wompi' | 'cash'
  wompi_reference: string
  wompi_transaction_id: string
  wompi_signature?: string
  notes: string
  items: BackendOrderItem[]
  tracking_history: BackendTrackingEvent[]
  created_at: string
  updated_at: string
}

export interface WompiCheckoutIntent {
  wompi_public_key?: string
  tracking_code: string
  wompi_reference: string
  wompi_signature: string
  total: string
  payment_status: 'PENDING'
}

export interface CreateOrderPayload {
  customer_name: string
  customer_email: string
  customer_phone?: string
  shipping_address: string
  city?: string
  department?: string
  postal_code?: string
  payment_method: 'wompi' | 'cash'
  wompi_reference?: string
  notes?: string
  items: { product_id: number; quantity: number }[]
}

export const ordersService = {
  create: async (data: CreateOrderPayload): Promise<BackendOrder> => {
    const res = await api.post<{ data: BackendOrder }>('/orders', data)
    return (res as unknown as { data: BackendOrder }).data
  },

  createWompiIntent: async (data: CreateOrderPayload): Promise<WompiCheckoutIntent> => {
    const res = await api.post<{ data: BackendOrder | WompiCheckoutIntent }>('/orders', data)
    return (res as unknown as { data: WompiCheckoutIntent }).data
  },

  getByTracking: async (trackingCode: string): Promise<BackendOrder> => {
    const res = await api.get<{ data: BackendOrder }>(`/orders/tracking/${trackingCode}`)
    return (res as unknown as { data: BackendOrder }).data
  },

  getById: async (id: number): Promise<BackendOrder> => {
    const res = await api.get<{ data: BackendOrder }>(`/orders/${id}`)
    return (res as unknown as { data: BackendOrder }).data
  },

  getMyOrders: async (): Promise<BackendOrder[]> => {
    const res = await api.get<{ data: BackendOrder[] }>('/orders?per_page=50')
    return (res as unknown as { data: BackendOrder[] }).data ?? []
  },

  getAll: async (params?: { page?: number; page_size?: number }): Promise<{ results: BackendOrder[] }> => {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', String(params.page))
    if (params?.page_size) queryParams.append('page_size', String(params.page_size))
    const res = await api.get<{ data: BackendOrder[] }>(`/orders?${queryParams.toString()}`)
    return { results: (res as unknown as { data: BackendOrder[] }).data ?? [] }
  },
}

export default ordersService
