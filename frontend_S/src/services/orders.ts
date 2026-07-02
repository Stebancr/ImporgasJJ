import api from './api'
import type { Order, OrderStatus, TrackingEvent, ApiResponse, PaginatedResponse } from '@/types'

export interface OrderFilters {
  status?: OrderStatus
  payment_method?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export const ordersService = {
  async getAll(filters?: OrderFilters): Promise<PaginatedResponse<Order>> {
    const response = await api.get<PaginatedResponse<Order>>('/ecommerce/admin/orders', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Order> {
    const response = await api.get<ApiResponse<Order>>(`/ecommerce/admin/orders/${id}`)
    return response.data.data
  },

  async updateStatus(id: number, newStatus: OrderStatus, description?: string): Promise<Order> {
    const response = await api.patch<ApiResponse<Order>>(`/ecommerce/admin/orders/${id}`, {
      status: newStatus,
      description: description ?? `Estado actualizado a ${newStatus}`,
    })
    return response.data.data
  },

  async addTrackingEvent(
    orderId: number,
    event: { status: OrderStatus; description: string; location?: string }
  ): Promise<TrackingEvent> {
    const response = await api.post<ApiResponse<TrackingEvent>>(`/orders/${orderId}/tracking`, event)
    return response.data.data
  },
}

export default ordersService
