import './styles/CheckoutPage.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, Truck, Shield, ChevronLeft, Check } from 'lucide-react'

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

const cartSummary = {
  items: [
    { name: 'Calentador de Agua a Gas 13L', price: 650000, quantity: 1 },
    { name: 'Regulador de Gas Alta Presión', price: 85000, quantity: 2 },
  ],
  subtotal: 820000,
  shipping: 0,
  total: 820000,
}

function CheckoutPage() {
  const [step, setStep] = useState<'info' | 'payment' | 'confirm'>('info')
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

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmitInfo = (e: React.FormEvent) => {
    e.preventDefault()
    setStep('payment')
  }

  const handleSubmitPayment = (e: React.FormEvent) => {
    e.preventDefault()
    setStep('confirm')
  }

  const departments = [
    'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá',
    'Caldas', 'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca',
  ]

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
                          <option key={dept} value={dept}>
                            {dept}
                          </option>
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
              <form onSubmit={handleSubmitPayment} className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Método de Pago</h2>

                <div className="space-y-4">
                  <label className={`block p-4 border-2 rounded-xl cursor-pointer transition-colors ${form.paymentMethod === 'wompi' ? 'border-blue-600 bg-blue-50' : 'border-gray-200'}`}>
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
                        <p className="text-sm text-gray-500">Tarjeta de crédito, débito, PSE, Nequi</p>
                      </div>
                    </div>
                  </label>

                  <label className={`block p-4 border-2 rounded-xl cursor-pointer transition-colors ${form.paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50' : 'border-gray-200'}`}>
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
                        <span className="text-lg">💵</span>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">Pago Contra Entrega</p>
                        <p className="text-sm text-gray-500">Paga en efectivo al recibir tu pedido</p>
                      </div>
                    </div>
                  </label>
                </div>

                <div className="flex gap-4 mt-6">
                  <button
                    type="button"
                    onClick={() => setStep('info')}
                    className="flex-1 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Atrás
                  </button>
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                  >
                    Confirmar Pedido
                  </button>
                </div>
              </form>
            )}

            {/* Confirmation Step */}
            {step === 'confirm' && (
              <div className="bg-white rounded-xl p-8 shadow-sm text-center">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Check className="w-10 h-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">¡Pedido Confirmado!</h2>
                <p className="text-gray-600 mb-6">
                  Tu pedido #GS-2024-001234 ha sido procesado exitosamente.
                  <br />
                  Recibirás un correo de confirmación en {form.email}
                </p>
                <div className="bg-gray-50 rounded-xl p-6 mb-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Próximos Pasos</h3>
                  <div className="space-y-3 text-left">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-blue-600">1</span>
                      </div>
                      <p className="text-sm text-gray-600">Recibirás un correo con los detalles de tu pedido</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-blue-600">2</span>
                      </div>
                      <p className="text-sm text-gray-600">Te notificaremos cuando tu pedido sea enviado</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-blue-600">3</span>
                      </div>
                      <p className="text-sm text-gray-600">Coordinaremos la instalación contigo</p>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    to="/seguimiento"
                    className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                  >
                    Ver Estado del Pedido
                  </Link>
                  <Link
                    to="/"
                    className="flex-1 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Volver al Inicio
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
                {cartSummary.items.map((item, index) => (
                  <div key={index} className="flex justify-between gap-4">
                    <div>
                      <p className="text-gray-900 font-medium line-clamp-1">{item.name}</p>
                      <p className="text-sm text-gray-500">Cantidad: {item.quantity}</p>
                    </div>
                    <p className="font-medium text-gray-900 flex-shrink-0">{formatPrice(item.price * item.quantity)}</p>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="font-medium">{formatPrice(cartSummary.subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Envío</span>
                  <span className="text-green-600 font-medium">Gratis</span>
                </div>
                <div className="border-t pt-3">
                  <div className="flex justify-between">
                    <span className="text-lg font-semibold text-gray-900">Total</span>
                    <span className="text-lg font-bold text-gray-900">{formatPrice(cartSummary.total)}</span>
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
