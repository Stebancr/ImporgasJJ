import { Order, CartItem } from '../types'
import api from './api'

interface CreateOrderData {
  items: CartItem[]
  shippingAddress: string
  paymentMethod: string
}

export const ordersService = {
  create: async (data: CreateOrderData): Promise<Order> => {
    return api.post<Order>('/orders', data)
  },

  getById: async (id: string): Promise<Order> => {
    return api.get<Order>(`/orders/${id}`)
  },

  getMyOrders: async (): Promise<Order[]> => {
    return api.get<Order[]>('/orders/my-orders')
  },

  getTracking: async (orderId: string): Promise<Order> => {
    return api.get<Order>(`/orders/${orderId}/tracking`)
  },

  updateStatus: async (orderId: string, status: Order['status']): Promise<Order> => {
    return api.patch<Order>(`/orders/${orderId}/status`, { status })
  },
}

export default ordersService
