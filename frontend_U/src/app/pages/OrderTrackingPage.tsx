import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Search, Package, Truck, Home, Check, Clock, Wrench, Loader2, MapPin, CheckCircle } from 'lucide-react'
import api from '../../services/api'
import './styles/OrderTrackingPage.css'

// --- helpers -----------------------------------------------------------------

const statusSteps = [
  { key: 'pending',   label: 'Pedido',       icon: Package },
  { key: 'paid',      label: 'Pagado',        icon: Check },
  { key: 'preparing', label: 'Preparación',   icon: Clock },
  { key: 'shipping',  label: 'En Camino',     icon: Truck },
  { key: 'delivered', label: 'Entregado',     icon: Home },
  { key: 'installed', label: 'Instalado',     icon: Wrench },
]

interface StatusResult {
  found: boolean
  order_number?: string
  tracking_code?: string
  status?: string
  status_label?: string
  customer_name?: string
  total?: string
  created_at?: string
}

// --- component ---------------------------------------------------------------

function OrderTrackingPage() {
  const [searchParams] = useSearchParams()
  const [orderNumber, setOrderNumber] = useState(searchParams.get('code') ?? '')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<StatusResult | null>(null)

  // Auto-search when code is in URL
  useEffect(() => {
    const code = searchParams.get('code')
    if (code) {
      setOrderNumber(code)
      doSearch(code)
    }
  }, [])

  const currentStepIndex = result?.status
    ? statusSteps.findIndex((s) => s.key === result.status)
    : -1

  const doSearch = async (query: string) => {
    const q = query.trim()
    if (!q) { setError('Ingresa el número de pedido o código de seguimiento'); return }

    setIsLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.get<StatusResult>(`/orders/status?q=${encodeURIComponent(q)}`)
      const res = data as unknown as StatusResult
      if (res.found) {
        setResult(res)
      } else {
        setError('No encontramos ningún pedido con ese número. Verifica e intenta de nuevo.')
      }
    } catch {
      setError('Ocurrió un error. Por favor intenta de nuevo.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    doSearch(orderNumber)
  }

  return (
    <div className="tracking-page bg-gray-50 min-h-screen py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Seguimiento de Pedido</h1>
          <p className="text-gray-600">
            Ingresa el número de tu pedido (Ej: ORD-00001) o el código de seguimiento
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <input
                type="text"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                placeholder="Ej: ORD-00001 o código de seguimiento"
                className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
               aria-label="Ej: ORD-00001 o código de seguimiento" />
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="bg-[#001575] text-white px-8 py-4 rounded-xl font-semibold hover:bg-[#00104f] transition-colors disabled:bg-[#001575]/50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-5 h-5 animate-spin" />}
              {isLoading ? 'Buscando...' : 'Buscar Pedido'}
            </button>
          </div>
          {error && (
            <p className="mt-3 text-red-500 text-center text-sm">{error}</p>
          )}
        </form>

        {/* Result or static preview */}
        {result ? (
          <div className="space-y-5">
            {/* Order info + tracking steps */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
                <div>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Número de pedido</p>
                  <p className="text-xl font-bold text-gray-900">{result.order_number}</p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#e8ecff] text-[#001575] rounded-full text-sm font-semibold border border-[#c0caef]">
                  <CheckCircle className="w-4 h-4" />
                  {result.status_label}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm mb-6">
                <div>
                  <p className="text-gray-400 mb-0.5">Cliente</p>
                  <p className="font-medium text-gray-800">{result.customer_name}</p>
                </div>
                <div>
                  <p className="text-gray-400 mb-0.5">Total</p>
                  <p className="font-medium text-gray-800">
                    {Number(result.total).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 mb-0.5">Fecha</p>
                  <p className="font-medium text-gray-800">{result.created_at}</p>
                </div>
              </div>

              {/* Status Steps */}
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center mb-5">
                Seguimiento en tiempo real
              </p>
              <div className="flex items-start justify-between overflow-x-auto pb-1 gap-1">
                {statusSteps.map((step, index) => {
                  const Icon = step.icon
                  const isCompleted = index < currentStepIndex
                  const isCurrent = index === currentStepIndex
                  return (
                    <div key={step.key} className="flex flex-col items-center gap-2 flex-shrink-0 flex-1 min-w-[3.5rem]">
                      <div className={`w-11 h-11 rounded-full border-2 flex items-center justify-center transition-colors ${
                        isCurrent
                          ? 'border-[#F58634] bg-[#F58634] shadow-md shadow-[#F58634]/20'
                          : isCompleted
                          ? 'border-green-500 bg-green-500'
                          : 'border-dashed border-gray-200 bg-gray-50'
                      }`}>
                        <Icon className={`w-5 h-5 ${isCurrent || isCompleted ? 'text-white' : 'text-gray-300'}`} />
                      </div>
                      <p className={`text-xs text-center leading-tight font-medium ${
                        isCurrent ? 'text-[#F58634]' : isCompleted ? 'text-green-600' : 'text-gray-400'
                      }`}>{step.label}</p>
                    </div>
                  )
                })}
              </div>

              {result.tracking_code && (
                <div className="mt-5 pt-5 border-t border-gray-100 text-center">
                  <p className="text-xs text-gray-400 mb-1">Código de seguimiento</p>
                  <p className="font-mono text-sm text-gray-600">{result.tracking_code}</p>
                </div>
              )}
            </div>

            <div className="text-center">
              <button
                onClick={() => { setResult(null); setOrderNumber('') }}
                className="text-sm text-[#001575] hover:text-[#F58634] hover:underline font-medium transition-colors"
              >
                ← Buscar otro pedido
              </button>
            </div>
          </div>
        ) : (
          /* Static preview — shown before any search */
          <div className="space-y-5">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center mb-5">
                Seguimiento en tiempo real
              </p>
              <div className="flex items-start justify-between overflow-x-auto pb-1 gap-1">
                {statusSteps.map((step) => {
                  const Icon = step.icon
                  return (
                    <div key={step.key} className="flex flex-col items-center gap-2 flex-shrink-0 flex-1 min-w-[3.5rem]">
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

            <div className="bg-[#e8ecff] rounded-2xl p-5 border border-[#c0caef]">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-[#c8d3f5] rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                    <MapPin className="w-5 h-5 text-[#001575]" />
                </div>
                <div>
                  <p className="font-semibold text-gray-800 mb-1">¿Dónde encuentro mi código?</p>
                  <p className="text-sm text-gray-600">
                    Busca el número de pedido en el correo de confirmación (Ej: ORD-00001),
                    o el código de seguimiento que aparece en la pantalla de confirmación de tu compra.
                  </p>
                  <Link to="/perfil" className="mt-2 inline-block text-sm text-[#001575] font-medium hover:text-[#F58634] hover:underline transition-colors">
                    Ver mis pedidos →
                  </Link>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-2xl p-6 text-center border border-gray-100">
              <h3 className="font-semibold text-gray-800 mb-2">¿Necesitas ayuda?</h3>
              <p className="text-sm text-gray-500 mb-4">
                Si tienes problemas para encontrar tu pedido, contáctanos.
              </p>
              <a href="/contacto"
                className="inline-flex items-center gap-2 bg-[#001575] text-white px-6 py-2.5 rounded-xl font-medium hover:bg-[#00104f] transition-colors text-sm">
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