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
  notes: string
  items: BackendOrderItem[]
  tracking_history: BackendTrackingEvent[]
  created_at: string
  updated_at: string
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
}

export default ordersService
