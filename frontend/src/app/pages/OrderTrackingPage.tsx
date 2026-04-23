import { useState } from 'react'
import { Search, Package, Truck, Home, Check, Clock, Wrench } from 'lucide-react'
import { Order, TrackingEvent } from '../../types'
import './styles/OrderTrackingPage.css'

// Mock order data
const mockOrder: Order = {
  id: 'GS-2024-001234',
  userId: '1',
  items: [
    {
      product: {
        id: '1',
        name: 'Calentador de Agua a Gas 13L',
        description: '',
        price: 650000,
        category: 'calentadores',
        brand: 'Haceb',
        images: ['https://placehold.co/100x100/f97316/white?text=Calentador'],
        rating: 5,
        reviewsCount: 128,
        stock: 15,
        specifications: {},
        isAvailable: true,
      },
      quantity: 1,
    },
  ],
  total: 820000,
  status: 'shipping',
  paymentMethod: 'wompi',
  shippingAddress: 'Calle 123 #45-67, Bogotá',
  createdAt: '2024-01-15T10:30:00Z',
  updatedAt: '2024-01-17T14:00:00Z',
  trackingHistory: [
    {
      status: 'Pedido Confirmado',
      description: 'Tu pedido ha sido confirmado y está siendo procesado',
      timestamp: '2024-01-15T10:30:00Z',
    },
    {
      status: 'Pago Verificado',
      description: 'El pago ha sido verificado exitosamente',
      timestamp: '2024-01-15T10:35:00Z',
    },
    {
      status: 'En Preparación',
      description: 'Tu pedido está siendo preparado en nuestro almacén',
      timestamp: '2024-01-16T09:00:00Z',
      location: 'Bodega Central - Bogotá',
    },
    {
      status: 'En Camino',
      description: 'Tu pedido ha salido para entrega',
      timestamp: '2024-01-17T08:00:00Z',
      location: 'Centro de Distribución Norte',
    },
  ],
}

const statusSteps = [
  { key: 'pending', label: 'Pedido', icon: Package },
  { key: 'paid', label: 'Pagado', icon: Check },
  { key: 'preparing', label: 'Preparación', icon: Clock },
  { key: 'shipping', label: 'En Camino', icon: Truck },
  { key: 'delivered', label: 'Entregado', icon: Home },
  { key: 'installed', label: 'Instalado', icon: Wrench },
]

function OrderTrackingPage() {
  const [orderNumber, setOrderNumber] = useState('')
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orderNumber.trim()) {
      setError('Por favor ingresa un número de pedido')
      return
    }

    setIsLoading(true)
    setError('')

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))

    if (orderNumber.toUpperCase() === 'GS-2024-001234') {
      setOrder(mockOrder)
    } else {
      setError('No se encontró ningún pedido con ese número')
      setOrder(null)
    }

    setIsLoading(false)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const getCurrentStepIndex = (status: Order['status']) => {
    const statusMap: Record<Order['status'], number> = {
      pending: 0,
      paid: 1,
      preparing: 2,
      shipping: 3,
      delivered: 4,
      installed: 5,
    }
    return statusMap[status]
  }

  return (
    <div className="tracking-page bg-gray-50 min-h-screen py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Seguimiento de Pedido</h1>
          <p className="text-gray-600">
            Ingresa el número de tu pedido para ver el estado de tu envío
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-12">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <input
                type="text"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                placeholder="Ej: GS-2024-001234"
                className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="bg-blue-600 text-white px-8 py-4 rounded-xl font-semibold hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              {isLoading ? 'Buscando...' : 'Buscar Pedido'}
            </button>
          </div>
          {error && <p className="mt-3 text-red-500 text-center">{error}</p>}
        </form>

        {/* Order Details */}
        {order && (
          <div className="space-y-8">
            {/* Order Info Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6 lg:p-8">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Número de Pedido</p>
                  <h2 className="text-2xl font-bold text-gray-900">{order.id}</h2>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500 mb-1">Total</p>
                  <p className="text-2xl font-bold text-gray-900">{formatPrice(order.total)}</p>
                </div>
              </div>

              {/* Progress Steps */}
              <div className="relative mb-8">
                <div className="flex justify-between">
                  {statusSteps.map((step, index) => {
                    const currentIndex = getCurrentStepIndex(order.status)
                    const isCompleted = index <= currentIndex
                    const isCurrent = index === currentIndex
                    const Icon = step.icon

                    return (
                      <div key={step.key} className="flex flex-col items-center relative z-10">
                        <div
                          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                            isCompleted
                              ? 'bg-green-500 text-white'
                              : 'bg-gray-200 text-gray-400'
                          } ${isCurrent ? 'ring-4 ring-green-100' : ''}`}
                        >
                          <Icon className="w-6 h-6" />
                        </div>
                        <p
                          className={`mt-2 text-xs sm:text-sm text-center ${
                            isCompleted ? 'text-gray-900 font-medium' : 'text-gray-400'
                          }`}
                        >
                          {step.label}
                        </p>
                      </div>
                    )
                  })}
                </div>
                {/* Progress Line */}
                <div className="absolute top-6 left-0 right-0 h-0.5 bg-gray-200 -z-0">
                  <div
                    className="h-full bg-green-500 transition-all duration-500"
                    style={{
                      width: `${(getCurrentStepIndex(order.status) / (statusSteps.length - 1)) * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* Shipping Info */}
              <div className="grid md:grid-cols-2 gap-6 pt-6 border-t">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Dirección de Envío</p>
                  <p className="font-medium text-gray-900">{order.shippingAddress}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">Fecha del Pedido</p>
                  <p className="font-medium text-gray-900">{formatDate(order.createdAt)}</p>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="bg-white rounded-2xl shadow-sm p-6 lg:p-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Historial de Seguimiento</h3>
              <div className="space-y-6">
                {order.trackingHistory.slice().reverse().map((event: TrackingEvent, index: number) => (
                  <div key={index} className="flex gap-4">
                    <div className="relative">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          index === 0 ? 'bg-green-500' : 'bg-gray-300'
                        }`}
                      />
                      {index < order.trackingHistory.length - 1 && (
                        <div className="absolute top-3 left-1/2 -translate-x-1/2 w-0.5 h-12 bg-gray-200" />
                      )}
                    </div>
                    <div className="flex-1 pb-6">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <h4 className={`font-semibold ${index === 0 ? 'text-green-600' : 'text-gray-900'}`}>
                          {event.status}
                        </h4>
                        <p className="text-sm text-gray-500">{formatDate(event.timestamp)}</p>
                      </div>
                      <p className="text-gray-600 mt-1">{event.description}</p>
                      {event.location && (
                        <p className="text-sm text-gray-500 mt-1">📍 {event.location}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Order Items */}
            <div className="bg-white rounded-2xl shadow-sm p-6 lg:p-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Productos del Pedido</h3>
              <div className="space-y-4">
                {order.items.map((item) => (
                  <div key={item.product.id} className="flex gap-4 items-center">
                    <img
                      src={item.product.images[0]}
                      alt={item.product.name}
                      className="w-16 h-16 object-cover rounded-lg"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{item.product.name}</p>
                      <p className="text-sm text-gray-500">Cantidad: {item.quantity}</p>
                    </div>
                    <p className="font-semibold text-gray-900">
                      {formatPrice(item.product.price * item.quantity)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Initial state — shown before any search */}
        {!order && !error && (
          <div className="space-y-5">
            {/* How tracking works */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center mb-5">
                Seguimiento en tiempo real
              </p>
              <div className="flex items-start justify-between overflow-x-auto pb-1 gap-1">
                {statusSteps.map((step, index) => {
                  const Icon = step.icon
                  return (
                    <div key={step.key} className="flex flex-col items-center gap-2 flex-shrink-0 flex-1 min-w-[3.5rem]">
                      {index > 0 && (
                        <div className="hidden" />
                      )}
                      <div className="w-11 h-11 rounded-full border-2 border-dashed border-gray-200 bg-gray-50 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-gray-300" />
                      </div>
                      <p className="text-xs text-gray-400 text-center leading-tight">{step.label}</p>
                    </div>
                  )
                })}
              </div>
              <p className="mt-5 text-center text-sm text-gray-400">
                Ingresa tu número de pedido para ver el estado en tiempo real
              </p>
            </div>

            {/* Demo hint */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-5 border border-blue-100">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Package className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800 mb-1">¿Quieres ver una demo?</p>
                  <p className="text-sm text-gray-600 mb-3">
                    Prueba con el número de pedido de ejemplo:
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <code className="bg-white px-3 py-1.5 rounded-lg font-mono text-blue-700 font-bold border border-blue-200 text-sm">
                      GS-2024-001234
                    </code>
                    <button
                      type="button"
                      onClick={() => setOrderNumber('GS-2024-001234')}
                      className="text-sm text-blue-600 font-semibold hover:text-blue-800 transition-colors underline underline-offset-2"
                    >
                      Usar este número →
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Help */}
            <div className="bg-gray-50 rounded-2xl p-6 text-center border border-gray-100">
              <h3 className="font-semibold text-gray-800 mb-2">¿No encuentras tu pedido?</h3>
              <p className="text-sm text-gray-500 mb-4">
                Si tienes problemas para encontrar tu pedido, contáctanos y te ayudaremos.
              </p>
              <a
                href="/contacto"
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-blue-700 transition-colors text-sm"
              >
                Contactar Soporte
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default OrderTrackingPage
