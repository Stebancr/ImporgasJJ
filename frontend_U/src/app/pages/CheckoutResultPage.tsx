import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Clock3, Loader2, XCircle } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import paymentsService, { type PaymentResult, type WompiStatus } from '../../services/payments'
import { useCart } from '../../context/CartContext'

const presentation: Record<WompiStatus, { title: string; message: string; color: string }> = {
  APPROVED: { title: 'Pago aprobado', message: 'Tu pago fue confirmado correctamente.', color: 'text-green-600' },
  PENDING: { title: 'Pago pendiente', message: 'Wompi todavía está procesando la transacción.', color: 'text-amber-600' },
  DECLINED: { title: 'Pago rechazado', message: 'La entidad financiera rechazó la transacción.', color: 'text-red-600' },
  VOIDED: { title: 'Pago anulado', message: 'La transacción fue anulada.', color: 'text-red-600' },
  ERROR: { title: 'Error en el pago', message: 'Wompi reportó un error al procesar la transacción.', color: 'text-red-600' },
}

export default function CheckoutResultPage() {
  const [params] = useSearchParams()
  const { clearCart } = useCart()
  const [result, setResult] = useState<PaymentResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const tracking = params.get('tracking') || ''
  const transactionId = params.get('id') || params.get('transaction_id') || ''

  const verify = useCallback(async () => {
    if (!tracking) { setError('No se recibió el código de seguimiento de la compra.'); setLoading(false); return }
    try {
      const data = await paymentsService.getPaymentStatus(tracking, transactionId || undefined)
      setResult(data)
      if (data.payment_status === 'APPROVED') clearCart()
      if (data.payment_status !== 'PENDING') sessionStorage.removeItem('pendingWompiOrder')
    } catch (err) { setError(err instanceof Error ? err.message : 'No fue posible verificar el pago') }
    finally { setLoading(false) }
  }, [tracking, transactionId, clearCart])

  useEffect(() => { void verify() }, [verify])
  useEffect(() => {
    if (result?.payment_status !== 'PENDING') return
    const timer = window.setTimeout(() => void verify(), 5000)
    return () => window.clearTimeout(timer)
  }, [result, verify])

  if (loading) return <div className="flex min-h-[60vh] items-center justify-center"><Loader2 className="h-12 w-12 animate-spin text-blue-700" /></div>
  if (error || !result) return <div className="mx-auto max-w-2xl px-4 py-16 text-center"><AlertCircle className="mx-auto mb-4 h-16 w-16 text-red-500" /><h1 className="text-2xl font-bold">No fue posible verificar el pago</h1><p className="my-4 text-gray-600">{error}</p><Link to="/" className="font-semibold text-blue-700">Volver al inicio</Link></div>
  const info = presentation[result.payment_status]
  const Icon = result.payment_status === 'APPROVED' ? CheckCircle2 : result.payment_status === 'PENDING' ? Clock3 : XCircle
  const canRetry = ['DECLINED', 'VOIDED', 'ERROR'].includes(result.payment_status)
  return <div className="mx-auto max-w-3xl px-4 py-14"><div className="rounded-2xl border bg-white p-8 shadow-sm">
    <Icon className={`mx-auto mb-4 h-20 w-20 ${info.color}`} /><h1 className={`text-center text-3xl font-bold ${info.color}`}>{info.title}</h1><p className="mt-3 text-center text-gray-600">{info.message}</p>
    <dl className="mt-8 grid gap-4 rounded-xl bg-gray-50 p-6 sm:grid-cols-2">
      <div><dt className="text-sm text-gray-500">Orden</dt><dd className="font-semibold">{result.order_number || 'Se creará al aprobarse el pago'}</dd></div><div><dt className="text-sm text-gray-500">Referencia</dt><dd className="break-all font-mono text-sm">{result.reference}</dd></div>
      <div><dt className="text-sm text-gray-500">Monto</dt><dd className="font-semibold">{new Intl.NumberFormat('es-CO', { style: 'currency', currency: result.currency, minimumFractionDigits: 0 }).format(Number(result.amount))}</dd></div><div><dt className="text-sm text-gray-500">Estado real</dt><dd className="font-semibold">{result.payment_status}</dd></div>
    </dl>
    <div className="mt-6"><h2 className="font-semibold">Productos</h2>{result.items.map((item, index) => <p key={`${item.product_name}-${index}`} className="mt-2 text-gray-600">{item.quantity} × {item.product_name}</p>)}</div>
    <div className="mt-8 flex flex-wrap justify-center gap-4"><Link to="/" className="rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white">Ir al inicio</Link>{canRetry && <Link to="/carrito" className="rounded-lg border px-5 py-3 font-semibold">Volver al carrito</Link>}{result.order_number && <Link to={`/pedido/${result.tracking_code}`} className="rounded-lg border px-5 py-3 font-semibold">Ver compra</Link>}</div>
  </div></div>
}
