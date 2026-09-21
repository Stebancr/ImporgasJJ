import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  User, Package, ChevronRight, LogOut, Loader2, ShoppingBag,
  MapPin, Phone, Mail, CreditCard, Eye, ExternalLink,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { ordersService } from '../../services/orders'
import type { BackendOrder } from '../../services/orders'
import api from '../../services/api'

// ─── types ────────────────────────────────────────────────────────────────────

interface UserProfile {
  id: number
  cedula: string
  nombre_completo: string
  correo: string
  telefono: string
  estado: number
}

// ─── helpers ──────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<BackendOrder['status'], { label: string; color: string; dot: string }> = {
  pending:   { label: 'Pendiente',    color: 'bg-yellow-50 text-yellow-700 border-yellow-200',   dot: 'bg-yellow-500' },
  paid:      { label: 'Confirmado',   color: 'bg-blue-50 text-blue-700 border-blue-200',         dot: 'bg-blue-500' },
  preparing: { label: 'Preparando',   color: 'bg-indigo-50 text-indigo-700 border-indigo-200',   dot: 'bg-indigo-500' },
  shipping:  { label: 'En camino',    color: 'bg-orange-50 text-orange-700 border-orange-200',   dot: 'bg-orange-500' },
  delivered: { label: 'Entregado',    color: 'bg-green-50 text-green-700 border-green-200',      dot: 'bg-green-500' },
  installed: { label: 'Instalado',    color: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-500' },
  cancelled: { label: 'Cancelado',    color: 'bg-red-50 text-red-600 border-red-200',            dot: 'bg-red-500' },
}

const fmt = (val: string | number) =>
  Number(val).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })

// ─── component ────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile]   = useState<UserProfile | null>(null)
  const [orders, setOrders]     = useState<BackendOrder[]>([])
  const [loading, setLoading]   = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    if (!isAuthenticated) { navigate('/login'); return }

    const load = async () => {
      setLoading(true)
      try {
        const [prof, ords] = await Promise.all([
          api.get<UserProfile>('/user/perfil'),
          ordersService.getMyOrders(),
        ])
        setProfile(prof as unknown as UserProfile)
        setOrders(Array.isArray(ords) ? ords : [])
      } catch { /* silent */ } finally {
        setLoading(false)
      }
    }
    load()
  }, [isAuthenticated, navigate])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Page title */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mi Cuenta</h1>
          <p className="text-gray-500 text-sm mt-0.5">Gestiona tu perfil e historial de compras</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">

          {/* ── Profile card ──────────────────────────────────────────────── */}
          <div className="min-w-0 lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              {/* Avatar */}
              <div className="flex flex-col items-center mb-6">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#001575] to-[#0033cc] flex items-center justify-center text-white text-2xl font-bold shadow-lg mb-3">
                  {profile?.nombre_completo?.charAt(0).toUpperCase() ?? '?'}
                </div>
                <h2 className="font-semibold text-gray-900 text-lg text-center">
                  {profile?.nombre_completo ?? '—'}
                </h2>
                <span className="text-xs text-gray-400 mt-0.5">CC {profile?.cedula ?? '—'}</span>
              </div>

              {/* Info */}
              <div className="space-y-3 text-sm">
                {profile?.correo && (
                  <div className="flex min-w-0 items-center gap-2.5 text-gray-600">
                    <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{profile.correo}</span>
                  </div>
                )}
                {profile?.telefono && (
                  <div className="flex items-center gap-2.5 text-gray-600">
                    <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span>{profile.telefono}</span>
                  </div>
                )}
              </div>

              <Link to="/perfil/editar" className="mt-5 flex items-center justify-center rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-medium text-[#001575] hover:bg-blue-50">Editar perfil y contraseña</Link>

              <hr className="my-5 border-gray-100" />

              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors text-sm font-medium"
              >
                <LogOut className="w-4 h-4" />
                Cerrar sesión
              </button>
            </div>

            {/* Quick links */}
            <div className="mt-4 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              {[
                { to: '/productos', icon: ShoppingBag, label: 'Seguir comprando' },
                { to: '/seguimiento', icon: Package, label: 'Rastrear un pedido' },
              ].map(({ to, icon: Icon, label }) => (
                <Link key={to} to={to}
                  className="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-0 text-sm text-gray-700">
                  <Icon className="w-4 h-4 text-gray-400" />
                  <span className="flex-1">{label}</span>
                  <ChevronRight className="w-4 h-4 text-gray-300" />
                </Link>
              ))}
            </div>
          </div>

          {/* ── Orders section ────────────────────────────────────────────── */}
          <div className="min-w-0 lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Package className="w-5 h-5 text-[#001575]" />
                Mis Pedidos
                {orders.length > 0 && (
                  <span className="ml-1 px-2 py-0.5 rounded-full bg-[#e8ecff] text-[#001575] text-xs font-medium">
                    {orders.length}
                  </span>
                )}
              </h2>
            </div>

            {orders.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
                <ShoppingBag className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Aún no tienes pedidos.</p>
                <Link to="/productos"
                  className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 bg-[#001575] text-white rounded-xl text-sm font-medium hover:bg-[#00104f] transition-colors">
                  <ShoppingBag className="w-4 h-4" />
                  Ver productos
                </Link>
              </div>
            ) : (
              orders.map((order) => {
                const cfg = STATUS_CONFIG[order.status] ?? STATUS_CONFIG.pending
                const isExpanded = expandedId === order.id

                return (
                  <div key={order.id}
                    className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

                    {/* Order header */}
                    <div className="px-5 py-4 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono font-semibold text-gray-900 text-sm">
                          {order.order_number}
                        </span>
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                          {cfg.label}
                        </span>
                        <span className="text-xs text-gray-400">{fmtDate(order.created_at)}</span>
                        <span className="text-xs text-gray-400">
                          {order.payment_method === 'wompi' ? '💳 Wompi' : '💵 Contra entrega'}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-gray-900">{fmt(order.total)}</span>
                        <div className="flex items-center gap-1.5">
                          <Link
                            to={`/pedido/${order.tracking_code}`}
                            className="p-2 rounded-lg bg-[#e8ecff] text-[#001575] hover:bg-[#d0d8ff] transition-colors"
                            title="Ver seguimiento"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : order.id)}
                            className="p-2 rounded-lg bg-gray-50 text-gray-500 hover:bg-gray-100 transition-colors"
                            title={isExpanded ? 'Ocultar' : 'Ver productos'}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Products preview */}
                    <div className="px-5 pb-4 flex items-center gap-3 overflow-x-auto">
                      {order.items.slice(0, 4).map((item) => (
                        <div key={item.id} className="flex items-center gap-2 flex-shrink-0 bg-gray-50 rounded-xl px-3 py-2">
                          {item.primary_image ? (
                            <img src={item.primary_image} alt={item.product_name}
                              className="w-8 h-8 rounded-lg object-cover" />
                          ) : (
                            <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center">
                              <Package className="w-4 h-4 text-gray-400" />
                            </div>
                          )}
                          <div>
                            <p className="text-xs font-medium text-gray-700 max-w-[120px] truncate">{item.product_name}</p>
                            <p className="text-xs text-gray-400">x{item.quantity} · {fmt(item.unit_price)}</p>
                          </div>
                        </div>
                      ))}
                      {order.items.length > 4 && (
                        <span className="text-xs text-gray-400 flex-shrink-0">
                          +{order.items.length - 4} más
                        </span>
                      )}
                    </div>

                    {/* Expanded detail: address + tracking */}
                    {isExpanded && (
                      <div className="border-t border-gray-100 px-5 py-4 space-y-4 bg-gray-50/50">
                        {/* Delivery info */}
                        <div className="flex items-start gap-2 text-sm">
                          <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="font-medium text-gray-700">{order.customer_name}</p>
                            <p className="text-gray-500">{order.shipping_address}{order.city ? `, ${order.city}` : ''}{order.department ? `, ${order.department}` : ''}</p>
                          </div>
                        </div>

                        {/* Tracking code */}
                        <div className="flex items-center gap-2 text-sm">
                          <CreditCard className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          <span className="text-gray-500">Código de seguimiento:</span>
                          <span className="font-mono text-xs text-blue-600 break-all">{order.tracking_code}</span>
                        </div>

                        {/* Last tracking event */}
                        {order.tracking_history.length > 0 && (
                          <div className="text-sm">
                            <p className="text-gray-500 text-xs mb-1">Último estado:</p>
                            <p className="text-gray-700 font-medium">
                              {order.tracking_history[order.tracking_history.length - 1].description}
                            </p>
                          </div>
                        )}

                        <Link
                          to={`/pedido/${order.tracking_code}`}
                          className="inline-flex items-center gap-2 text-sm text-[#001575] font-medium hover:text-[#F58634] hover:underline transition-colors"
                        >
                          Ver seguimiento completo
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
