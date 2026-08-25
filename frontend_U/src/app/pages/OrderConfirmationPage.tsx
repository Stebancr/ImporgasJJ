import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle, Package, ArrowRight, Loader2 } from 'lucide-react'
import ordersService from '../../services/orders'
import { useCart } from '../../context/CartContext'

interface OrderDetails {
  tracking_code: string
  order_number: string
  total: number
  status: string
  customer_name: string
  payment_method: string
}

function OrderConfirmationPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { clearCart } = useCart()
  const [loading, setLoading] = useState(true)
  const [order, setOrder] = useState<OrderDetails | null>(null)
  const [error, setError] = useState('')

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)

  useEffect(() => {
    const trackingCode = searchParams.get('tracking')
    const reference = searchParams.get('id')

    // Check if there's a pending Wompi order
    const pendingOrder = sessionStorage.getItem('pendingWompiOrder')
    if (pendingOrder) {
      try {
        const orderData = JSON.parse(pendingOrder)
        if (orderData.clearCartOnReturn) {
          clearCart()
          sessionStorage.removeItem('pendingWompiOrder')
        }
      } catch (e) {
        console.error('Error parsing pending order:', e)
      }
    }

    if (!trackingCode && !reference) {
      navigate('/carrito')
      return
    }

    const fetchOrder = async () => {
      try {
        // Buscar por tracking code desde el URL
        if (trackingCode) {
          const data = await ordersService.getByTracking(trackingCode)
          setOrder({
            ...data,
            total: typeof data.total === 'string' ? parseFloat(data.total) : data.total,
          })
        } else if (reference) {
          // Buscar por referencia de Wompi
          const allOrders = await ordersService.getAll({ page: 1, page_size: 1 })
          const found = allOrders.results?.find(
            (o: any) => o.wompi_reference === reference
          )
          if (found) {
            setOrder({
              ...found,
              total: typeof found.total === 'string' ? parseFloat(found.total) : found.total,
            })
          } else {
            setError('No se encontró la orden')
          }
        }
      } catch (err) {
        console.error('Error loading order:', err)
        setError('Error al cargar la orden')
      } finally {
        setLoading(false)
      }
    }

    fetchOrder()
  }, [searchParams, navigate])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFBFC] flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-[#001575] animate-spin" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="min-h-screen bg-[#FAFBFC] py-16">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <div className="bg-white rounded-2xl p-8 shadow-sm">
            <p className="text-[#EF4444] font-medium mb-4">{error || 'Orden no encontrada'}</p>
            <button
              onClick={() => navigate('/carrito')}
              className="text-[#001575] hover:underline"
            >
              Volver al carrito
            </button>
          </div>
        </div>
      </div>
    )
  }

  const isWompi = order.payment_method === 'wompi'
  const isPaid = order.status === 'paid'

  return (
    <div className="min-h-screen bg-[#FAFBFC] py-16">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8 shadow-sm text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-[#D1FAE5] to-[#059669] rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-12 h-12 text-white" />
          </div>

          <h1 className="text-3xl font-bold text-[#1A1D21] mb-4">
            {isPaid ? '¡Pedido Confirmado!' : '¡Pedido Recibido!'}
          </h1>

          <p className="text-lg text-[#6B7280] mb-8">
            {isPaid
              ? 'Tu pago fue procesado exitosamente. Te enviaremos un correo con los detalles de tu pedido.'
              : isWompi
              ? 'Estamos verificando tu pago. Recibirás una confirmación por correo pronto.'
              : 'El pago se realizará contra entrega. Recibirás un correo con los detalles.'}
          </p>

          <div className="bg-[#F9FAFB] rounded-xl p-6 mb-8">
            <div className="grid grid-cols-2 gap-4 text-left">
              <div>
                <p className="text-sm text-[#6B7280] mb-1">Número de Orden</p>
                <p className="font-semibold text-[#1A1D21]">{order.order_number}</p>
              </div>
              <div>
                <p className="text-sm text-[#6B7280] mb-1">Total</p>
                <p className="font-semibold text-[#1A1D21]">{formatPrice(order.total)}</p>
              </div>
              <div>
                <p className="text-sm text-[#6B7280] mb-1">Código de Seguimiento</p>
                <p className="font-mono text-sm text-[#1A1D21]">
                  {order.tracking_code.slice(0, 8)}...
                </p>
              </div>
              <div>
                <p className="text-sm text-[#6B7280] mb-1">Método de Pago</p>
                <p className="font-semibold text-[#1A1D21]">
                  {isWompi ? '💳 Wompi' : '💵 Contra entrega'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate(`/seguimiento-pedido?tracking=${order.tracking_code}`)}
              className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#001575] to-[#00104f] text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#001575]/25 transition-all"
            >
              <Package className="w-5 h-5" />
              Rastrear Pedido
            </button>
            <button
              onClick={() => navigate('/productos')}
              className="inline-flex items-center justify-center gap-2 border-2 border-[#E5E7EB] text-[#4B5563] px-6 py-3 rounded-xl font-semibold hover:border-[#001575] hover:text-[#001575] transition-all"
            >
              Seguir Comprando
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OrderConfirmationPage
