import { useEffect, useState } from 'react'
import { Bell, Check, Trash2, Package, Gift, Megaphone } from 'lucide-react'
import { Link } from 'react-router-dom'
import notificationsService, { Notification } from '../../services/notifications'

const typeIcons = {
  order_update: Package,
  order_delivered: Package,
  promotion: Gift,
  general: Megaphone,
}

const typeColors = {
  order_update: 'text-blue-600 bg-blue-100',
  order_delivered: 'text-green-600 bg-green-100',
  promotion: 'text-orange-600 bg-orange-100',
  general: 'text-gray-600 bg-gray-100',
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')

  useEffect(() => {
    loadNotifications()
  }, [filter])

  const loadNotifications = async () => {
    setLoading(true)
    try {
      const data = await notificationsService.getAll(filter === 'unread')
      setNotifications(data)
    } catch (error) {
      console.error('Error loading notifications:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (id: number) => {
    try {
      await notificationsService.markAsRead(id)
      setNotifications(notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    } catch (error) {
      console.error('Error marking as read:', error)
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsService.markAllAsRead()
      setNotifications(notifications.map((n) => ({ ...n, is_read: true })))
    } catch (error) {
      console.error('Error marking all as read:', error)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await notificationsService.delete(id)
      setNotifications(notifications.filter((n) => n.id !== id))
    } catch (error) {
      console.error('Error deleting notification:', error)
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#001575]"></div>
          <p className="mt-4 text-gray-600">Cargando notificaciones...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Bell className="w-8 h-8 text-[#001575]" />
            Notificaciones
          </h1>
          <p className="mt-2 text-gray-600">
            {unreadCount > 0 ? `${unreadCount} sin leer` : 'No tienes notificaciones sin leer'}
          </p>
        </div>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-xl font-semibold transition-colors ${
                filter === 'all'
                  ? 'bg-[#001575] text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Todas
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-2 rounded-xl font-semibold transition-colors ${
                filter === 'unread'
                  ? 'bg-[#001575] text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Sin leer
            </button>
          </div>

          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllAsRead}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-xl font-semibold hover:bg-gray-50 transition-colors"
            >
              <Check className="w-4 h-4" />
              Marcar todas como leídas
            </button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            <Bell className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {filter === 'unread' ? 'No tienes notificaciones sin leer' : 'No tienes notificaciones'}
            </h3>
            <p className="text-gray-600">
              {filter === 'unread'
                ? 'Todas tus notificaciones han sido leídas'
                : 'Te notificaremos sobre actualizaciones de tus pedidos y promociones'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((notification) => {
              const Icon = typeIcons[notification.type] || Bell
              const colorClass = typeColors[notification.type] || typeColors.general

              return (
                <div
                  key={notification.id}
                  className={`bg-white rounded-2xl shadow-sm border transition-all ${
                    notification.is_read ? 'border-gray-100' : 'border-blue-200 bg-blue-50/30'
                  }`}
                >
                  <div className="p-5 flex items-start gap-4">
                    <div className={`p-3 rounded-xl ${colorClass} flex-shrink-0`}>
                      <Icon className="w-5 h-5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3 mb-1">
                        <h3 className="font-semibold text-gray-900">{notification.title}</h3>
                        {!notification.is_read && (
                          <span className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-1.5"></span>
                        )}
                      </div>

                      <p className="text-gray-600 mb-2">{notification.message}</p>

                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-gray-500">
                          {new Date(notification.created_at).toLocaleDateString('es-CO', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>

                        {notification.link && (
                          <Link
                            to={notification.link}
                            className="text-[#001575] hover:underline font-medium"
                          >
                            Ver detalles →
                          </Link>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      {!notification.is_read && (
                        <button
                          onClick={() => handleMarkAsRead(notification.id)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Marcar como leída"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(notification.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
