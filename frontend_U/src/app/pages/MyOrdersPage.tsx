import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Package, Eye, Search } from 'lucide-react'
import ordersService, { BackendOrder } from '../../services/orders'

const statusLabels: Record<string, string> = {
  pending: 'Pendiente',
  paid: 'Pagado',
  preparing: 'En preparación',
  shipping: 'En camino',
  delivered: 'Entregado',
  installed: 'Instalado',
  cancelled: 'Cancelado',
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  preparing: 'bg-purple-100 text-purple-800',
  shipping: 'bg-indigo-100 text-indigo-800',
  delivered: 'bg-green-100 text-green-800',
  installed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-red-100 text-red-800',
}

export default function MyOrdersPage() {
  const [orders, setOrders] = useState<BackendOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadOrders()
  }, [])

  const loadOrders = async () => {
    setLoading(true)
    try {
      const data = await ordersService.getMyOrders()
      setOrders(data)
    } catch (error) {
      console.error('Error loading orders:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price: string) => {
    const num = parseFloat(price)
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(num)
  }

  const filteredOrders = orders.filter(
    (order) =>
      order.order_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      order.customer_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#001575]"></div>
          <p className="mt-4 text-gray-600">Cargando pedidos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Package className="w-8 h-8 text-[#001575]" />
            Mis Pedidos
          </h1>
          <p className="mt-2 text-gray-600">
            {orders.length} {orders.length === 1 ? 'pedido realizado' : 'pedidos realizados'}
          </p>
        </div>

        {orders.length > 0 && (
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar por número de pedido o nombre..."
                className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#001575] focus:border-transparent"
              />
            </div>
          </div>
        )}

        {filteredOrders.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {searchQuery ? 'No se encontraron pedidos' : 'No tienes pedidos'}
            </h3>
            <p className="text-gray-600 mb-6">
              {searchQuery
                ? 'Intenta con otro término de búsqueda'
                : 'Explora nuestros productos y realiza tu primera compra'}
            </p>
            {!searchQuery && (
              <Link
                to="/productos"
                className="inline-block px-6 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors"
              >
                Explorar productos
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredOrders.map((order) => (
              <div
                key={order.id}
                className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        Pedido {order.order_number}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {new Date(order.created_at).toLocaleDateString('es-CO', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>
                    <span
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold ${
                        statusColors[order.status] || statusColors.pending
                      }`}
                    >
                      {statusLabels[order.status] || order.status}
                    </span>
                  </div>

                  <div className="space-y-3 mb-4">
                    {order.items.map((item) => (
                      <div key={item.id} className="flex items-center gap-4">
                        {item.primary_image && (
                          <img
                            src={item.primary_image}
                            alt={item.product_name}
                            className="w-16 h-16 object-cover rounded-lg bg-gray-100"
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 truncate">
                            {item.product_name}
                          </p>
                          <p className="text-sm text-gray-600">
                            Cantidad: {item.quantity} × {formatPrice(item.unit_price)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-gray-900">
                            {formatPrice(item.subtotal)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="text-sm text-gray-600">
                        <p>
                          <strong>Método de pago:</strong>{' '}
                          {order.payment_method === 'wompi'
                            ? 'Wompi (tarjeta/PSE/Nequi)'
                            : 'Contra entrega'}
                        </p>
                        <p className="mt-1">
                          <strong>Dirección:</strong> {order.shipping_address}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">Total</p>
                        <p className="text-2xl font-bold text-[#001575]">
                          {formatPrice(order.total)}
                        </p>
                      </div>
                    </div>

                    <Link
                      to={`/pedido/${order.tracking_code}`}
                      className="flex items-center justify-center gap-2 w-full px-6 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors"
                    >
                      <Eye className="w-5 h-5" />
                      Ver detalles y rastreo
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
