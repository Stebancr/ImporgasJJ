import api from './api'
import type { Order, OrderStatus, TrackingEvent, ApiResponse, PaginatedResponse } from '@/types'

export interface OrderFilters {
  user_id?: number
  status?: OrderStatus
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export interface CreateOrderData {
  user_id: number
  payment_method: string
  shipping_address: string
  items: {
    product_id: number
    quantity: number
    unit_price: number
  }[]
}

export const ordersService = {
  async getAll(filters?: OrderFilters): Promise<PaginatedResponse<Order>> {
    const response = await api.get<PaginatedResponse<Order>>('/orders', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Order> {
    const response = await api.get<ApiResponse<Order>>(`/orders/${id}`)
    return response.data.data
  },

  async create(data: CreateOrderData): Promise<Order> {
    const response = await api.post<ApiResponse<Order>>('/orders', data)
    return response.data.data
  },

  async updateStatus(id: number, status: OrderStatus): Promise<Order> {
    const response = await api.patch<ApiResponse<Order>>(`/orders/${id}/status`, { status })
    return response.data.data
  },

  async addTrackingEvent(
    orderId: number,
    event: { status: OrderStatus; description: string; location?: string }
  ): Promise<TrackingEvent> {
    const response = await api.post<ApiResponse<TrackingEvent>>(`/orders/${orderId}/tracking`, event)
    return response.data.data
  },

  async getTrackingEvents(orderId: number): Promise<TrackingEvent[]> {
    const response = await api.get<ApiResponse<TrackingEvent[]>>(`/orders/${orderId}/tracking`)
    return response.data.data
  },

  async getMyOrders(): Promise<Order[]> {
    const response = await api.get<ApiResponse<Order[]>>('/orders/my-orders')
    return response.data.data
  },
}

export default ordersService
