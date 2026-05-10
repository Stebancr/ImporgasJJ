import './styles/CartPage.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, Minus, Plus, ShoppingBag, ArrowRight, ShieldCheck, Truck, Tag } from 'lucide-react'
import { CartItem } from '../../types'

// Mock cart data
const initialCartItems: CartItem[] = [
  {
    product: {
      id: '1',
      name: 'Calentador de Agua a Gas 13L Premium',
      description: 'Calentador de paso de alta eficiencia con encendido electronico',
      price: 650000,
      originalPrice: 750000,
      category: 'calentadores',
      brand: 'Haceb',
      images: ['https://placehold.co/120x120/FF6B35/white?text=Calentador'],
      rating: 5,
      reviewsCount: 128,
      stock: 15,
      specifications: {},
      isAvailable: true,
      discount: 13,
    },
    quantity: 1,
  },
  {
    product: {
      id: '3',
      name: 'Regulador de Gas Alta Presion Industrial',
      description: 'Regulador industrial certificado con valvula de seguridad',
      price: 85000,
      category: 'reguladores',
      brand: 'Fisher',
      images: ['https://placehold.co/120x120/10B981/white?text=Regulador'],
      rating: 5,
      reviewsCount: 234,
      stock: 50,
      specifications: {},
      isAvailable: true,
    },
    quantity: 2,
  },
]

function CartPage() {
  const [cartItems, setCartItems] = useState<CartItem[]>(initialCartItems)
  const [couponCode, setCouponCode] = useState('')

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const updateQuantity = (productId: string, newQuantity: number) => {
    if (newQuantity < 1) return
    setCartItems((prev) =>
      prev.map((item) =>
        item.product.id === productId
          ? { ...item, quantity: Math.min(newQuantity, item.product.stock) }
          : item
      )
    )
  }

  const removeItem = (productId: string) => {
    setCartItems((prev) => prev.filter((item) => item.product.id !== productId))
  }

  const subtotal = cartItems.reduce((sum, item) => sum + item.product.price * item.quantity, 0)
  const shipping = subtotal >= 500000 ? 0 : 25000
  const total = subtotal + shipping

  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-[#FAFBFC] py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="w-28 h-28 bg-[#F3F4F6] rounded-full flex items-center justify-center mx-auto mb-6">
            <ShoppingBag className="w-14 h-14 text-[#9CA3AF]" />
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold text-[#1A1D21] mb-3">Tu carrito esta vacio</h1>
          <p className="text-[#6B7280] mb-8 text-lg">Agrega productos para comenzar tu compra</p>
          <Link
            to="/productos"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white px-8 py-4 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#0066FF]/25 hover:-translate-y-0.5 transition-all"
          >
            Ver Productos
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#FAFBFC] py-8 lg:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-2">Carrito de Compras</h1>
          <p className="text-[#6B7280]">{cartItems.length} {cartItems.length === 1 ? 'producto' : 'productos'} en tu carrito</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            {cartItems.map((item) => (
              <div 
                key={item.product.id} 
                className="bg-white rounded-2xl border border-[#E5E7EB] p-4 sm:p-6 hover:border-[#0066FF]/20 hover:shadow-lg transition-all"
              >
                <div className="flex gap-4 sm:gap-6">
                  <Link to={`/producto/${item.product.id}`} className="flex-shrink-0">
                    <div className="relative">
                      <img
                        src={item.product.images[0]}
                        alt={item.product.name}
                        className="w-24 h-24 sm:w-32 sm:h-32 object-cover rounded-xl"
                      />
                      {item.product.discount && (
                        <span className="absolute -top-2 -right-2 w-10 h-10 bg-gradient-to-br from-[#EF4444] to-[#DC2626] text-white text-xs font-bold rounded-full flex items-center justify-center">
                          -{item.product.discount}%
                        </span>
                      )}
                    </div>
                  </Link>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between gap-4">
                      <div>
                        <span className="inline-block text-xs font-medium text-[#0066FF] bg-[#E6F0FF] px-2 py-0.5 rounded-md mb-2">
                          {item.product.brand}
                        </span>
                        <Link
                          to={`/producto/${item.product.id}`}
                          className="block font-semibold text-[#1A1D21] hover:text-[#0066FF] transition-colors line-clamp-2 text-lg"
                        >
                          {item.product.name}
                        </Link>
                        <p className="text-sm text-[#6B7280] mt-1 line-clamp-1">{item.product.description}</p>
                      </div>
                      <button
                        onClick={() => removeItem(item.product.id)}
                        className="w-10 h-10 flex items-center justify-center text-[#9CA3AF] hover:text-[#EF4444] hover:bg-[#FEE2E2] rounded-xl transition-all flex-shrink-0"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      {/* Quantity Controls */}
                      <div className="flex items-center bg-[#F3F4F6] rounded-xl p-1">
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                          className="w-10 h-10 flex items-center justify-center hover:bg-white rounded-lg transition-colors"
                        >
                          <Minus className="w-4 h-4 text-[#4B5563]" />
                        </button>
                        <span className="w-12 text-center font-semibold text-[#1A1D21]">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                          className="w-10 h-10 flex items-center justify-center hover:bg-white rounded-lg transition-colors"
                        >
                          <Plus className="w-4 h-4 text-[#4B5563]" />
                        </button>
                      </div>

                      {/* Price */}
                      <div className="text-right">
                        <p className="text-xl font-bold text-[#1A1D21]">
                          {formatPrice(item.product.price * item.quantity)}
                        </p>
                        {item.quantity > 1 && (
                          <p className="text-sm text-[#6B7280]">
                            {formatPrice(item.product.price)} c/u
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Features Banner */}
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-4 sm:p-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#D1FAE5] rounded-xl flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5 text-[#059669]" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1A1D21] text-sm">Compra Segura</p>
                    <p className="text-xs text-[#6B7280]">Pago encriptado</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#E6F0FF] rounded-xl flex items-center justify-center">
                    <Truck className="w-5 h-5 text-[#0066FF]" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1A1D21] text-sm">Envio Gratis</p>
                    <p className="text-xs text-[#6B7280]">En compras +$500K</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 sticky top-28">
              <h2 className="text-xl font-bold text-[#1A1D21] mb-6">Resumen del Pedido</h2>

              {/* Coupon Code */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-[#4B5563] mb-2">Codigo de descuento</label>
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={couponCode}
                      onChange={(e) => setCouponCode(e.target.value)}
                      placeholder="Ingresa tu codigo"
                      className="w-full pl-10 pr-4 py-3 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all text-sm"
                    />
                    <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                  </div>
                  <button className="px-4 py-3 bg-[#F3F4F6] text-[#4B5563] rounded-xl font-medium hover:bg-[#E5E7EB] transition-colors">
                    Aplicar
                  </button>
                </div>
              </div>

              <div className="space-y-4 mb-6">
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Subtotal ({cartItems.length} productos)</span>
                  <span className="font-medium text-[#1A1D21]">{formatPrice(subtotal)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Envio</span>
                  {shipping === 0 ? (
                    <span className="font-medium text-[#059669]">Gratis</span>
                  ) : (
                    <span className="font-medium text-[#1A1D21]">{formatPrice(shipping)}</span>
                  )}
                </div>
                {shipping > 0 && (
                  <div className="flex items-center gap-2 p-3 bg-[#E6F0FF] rounded-xl">
                    <Truck className="w-5 h-5 text-[#0066FF]" />
                    <p className="text-sm text-[#0066FF]">
                      Agrega {formatPrice(500000 - subtotal)} mas para envio gratis
                    </p>
                  </div>
                )}
                <div className="border-t border-[#E5E7EB] pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-semibold text-[#1A1D21]">Total</span>
                    <span className="text-2xl font-bold text-[#1A1D21]">{formatPrice(total)}</span>
                  </div>
                </div>
              </div>

              <Link
                to="/checkout"
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white py-4 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#0066FF]/25 hover:-translate-y-0.5 active:translate-y-0 transition-all"
              >
                Proceder al Pago
                <ArrowRight className="w-5 h-5" />
              </Link>

              <Link
                to="/productos"
                className="w-full flex items-center justify-center gap-2 mt-4 py-3 text-[#0066FF] font-medium hover:bg-[#E6F0FF] rounded-xl transition-colors"
              >
                Continuar Comprando
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CartPage
