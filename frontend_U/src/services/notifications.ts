import api from './api'

export interface Notification {
  id: number
  type: 'order_update' | 'order_delivered' | 'promotion' | 'general'
  title: string
  message: string
  link: string
  is_read: boolean
  created_at: string
}

class NotificationsService {
  async getAll(unreadOnly = false): Promise<Notification[]> {
    const url = unreadOnly ? '/ecommerce/user/notifications?unread=true' : '/ecommerce/user/notifications'
    const response = await api.get<{ data: Notification[] }>(url)
    return response.data
  }

  async markAsRead(id: number): Promise<Notification> {
    const response = await api.patch<{ data: Notification }>(`/ecommerce/user/notifications/${id}`, {
      is_read: true,
    })
    return response.data
  }

  async markAllAsRead(): Promise<void> {
    await api.post('/ecommerce/user/notifications/mark-all-read', {})
  }

  async delete(id: number): Promise<void> {
    await api.delete(`/ecommerce/user/notifications/${id}`)
  }
}

export default new NotificationsService()
