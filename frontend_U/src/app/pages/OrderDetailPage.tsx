import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Package, Truck, Home, Wrench, CheckCircle, Clock, XCircle,
  ChevronLeft, Loader2, CreditCard, MapPin, User, RefreshCw,
} from 'lucide-react'
import { ordersService } from '../../services/orders'
import type { BackendOrder } from '../../services/orders'

// ─── helpers ─────────────────────────────────────────────────────────────────

const STATUS_STEPS = [
  { key: 'pending',   label: 'Pedido recibido', icon: Package },
  { key: 'paid',      label: 'Pago confirmado', icon: CheckCircle },
  { key: 'preparing', label: 'En preparación',  icon: Clock },
  { key: 'shipping',  label: 'En camino',        icon: Truck },
  { key: 'delivered', label: 'Entregado',        icon: Home },
  { key: 'installed', label: 'Instalado',        icon: Wrench },
]

const STATUS_LABEL: Record<BackendOrder['status'], string> = {
  pending:   'Pendiente de pago',
  paid:      'Pago confirmado',
  preparing: 'En preparación',
  shipping:  'En camino',
  delivered: 'Entregado',
  installed: 'Instalado',
  cancelled: 'Cancelado',
}

const fmt = (val: string | number) =>
  Number(val).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })

function getCurrentStepIndex(status: BackendOrder['status']) {
  const idx = STATUS_STEPS.findIndex((s) => s.key === status)
  return idx === -1 ? 0 : idx
}

// ─── component ───────────────────────────────────────────────────────────────

export default function OrderDetailPage() {
  const { trackingCode } = useParams<{ trackingCode: string }>()
  const [order, setOrder]     = useState<BackendOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchOrder = async (showLoader = false) => {
    if (!trackingCode) return
    if (showLoader) setLoading(true)
    setError('')
    try {
      const data = await ordersService.getByTracking(trackingCode)
      setOrder(data)
      setLastRefresh(new Date())
    } catch {
      setError('No se encontró el pedido. Verifica el código de seguimiento.')
    } finally {
      if (showLoader) setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrder(true)
    // Poll every 30 seconds for status updates
    intervalRef.current = setInterval(() => fetchOrder(false), 30_000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [trackingCode])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#001575]" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Pedido no encontrado</h2>
          <p className="text-gray-500 text-sm mb-6">{error || 'Verifica el código de seguimiento.'}</p>
          <Link to="/seguimiento" className="inline-flex items-center gap-2 text-[#001575] font-medium hover:underline">
            <ChevronLeft className="w-4 h-4" />
            Buscar otro pedido
          </Link>
        </div>
      </div>
    )
  }

  const currentStep = getCurrentStepIndex(order.status)
  const isCancelled = order.status === 'cancelled'

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">

        {/* Back + refresh */}
        <div className="flex items-center justify-between mb-6">
          <Link to="/perfil" className="inline-flex items-center gap-2 text-gray-500 hover:text-[#001575] text-sm transition-colors">
            <ChevronLeft className="w-4 h-4" />
            Mis pedidos
          </Link>
          <button
            onClick={() => fetchOrder(false)}
            className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Actualizado {lastRefresh.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
          </button>
        </div>

        {/* Header card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Número de pedido</p>
              <h1 className="text-2xl font-bold text-gray-900">{order.order_number}</h1>
              <p className="text-sm text-gray-500 mt-1">Realizado el {fmtDate(order.created_at)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400 mb-1">Total</p>
              <p className="text-2xl font-bold text-gray-900">{fmt(order.total)}</p>
              <p className="text-xs text-gray-400 mt-1">
                {order.payment_method === 'wompi' ? '💳 Pago en línea' : '💵 Contra entrega'}
              </p>
            </div>
          </div>

          {/* Status badge */}
          <div className={`mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold ${
            isCancelled ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-[#001575]'
          }`}>
            {isCancelled ? <XCircle className="w-4 h-4" /> : <Package className="w-4 h-4" />}
            {STATUS_LABEL[order.status]}
          </div>

          {/* Tracking code */}
          <p className="mt-3 text-xs text-gray-400">
            Código: <span className="font-mono text-gray-600">{order.tracking_code}</span>
          </p>
        </div>

        {/* ── Status timeline ─────────────────────────────────────────────── */}
        {!isCancelled && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
            <h2 className="font-semibold text-gray-900 mb-6">Estado del pedido</h2>
            <div className="relative">
              {/* Progress line */}
              <div className="absolute left-5 top-5 bottom-5 w-0.5 bg-gray-100" />
              <div
                className="absolute left-5 top-5 w-0.5 bg-[#001575] transition-all duration-500"
                style={{ height: `${(currentStep / (STATUS_STEPS.length - 1)) * 100}%` }}
              />

              <div className="space-y-6 relative">
                {STATUS_STEPS.map((step, idx) => {
                  const Icon = step.icon
                  const done = idx <= currentStep
                  const active = idx === currentStep
                  return (
                    <div key={step.key} className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all z-10 ${
                        done
                          ? active
                            ? 'bg-[#001575] shadow-lg shadow-[#001575]/30 scale-110'
                            : 'bg-green-500'
                          : 'bg-gray-100'
                      }`}>
                        <Icon className={`w-5 h-5 ${done ? 'text-white' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <p className={`text-sm font-medium ${done ? 'text-gray-900' : 'text-gray-400'}`}>
                          {step.label}
                        </p>
                        {active && (
                          <p className="text-xs text-[#001575] mt-0.5 font-medium">Estado actual</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── Tracking history ───────────────────────────────────────────── */}
        {order.tracking_history.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
            <h2 className="font-semibold text-gray-900 mb-4">Historial de actualizaciones</h2>
            <div className="space-y-4">
              {[...order.tracking_history].reverse().map((event, idx) => (
                <div key={event.id ?? idx} className="flex items-start gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${idx === 0 ? 'bg-[#001575]' : 'bg-gray-300'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800">{event.description}</p>
                    {event.location && (
                      <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                        <MapPin className="w-3 h-3" /> {event.location}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-0.5">{fmtDate(event.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Products ──────────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-4">Productos ({order.items.length})</h2>
          <div className="space-y-4">
            {order.items.map((item) => (
              <div key={item.id} className="flex items-center gap-4">
                {item.primary_image ? (
                  <img src={item.primary_image} alt={item.product_name}
                    className="w-14 h-14 rounded-xl object-cover flex-shrink-0 border border-gray-100" />
                ) : (
                  <div className="w-14 h-14 rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <Package className="w-6 h-6 text-gray-400" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 text-sm truncate">{item.product_name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Cantidad: {item.quantity} · {fmt(item.unit_price)} c/u
                  </p>
                </div>
                <p className="font-semibold text-gray-900 text-sm flex-shrink-0">{fmt(item.subtotal)}</p>
              </div>
            ))}
          </div>

          <hr className="my-4 border-gray-100" />

          {/* Totals */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal</span><span>{fmt(order.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Envío</span>
              <span>{Number(order.shipping_cost) === 0 ? 'Gratis' : fmt(order.shipping_cost)}</span>
            </div>
            <div className="flex justify-between font-bold text-gray-900 text-base border-t border-gray-100 pt-2">
              <span>Total</span><span>{fmt(order.total)}</span>
            </div>
          </div>
        </div>

        {/* ── Delivery address ──────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Información de entrega</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <div className="flex items-center gap-2.5">
              <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span>{order.customer_name}</span>
            </div>
            <div className="flex items-start gap-2.5">
              <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
              <span>
                {order.shipping_address}
                {order.city ? `, ${order.city}` : ''}
                {order.department ? `, ${order.department}` : ''}
              </span>
            </div>
            <div className="flex items-center gap-2.5">
              <CreditCard className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="font-mono text-xs">{order.tracking_code}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
