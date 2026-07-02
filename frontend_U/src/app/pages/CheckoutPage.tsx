import './styles/CheckoutPage.css'
import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreditCard, Truck, Shield, ChevronLeft, Check } from 'lucide-react'
import { useCart } from '../../context/CartContext'
import WompiCheckout from '../../components/WompiCheckout'
import ordersService from '../../services/orders'

// Replace with your real Wompi public key from https://comercios.wompi.co
const WOMPI_PUBLIC_KEY = import.meta.env.VITE_WOMPI_PUBLIC_KEY ?? 'pub_test_YOUR_KEY_HERE'

interface CheckoutForm {
  email: string
  name: string
  phone: string
  address: string
  city: string
  department: string
  postalCode: string
  paymentMethod: 'wompi' | 'cash'
}

function CheckoutPage() {
  const { items, clearCart } = useCart()
  const navigate = useNavigate()
  const [step, setStep] = useState<'info' | 'payment' | 'confirm'>('info')
  const [submitting, setSubmitting] = useState(false)
  const [orderTrackingCode, setOrderTrackingCode] = useState<string>('')
  const [form, setForm] = useState<CheckoutForm>({
    email: '',
    name: '',
    phone: '',
    address: '',
    city: '',
    department: '',
    postalCode: '',
    paymentMethod: 'wompi',
  })

  const subtotal = useMemo(
    () => items.reduce((sum, item) => sum + item.product.price * item.quantity, 0),
    [items]
  )
  const shipping = subtotal >= 500000 ? 0 : 25000
  const total = subtotal + shipping
  const amountInCents = total * 100

  // Unique reference per session
  const reference = useMemo(
    () => `GS-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`,
    []
  )

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmitInfo = (e: React.FormEvent) => {
    e.preventDefault()
    setStep('payment')
  }

  const handleCashConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const order = await ordersService.create({
        customer_name: form.name,
        customer_email: form.email,
        customer_phone: form.phone,
        shipping_address: form.address,
        city: form.city,
        department: form.department,
        postal_code: form.postalCode,
        payment_method: 'cash',
        wompi_reference: reference,
        items: items.map((i) => ({
          product_id: parseInt(i.product.id),
          quantity: i.quantity,
        })),
      })
      setOrderTrackingCode(String(order.tracking_code ?? order.id))
      clearCart()
      setStep('confirm')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error al procesar el pedido'
      alert(message)
    } finally {
      setSubmitting(false)
    }
  }

  const departments = [
    'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá',
    'Caldas', 'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca',
    'Guainía', 'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño',
    'Norte de Santander', 'Putumayo', 'Quindío', 'Risaralda', 'San Andrés', 'Santander',
    'Sucre', 'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada',
  ]

  if (items.length === 0 && step !== 'confirm') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">No tienes productos en el carrito</p>
          <Link to="/productos" className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700">
            Ver Productos
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="checkout-page bg-gray-50 min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Link */}
        <Link to="/carrito" className="inline-flex items-center gap-2 text-gray-600 hover:text-blue-600 mb-8">
          <ChevronLeft className="w-5 h-5" />
          Volver al carrito
        </Link>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Checkout Form */}
          <div className="lg:col-span-2">
            {/* Progress Steps */}
            <div className="flex items-center mb-8 overflow-x-auto pb-1 -mx-1 px-1">
              {[
                { key: 'info', label: 'Información' },
                { key: 'payment', label: 'Pago' },
                { key: 'confirm', label: 'Confirmación' },
              ].map((s, index) => (
                <div key={s.key} className="flex items-center flex-shrink-0">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                      step === s.key
                        ? 'bg-blue-600 text-white'
                        : (step === 'payment' && index === 0) || (step === 'confirm' && index <= 1)
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    {(step === 'payment' && index === 0) || (step === 'confirm' && index <= 1) ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span className={`ml-2 text-sm ${step === s.key ? 'font-semibold text-gray-900' : 'text-gray-500'} hidden xs:inline sm:inline`}>
                    {s.label}
                  </span>
                  {index < 2 && <div className="w-6 sm:w-12 h-0.5 bg-gray-200 mx-2 flex-shrink-0" />}
                </div>
              ))}
            </div>

            {/* Information Step */}
            {step === 'info' && (
              <form onSubmit={handleSubmitInfo} className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Información de Envío</h2>

                <div className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
                      <input
                        type="text"
                        name="name"
                        value={form.name}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Juan Pérez"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
                      <input
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="juan@email.com"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                    <input
                      type="tel"
                      name="phone"
                      value={form.phone}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="+57 300 123 4567"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
                    <input
                      type="text"
                      name="address"
                      value={form.address}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Calle 123 #45-67, Apto 101"
                    />
                  </div>

                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad</label>
                      <input
                        type="text"
                        name="city"
                        value={form.city}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Bogotá"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
                      <select
                        name="department"
                        value={form.department}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Seleccionar</option>
                        {departments.map((dept) => (
                          <option key={dept} value={dept}>{dept}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
                      <input
                        type="text"
                        name="postalCode"
                        value={form.postalCode}
                        onChange={handleInputChange}
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="110111"
                      />
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full mt-6 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                >
                  Continuar al Pago
                </button>
              </form>
            )}

            {/* Payment Step */}
            {step === 'payment' && (
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Método de Pago</h2>

                <div className="space-y-4 mb-6">
                  {/* Wompi Option */}
                  <label
                    className={`block p-4 border-2 rounded-xl cursor-pointer transition-colors ${form.paymentMethod === 'wompi' ? 'border-blue-600 bg-blue-50' : 'border-gray-200'}`}
                  >
                    <div className="flex items-center gap-4">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="wompi"
                        checked={form.paymentMethod === 'wompi'}
                        onChange={handleInputChange}
                        className="w-5 h-5 text-blue-600"
                      />
                      <CreditCard className="w-8 h-8 text-blue-600" />
                      <div>
                        <p className="font-semibold text-gray-900">Pago con Wompi</p>
                        <p className="text-sm text-gray-500">Tarjeta crédito/débito, PSE, Nequi, Bancolombia</p>
                      </div>
                    </div>
                  </label>

                  {/* Cash Option */}
                  <label
                    className={`block p-4 border-2 rounded-xl cursor-pointer transition-colors ${form.paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50' : 'border-gray-200'}`}
                  >
                    <div className="flex items-center gap-4">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="cash"
                        checked={form.paymentMethod === 'cash'}
                        onChange={handleInputChange}
                        className="w-5 h-5 text-blue-600"
                      />
                      <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                        <span className="text-lg">ðŸ’µ</span>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">Pago Contra Entrega</p>
                        <p className="text-sm text-gray-500">Paga en efectivo al recibir tu pedido</p>
                      </div>
                    </div>
                  </label>
                </div>

                {/* Wompi widget */}
                {form.paymentMethod === 'wompi' && (
                  <div className="mb-4">
                    <p className="text-sm text-gray-500 mb-3">
                      Al hacer clic en el botón de Wompi serás redirigido al checkout seguro para completar el pago de{' '}
                      <strong>{formatPrice(total)}</strong>.
                    </p>
                    <WompiCheckout
                      publicKey={WOMPI_PUBLIC_KEY}
                      amountInCents={amountInCents}
                      reference={reference}
                      redirectUrl={`${window.location.origin}/checkout?status=success`}
                      className="flex justify-center"
                    />
                    <p className="text-xs text-gray-400 mt-2 text-center">
                      Tu pedido se registrará automáticamente al confirmar el pago en Wompi.
                    </p>
                  </div>
                )}

                <div className="flex gap-4 mt-4">
                  <button
                    type="button"
                    onClick={() => setStep('info')}
                    className="flex-1 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Atrás
                  </button>
                  {form.paymentMethod === 'cash' && (
                    <button
                      type="button"
                      onClick={handleCashConfirm as unknown as React.MouseEventHandler}
                      disabled={submitting}
                      className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-60"
                    >
                      {submitting ? 'Procesando...' : 'Confirmar Pedido'}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Confirmation Step */}
            {step === 'confirm' && (
              <div className="bg-white rounded-xl p-8 shadow-sm text-center">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Check className="w-10 h-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">¡Pedido Confirmado!</h2>
                <p className="text-gray-600 mb-6">
                  Tu pedido ha sido procesado exitosamente.
                  {orderTrackingCode && (
                    <span className="block mt-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                      <span className="block text-xs text-blue-500 font-medium mb-1">Código de seguimiento</span>
                      <span className="font-mono text-blue-700 font-bold break-all">{orderTrackingCode}</span>
                    </span>
                  )}
                  {form.email && (
                    <span className="block mt-2 text-sm">
                      Recibirás un correo de confirmación en <strong>{form.email}</strong>
                    </span>
                  )}
                </p>
                <div className="bg-gray-50 rounded-xl p-6 mb-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Próximos Pasos</h3>
                  <div className="space-y-3 text-left">
                    {[
                      'Recibirás un correo con los detalles de tu pedido',
                      'Te notificaremos cuando tu pedido sea enviado',
                      'Coordinaremos la instalación contigo',
                    ].map((text, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                          <span className="text-xs font-semibold text-blue-600">{i + 1}</span>
                        </div>
                        <p className="text-sm text-gray-600">{text}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    to={orderTrackingCode ? `/pedido/${orderTrackingCode}` : '/perfil'}
                    className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors text-center"
                  >
                    Ver Estado del Pedido
                  </Link>
                  <Link
                    to="/perfil"
                    className="flex-1 py-3 border border-blue-300 rounded-lg font-semibold text-blue-600 hover:bg-blue-50 transition-colors text-center"
                  >
                    Mis Pedidos
                  </Link>
                  <Link
                    to="/"
                    className="flex-1 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors text-center"
                  >
                    Inicio
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl p-6 shadow-sm lg:sticky lg:top-24">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Resumen del Pedido</h2>

              <div className="space-y-4 mb-6">
                {items.map((item) => (
                  <div key={item.product.id} className="flex justify-between gap-4">
                    <div className="flex gap-3 min-w-0">
                      <img
                        src={item.product.images[0]}
                        alt={item.product.name}
                        className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                      />
                      <div className="min-w-0">
                        <p className="text-gray-900 font-medium line-clamp-1 text-sm">{item.product.name}</p>
                        <p className="text-xs text-gray-500">Cant: {item.quantity}</p>
                      </div>
                    </div>
                    <p className="font-medium text-gray-900 flex-shrink-0 text-sm">
                      {formatPrice(item.product.price * item.quantity)}
                    </p>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="font-medium">{formatPrice(subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Envío</span>
                  {shipping === 0 ? (
                    <span className="text-green-600 font-medium">Gratis</span>
                  ) : (
                    <span className="font-medium">{formatPrice(shipping)}</span>
                  )}
                </div>
                <div className="border-t pt-3">
                  <div className="flex justify-between">
                    <span className="text-lg font-semibold text-gray-900">Total</span>
                    <span className="text-lg font-bold text-gray-900">{formatPrice(total)}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Truck className="w-4 h-4 text-blue-600" />
                  <span>Envío gratis en compras +$500.000</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Shield className="w-4 h-4 text-green-600" />
                  <span>Pago 100% seguro</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CheckoutPage
