import './styles/CheckoutPage.css'
import { useState, useMemo, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreditCard, Truck, Shield, ChevronLeft, Check, MapPin } from 'lucide-react'
import { useCart } from '../../context/CartContext'
import { useAuth } from '../../context/AuthContext'
import ordersService from '../../services/orders'
import { getWompiOptions, loadWompiWidget } from '../../services/wompiCheckout'
import addressesService, { UserAddress } from '../../services/addresses'
import { shippingService, type ShippingQuote, type TCCAddress } from '../../services/shipping'
import TCCAddressFields from '../../components/TCCAddressFields'
import { shippingDestinationKey } from '../../services/shipping'

// La llave pública puede incluirse en el bundle; los secretos permanecen sólo
// en Django. El backend también devuelve esta llave con la intención de pago.
const WOMPI_PUBLIC_KEY = import.meta.env.VITE_WOMPI_PUBLIC_KEY ?? ''
const CASH_ON_DELIVERY_ENABLED = false

interface CheckoutForm extends TCCAddress {
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
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState<'info' | 'payment'>('info')
  const [submitting, setSubmitting] = useState(false)
  const paymentLock = useRef(false)
  const [addresses, setAddresses] = useState<UserAddress[]>([])
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null)
  const [tccEnabled,setTccEnabled]=useState<boolean|null>(null)
  const [requiresConfirmation,setRequiresConfirmation]=useState(true)
  const [shippingError,setShippingError]=useState('')
  const [quoting,setQuoting]=useState(false)
  const [quoted,setQuoted]=useState<{key:string;value:ShippingQuote}|null>(null)
  const [quoteVersion,setQuoteVersion]=useState(0)
  const [form, setForm] = useState<CheckoutForm>({
    tcc_city_code:'',complement:'',neighborhood:'',delivery_instructions:'',
    email: '',
    name: '',
    phone: '',
    address: '',
    city: '',
    department: '',
    postalCode: '',
    paymentMethod: 'wompi',
  })
  useEffect(()=>{shippingService.config().then(config=>{setTccEnabled(config.enabled);setRequiresConfirmation(config.requires_shipping_confirmation===true);if(config.requires_shipping_confirmation&&!config.enabled)setShippingError('Envío pendiente por confirmar. Contacta al asesor antes de pagar.')}).catch(()=>setShippingError('No fue posible verificar el transporte. Actualiza la página antes de pagar.'))},[])
  const quoteKey=JSON.stringify({items:items.map(item=>({product_id:Number(item.product.id),quantity:item.quantity})),form,address_id:selectedAddressId})
  const activeQuote=quoted?.key===quoteKey && Date.parse(quoted.value.expires_at)>Date.now()?quoted.value:null
  useEffect(()=>{
    let active=true
    setQuoted(null)
    if(tccEnabled!==true)return
    setShippingError('')
    if(!form.email||!form.name||!form.phone||!form.address||!form.tcc_city_code){setQuoting(false);return}
    setQuoting(true)
    const timer=setTimeout(()=>{
      shippingService.quote({force:quoteVersion>0,items:items.map(item=>({product_id:Number(item.product.id),quantity:item.quantity})),
        address_id:selectedAddressId,customer_name:form.name,customer_email:form.email,customer_phone:form.phone,
        shipping_address:form.address,city:form.city,department:form.department,postal_code:form.postalCode,
        tcc_city_code:form.tcc_city_code,complement:form.complement,neighborhood:form.neighborhood,delivery_instructions:form.delivery_instructions})
        .then(value=>{if(active)setQuoted({key:quoteKey,value})})
        .catch((e:unknown)=>{if(active)setShippingError(e instanceof Error?e.message:'No fue posible cotizar el transporte.')})
        .finally(()=>{if(active)setQuoting(false)})
    },500)
    return()=>{active=false;clearTimeout(timer)}
  },[quoteKey,tccEnabled,quoteVersion])
  useEffect(()=>{
    if(!quoted)return
    const timer=setTimeout(()=>setQuoteVersion(value=>value+1),Math.max(0,Date.parse(quoted.value.expires_at)-Date.now()))
    return()=>clearTimeout(timer)
  },[quoted])

  // Load user data and addresses if authenticated
  useEffect(() => {
    if (isAuthenticated && user?.usuario_rel) {
      setForm((prev) => ({
        ...prev,
        email: user.usuario_rel?.correo || '',
        name: user.usuario_rel?.nombre_completo || '',
        phone: user.usuario_rel?.telefono || '',
      }))
      
      // Load addresses
      loadAddresses()
    }
  }, [isAuthenticated, user])

  const loadAddresses = async () => {
    try {
      const data = await addressesService.getAll()
      setAddresses(data)
      // Auto-select default address
      let defaultAddr = data.find((addr) => addr.is_default)
      try {
        const draft = user?.id ? JSON.parse(sessionStorage.getItem(shippingDestinationKey(user.id)) || 'null') : null
        if (draft && typeof draft === 'object' && !Array.isArray(draft)) {
          if (draft.address_id) defaultAddr = data.find(addr => addr.id === draft.address_id) || defaultAddr
          else if (typeof draft.tcc_city_code === 'string') {
            const text = (key:string) => typeof draft[key] === 'string' ? draft[key] : ''
            setSelectedAddressId(null)
            setForm(previous => ({...previous, name:text('customer_name')||previous.name, phone:text('customer_phone')||previous.phone,
              address:text('shipping_address'), city:text('city'), department:text('department'), postalCode:text('postal_code'),
              tcc_city_code:text('tcc_city_code'), complement:text('complement'), neighborhood:text('neighborhood'),
              delivery_instructions:text('delivery_instructions')}))
            return
          }
        }
      } catch { /* Invalid or unavailable browser storage never replaces a saved address. */ }
      if (defaultAddr) {
        setSelectedAddressId(defaultAddr.id)
        setForm(prev => ({ ...prev, name: defaultAddr.recipient_name, phone: defaultAddr.phone,
          address: defaultAddr.address, city: defaultAddr.city, department: defaultAddr.department,
          postalCode: defaultAddr.postal_code || '' }))
        setForm(prev=>({...prev,tcc_city_code:defaultAddr.tcc_city_code||'',complement:defaultAddr.complement||'',neighborhood:defaultAddr.neighborhood||'',delivery_instructions:defaultAddr.delivery_instructions||''}))
      }
    } catch (error) {
      console.error('Error loading addresses:', error)
    }
  }

  const handleSelectAddress = (addressId: number) => {
    const addr = addresses.find((a) => a.id === addressId)
    if (addr) {
      setSelectedAddressId(addressId)
      setForm((prev) => ({
        ...prev,
        name: addr.recipient_name,
        phone: addr.phone,
        address: addr.address,
        city: addr.city,
        department: addr.department,
        postalCode: addr.postal_code || '',
        tcc_city_code:addr.tcc_city_code||'',complement:addr.complement||'',neighborhood:addr.neighborhood||'',delivery_instructions:addr.delivery_instructions||'',
      }))
    }
  }

  const subtotal = useMemo(
    () => items.reduce((sum, item) => sum + item.product.price * item.quantity, 0),
    [items]
  )
  const shipping = (tccEnabled===null || (requiresConfirmation&&!tccEnabled)) ? null : tccEnabled ? (activeQuote?Number(activeQuote.total):null) : (subtotal >= 500000 ? 0 : 25000)
  const total = activeQuote?Number(activeQuote.order_total):subtotal+(shipping??0)


  // Unique reference per session
  const reference = useMemo(
    () => `GS-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`,
    [activeQuote?.id]
  )

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    if(!['email','paymentMethod'].includes(e.target.name))setSelectedAddressId(null)
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmitInfo = (e: React.FormEvent) => {
    e.preventDefault()
    if((requiresConfirmation&&!tccEnabled) || tccEnabled===null || (tccEnabled && !activeQuote)){
      setShippingError('Completa la dirección y espera una cotización vigente antes de pagar.');return
    }
    if (items.some((item) => !Number.isInteger(item.quantity) || item.quantity < 1)) {
      alert('El carrito contiene una cantidad inválida. Regresa al carrito y vuelve a agregar el producto.')
      return
    }
    setStep('payment')
  }

  const handleCashConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!CASH_ON_DELIVERY_ENABLED) return
    if (submitting) return
    setSubmitting(true)
    try {
      const order = await ordersService.create({
        shipping_quote_id:activeQuote?.id,address_id:selectedAddressId,
        tcc_city_code:form.tcc_city_code,complement:form.complement,neighborhood:form.neighborhood,delivery_instructions:form.delivery_instructions,
        customer_name: form.name,
        customer_email: form.email,
        customer_phone: form.phone,
        shipping_address: form.address,
        city: form.city,
        department: form.department,
        postal_code: form.postalCode,
        payment_method: 'cash',
        items: items.map((i) => ({
          product_id: parseInt(i.product.id),
          quantity: i.quantity,
        })),
      })
      await clearCart()
      navigate(`/orden-confirmada?tracking=${order.tracking_code}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error al procesar el pedido'
      alert(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleWompiConfirm = async () => {
    if((requiresConfirmation&&!tccEnabled) || tccEnabled===null || (tccEnabled && !activeQuote)){setShippingError('Actualiza la cotización antes de pagar.');return null}
    if (paymentLock.current) return
    paymentLock.current = true
    setSubmitting(true)
    try {
      const paymentIntent = await ordersService.createWompiIntent({
        shipping_quote_id:activeQuote?.id,address_id:selectedAddressId,
        tcc_city_code:form.tcc_city_code,complement:form.complement,neighborhood:form.neighborhood,delivery_instructions:form.delivery_instructions,
        customer_name: form.name,
        customer_email: form.email,
        customer_phone: form.phone,
        shipping_address: form.address,
        city: form.city,
        department: form.department,
        postal_code: form.postalCode,
        payment_method: 'wompi',
        wompi_reference: reference,
        items: items.map((i) => ({
          product_id: parseInt(i.product.id),
          quantity: i.quantity,
        })),
      })
      
      const options = getWompiOptions(paymentIntent, WOMPI_PUBLIC_KEY, form.email, form.name)
      const Widget = await loadWompiWidget()
      sessionStorage.setItem('pendingWompiOrder', JSON.stringify({
        tracking_code: paymentIntent.tracking_code, reference: paymentIntent.wompi_reference,
      }))
      new Widget(options).open((result) => {
        if (!result.transaction?.id) return
        const query = new URLSearchParams({ tracking: paymentIntent.tracking_code, id: result.transaction.id })
        navigate('/checkout/resultado?' + query.toString())
      })
      setSubmitting(false)
      paymentLock.current = false

      return paymentIntent
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error al procesar el pedido'
      alert(message)
      if(tccEnabled)setQuoteVersion(value=>value+1)
      setSubmitting(false)
      paymentLock.current = false
      return null
    }
  }

  const departments = [
    'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá',
    'Caldas', 'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca',
    'Guainía', 'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño',
    'Norte de Santander', 'Putumayo', 'Quindío', 'Risaralda', 'San Andrés', 'Santander',
    'Sucre', 'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada',
  ]

  if (items.length === 0) {
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
              ].map((s, index) => (
                <div key={s.key} className="flex items-center flex-shrink-0">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                      step === s.key
                        ? 'bg-blue-600 text-white'
                        : step === 'payment' && index === 0
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    {step === 'payment' && index === 0 ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span className={`ml-2 text-sm ${step === s.key ? 'font-semibold text-gray-900' : 'text-gray-500'} hidden xs:inline sm:inline`}>
                    {s.label}
                  </span>
                  {index < 1 && <div className="w-6 sm:w-12 h-0.5 bg-gray-200 mx-2 flex-shrink-0" />}
                </div>
              ))}
            </div>

            {/* Information Step */}
            {step === 'info' && (
              <form onSubmit={handleSubmitInfo} className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Información de Envío</h2>

                {/* Saved Addresses Selector */}
                {isAuthenticated && addresses.length > 0 && (
                  <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                    <div className="flex items-center gap-2 mb-3">
                      <MapPin className="w-5 h-5 text-blue-600" />
                      <h3 className="font-semibold text-gray-900">Direcciones guardadas</h3>
                    </div>
                    <div className="space-y-2">
                      {addresses.map((addr) => (
                        <button
                          key={addr.id}
                          type="button"
                          onClick={() => handleSelectAddress(addr.id)}
                          className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                            selectedAddressId === addr.id
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-200 bg-white hover:border-blue-300'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-semibold text-gray-900">{addr.label}</p>
                              <p className="text-sm text-gray-600">{addr.recipient_name}</p>
                              <p className="text-sm text-gray-600">{addr.address}</p>
                              <p className="text-sm text-gray-600">
                                {addr.city}, {addr.department}
                              </p>
                            </div>
                            {selectedAddressId === addr.id && (
                              <Check className="w-5 h-5 text-blue-600 flex-shrink-0" />
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                    <Link
                      to="/direcciones"
                      className="mt-3 inline-block text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Administrar direcciones →
                    </Link>
                  </div>
                )}

                <div className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="checkout-name" className="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
                      <input
                        type="text"
                        name="name" id="checkout-name" autoComplete="name"
                        value={form.name}
                        onChange={handleInputChange}
                        required
                        className="min-w-0 min-h-11 w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Juan Pérez" />
                    </div>
                    <div>
                      <label htmlFor="checkout-email" className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
                      <input
                        type="email"
                        name="email" id="checkout-email" autoComplete="email"
                        value={form.email}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="juan@email.com" />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="checkout-phone" className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                    <input
                      type="tel"
                      name="phone" id="checkout-phone" autoComplete="tel"
                      value={form.phone}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="+57 300 123 4567" />
                  </div>

                  <div>
                    <label htmlFor="checkout-address" className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
                    <input
                      type="text"
                      name="address" id="checkout-address" autoComplete="street-address"
                      value={form.address}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Calle 123 #45-67, Apto 101" />
                  </div>

                  {tccEnabled && <TCCAddressFields value={form} onChange={patch=>{setSelectedAddressId(null);setForm(prev=>({...prev,...patch}))}}/>}
                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor="checkout-city" className="block text-sm font-medium text-gray-700 mb-1">Ciudad</label>
                      <input
                        type="text"
                        name="city" id="checkout-city" autoComplete="address-level2"
                        readOnly={!!tccEnabled}
                        value={form.city}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Bogotá" />
                    </div>
                    <div>
                      <label htmlFor="checkout-department" className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
                      <select
                        name="department" id="checkout-department" autoComplete="address-level1"
                        disabled={!!tccEnabled}
                        value={form.department}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Seleccionar</option>
                        {tccEnabled && form.department && <option value={form.department}>{form.department}</option>}
                        {departments.map((dept) => (
                          <option key={dept} value={dept}>{dept}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="checkout-postalCode" className="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
                      <input
                        type="text"
                        name="postalCode" id="checkout-postalCode" autoComplete="postal-code"
                        value={form.postalCode}
                        onChange={handleInputChange}
                        className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="110111" />
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={(requiresConfirmation&&!tccEnabled) || tccEnabled===null || (tccEnabled && (!activeQuote||quoting))}
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

                  {/* Cash Option: retained for a future reactivation. */}
                  {CASH_ON_DELIVERY_ENABLED && <label
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
                  </label>}
                </div>

                {/* Wompi info */}
                {form.paymentMethod === 'wompi' && (
                  <div className="mb-4 p-4 bg-blue-50 rounded-xl">
                    <p className="text-sm text-blue-800">
                      Al hacer clic en <strong>"Pagar con Wompi"</strong> abriremos el checkout seguro de Wompi
                      para completar el pago de <strong>{formatPrice(total)}</strong>. La orden se creará cuando Wompi confirme el pago.
                    </p>
                    <p className="text-xs text-blue-600 mt-2">
                      Acepta tarjetas crédito/débito, PSE, Nequi, Bancolombia y más.
                    </p>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-4 mt-4">
                  <button
                    type="button"
                    onClick={() => setStep('info')}
                    className="flex-1 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Atrás
                  </button>
                  {CASH_ON_DELIVERY_ENABLED && form.paymentMethod === 'cash' ? (
                    <button
                      type="button"
                      onClick={handleCashConfirm as unknown as React.MouseEventHandler}
                      disabled={submitting||(requiresConfirmation&&!tccEnabled)||tccEnabled===null||(!!tccEnabled&&!activeQuote)}
                      className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-60"
                    >
                      {submitting ? 'Procesando...' : 'Confirmar Pedido'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleWompiConfirm}
                      disabled={submitting||(requiresConfirmation&&!tccEnabled)||tccEnabled===null||(!!tccEnabled&&!activeQuote)}
                      className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg font-semibold hover:shadow-lg transition-all disabled:opacity-60 flex items-center justify-center gap-2"
                    >
                      {submitting ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                          Procesando...
                        </>
                      ) : (
                        <>
                          <CreditCard className="w-5 h-5" />
                          Pagar con Wompi
                        </>
                      )}
                    </button>
                  )}
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
                <div className="flex justify-between text-sm"><span>Descuentos adicionales</span><span>{formatPrice(Number(activeQuote?.discounts||0))}</span></div>
                <div className="flex justify-between text-sm"><span>Impuestos adicionales</span><span>{formatPrice(Number(activeQuote?.taxes||0))}</span></div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Envío</span>
                  {shipping === 0 ? (
                    <span className="text-green-600 font-medium">Gratis</span>
                  ) : (
                    <span className="font-medium">{shipping===null?'Pendiente de cotización':formatPrice(shipping)}</span>
                  )}
                </div>
                <div className="border-t pt-3">
                  <div className="flex justify-between">
                    <span className="text-lg font-semibold text-gray-900">Total</span>
                    <span className="text-lg font-bold text-gray-900">{shipping===null?'Pendiente de cotización':formatPrice(total)}</span>
                  </div>
                </div>
              </div>

              {tccEnabled && <div className="mt-4 space-y-2 text-sm" aria-live="polite">
                {quoting&&<p>Cotizando transporte con TCC…</p>}
                {activeQuote&&<><p>Tarifa TCC: {formatPrice(Number(activeQuote.tcc_rate))}</p><p>Recargo y manipulación: {formatPrice(Number(activeQuote.surcharge))}</p><p>{activeQuote.package_count} paquetes · Cotización válida hasta {new Date(activeQuote.expires_at).toLocaleTimeString('es-CO')}</p></>}
                <button type="button" className="text-blue-700 underline" disabled={quoting} onClick={()=>setQuoteVersion(value=>value+1)}>Volver a cotizar</button>
              </div>}
              {shippingError&&<p role="alert" className="mt-3 text-sm text-red-700">{shippingError}</p>}

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Truck className="w-4 h-4 text-blue-600" />
                  <span>{tccEnabled?'Transporte cotizado con TCC antes del pago':requiresConfirmation?'Envío pendiente por confirmar':'Envío gratis en compras +$500.000'}</span>
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
