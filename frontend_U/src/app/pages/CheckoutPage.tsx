import './styles/CheckoutPage.css'
import { useState, useMemo, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreditCard, Truck, Shield, ChevronLeft, Check, MapPin } from 'lucide-react'
import { useCart } from '../../context/CartContext'
import { useAuth } from '../../context/AuthContext'
import ordersService from '../../services/orders'
import { getWompiOptions, loadWompiWidget } from '../../services/wompiCheckout'
import addressesService, { UserAddress, type CreateAddressPayload } from '../../services/addresses'
import DeliveryAddressForm from '../../components/DeliveryAddressForm'
import { shippingService, deliveryError, previousEstimate, type ShippingQuote, type TCCAddress } from '../../services/shipping'
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
  const restorePaymentCart = useRef<string|null>(null)
  const [addresses, setAddresses] = useState<UserAddress[]>([])
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null)
  const [addressEditor,setAddressEditor]=useState<(Partial<CreateAddressPayload>&{id?:number})|null>(null)
  const [destinationReady,setDestinationReady]=useState(false)
  const [addressError,setAddressError]=useState('')
  const [tccEnabled,setTccEnabled]=useState<boolean|null>(null)
  const [shippingError,setShippingError]=useState('')
  const [rateNotice,setRateNotice]=useState('')
  const lastRate=useRef<{key:string;total:string}|null>(null)
  const [paymentError,setPaymentError]=useState('')
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
  useEffect(()=>{shippingService.config().then(config=>setTccEnabled(config.enabled)).catch(()=>setShippingError('No fue posible verificar el transporte. Actualiza la página antes de pagar.'))},[])
  const quoteKey=JSON.stringify({items:items.map(item=>({product_id:Number(item.product.id),quantity:item.quantity})),form,address_id:selectedAddressId})
  const cartKey=JSON.stringify(items.map(item=>({id:item.product.id,quantity:item.quantity})))
  useEffect(()=>{
    if(destinationReady&&items.length&&restorePaymentCart.current){
      if(restorePaymentCart.current===cartKey)setStep('payment')
      restorePaymentCart.current=null
    }
  },[destinationReady,cartKey])
  const activeQuote=quoted?.key===quoteKey && Date.parse(quoted.value.expires_at)>Date.now()?quoted.value:null
  useEffect(()=>{
    let active=true
    const controller=new AbortController()
    setQuoted(null)
    setRateNotice('')
    if(tccEnabled!==true||!destinationReady||addressEditor)return
    setShippingError('')
    if(!form.email||!form.name||!form.phone||!form.address||!form.tcc_city_code){setQuoting(false);return}
    setQuoting(true)
    const timer=setTimeout(()=>{
      shippingService.quote({force:quoteVersion>0,items:items.map(item=>({product_id:Number(item.product.id),quantity:item.quantity})),
        address_id:selectedAddressId,customer_name:form.name,customer_email:form.email,customer_phone:form.phone,
        shipping_address:form.address,city:form.city,department:form.department,postal_code:form.postalCode,
        tcc_city_code:form.tcc_city_code,complement:form.complement,neighborhood:form.neighborhood,delivery_instructions:form.delivery_instructions},controller.signal)
        .then(value=>{if(active){
          const estimated=previousEstimate({items:items.map(item=>({product_id:Number(item.product.id),quantity:item.quantity})),tcc_city_code:form.tcc_city_code})
          const previous=lastRate.current?.key===quoteKey?lastRate.current.total:estimated?.total
          if(previous!==undefined&&Number(previous)!==Number(value.total))setRateNotice('El costo de envío cambió respecto a la cotización anterior. Revisa el total actualizado antes de pagar.')
          lastRate.current={key:quoteKey,total:value.total}
          setQuoted({key:quoteKey,value})
        }})
        .catch((e:unknown)=>{if(active)setShippingError(deliveryError(e))})
        .finally(()=>{if(active)setQuoting(false)})
    },500)
    return()=>{active=false;clearTimeout(timer);controller.abort()}
  },[quoteKey,tccEnabled,quoteVersion,destinationReady,!!addressEditor])
  useEffect(()=>{
    if(!destinationReady||!user?.id||!items.length)return
    try{
      sessionStorage.setItem(`delivery-checkout:${user.id}`,JSON.stringify({form,step,cartKey,address_id:selectedAddressId,quote_id:activeQuote?.id||null}))
      sessionStorage.setItem(shippingDestinationKey(user.id),JSON.stringify({address_id:selectedAddressId,customer_name:form.name,customer_phone:form.phone,customer_email:form.email,shipping_address:form.address,city:form.city,department:form.department,postal_code:form.postalCode,tcc_city_code:form.tcc_city_code,complement:form.complement,neighborhood:form.neighborhood,delivery_instructions:form.delivery_instructions}))
    }catch{/* Optional storage. Server always recalculates before charging. */}
  },[destinationReady,user?.id,form,step,selectedAddressId,cartKey,activeQuote?.id])
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
  }, [isAuthenticated, user?.id])

  const loadAddresses = async () => {
    setAddressError('');setDestinationReady(false)
    let loaded=false
    try {
      const data = await addressesService.getAll()
      loaded=true
      setAddresses(data)
      // Auto-select default address
      let defaultAddr = data.find((addr) => addr.is_default) || data[0]
      try{
        const saved=JSON.parse(sessionStorage.getItem(`delivery-checkout:${user?.id}`)||'null')
        const destination=JSON.parse(sessionStorage.getItem(shippingDestinationKey(user?.id||''))||sessionStorage.getItem(shippingDestinationKey('guest'))||'null')
        // A newer cart location takes precedence over an older checkout draft.
        const sameDestination=!destination||(destination.tcc_city_code===saved?.form?.tcc_city_code
          &&(destination.address_id??null)===(saved?.address_id??null)
          &&[['shipping_address','address'],['complement','complement'],['neighborhood','neighborhood'],['delivery_instructions','delivery_instructions']].every(([source,target])=>!(source in destination)||destination[source]===saved?.form?.[target]))
        if(saved?.form&&sameDestination&&(!saved.address_id||data.some(address=>address.id===saved.address_id))){
          setForm(previous=>({...previous,...Object.fromEntries(Object.entries(saved.form).filter(([key,value])=>key in previous&&typeof value==='string')),paymentMethod:'wompi'}))
          setSelectedAddressId(saved.address_id||null)
          if(saved.address_id)applyAddress(data.find(a=>a.id===saved.address_id)!)
          if(saved.step==='payment'&&typeof saved.cartKey==='string')restorePaymentCart.current=saved.cartKey
          return
        }
      }catch{/* Invalid browser state is ignored. */}
      try {
        const draft = user?.id ? JSON.parse(sessionStorage.getItem(shippingDestinationKey(user.id)) || sessionStorage.getItem(shippingDestinationKey('guest')) || 'null') : null
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
      setAddressError('No fue posible cargar tus direcciones. Puedes reintentar o agregar una dirección de entrega.')
    }finally{setDestinationReady(loaded)}
  }

  const applyAddress=(addr:UserAddress)=>{
    setSelectedAddressId(addr.id)
    setForm(previous=>({...previous,name:addr.recipient_name,phone:addr.phone,address:addr.address,city:addr.city,department:addr.department,postalCode:addr.postal_code||'',tcc_city_code:addr.tcc_city_code||'',complement:addr.complement||'',neighborhood:addr.neighborhood||'',delivery_instructions:addr.delivery_instructions||''}))
  }
  const saveAddress=(address:UserAddress)=>{
    setAddresses(previous=>[address,...previous.filter(item=>item.id!==address.id).map(item=>address.is_default?{...item,is_default:false}:item)])
    applyAddress(address);setAddressEditor(null);setDestinationReady(true);setAddressError('');setQuoteVersion(value=>value+1)
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
  const shipping = tccEnabled!==false ? (activeQuote?Number(activeQuote.total):null) : null
  const total = activeQuote?Number(activeQuote.order_total):subtotal+(shipping??0)


  // Unique reference per session
  const reference = useMemo(
    () => `GS-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`,
    [cartKey, selectedAddressId, form.address, form.city, form.department, form.complement, form.neighborhood, form.delivery_instructions, activeQuote?.id]
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
    if(tccEnabled===null || (tccEnabled && !activeQuote)){
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
      setPaymentError(deliveryError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const handleWompiConfirm = async () => {
    if(tccEnabled===null || (tccEnabled && !activeQuote)){setShippingError('Actualiza la cotización antes de pagar.');return null}
    if (paymentLock.current) return
    paymentLock.current = true
    setPaymentError('')
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
      setPaymentError(deliveryError(err))
      // Preserve the same payment reference on a transient failure; explicit recotation or expiry changes it.
      setSubmitting(false)
      paymentLock.current = false
      return null
    }
  }

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

            {paymentError&&<p role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{paymentError}</p>}
            {/* Information Step */}
            {step==='info'&&addressEditor&&<DeliveryAddressForm key={addressEditor.id||'new'} initial={addressEditor} onSaved={saveAddress} onCancel={()=>setAddressEditor(null)}/>}
            {step === 'info' && !addressEditor && (
              <form onSubmit={handleSubmitInfo} className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Dirección de entrega</h2>
                {addressError&&<p role="alert" className="mb-4 text-red-700">{addressError} <button type="button" className="underline" onClick={loadAddresses}>Reintentar</button></p>}
                {!destinationReady&&<p role="status">Cargando direcciones de entrega…</p>}
                <button type="button" className="mb-4 min-h-11 rounded-lg border border-blue-700 px-4 text-blue-800" onClick={()=>setAddressEditor({recipient_name:form.name,phone:form.phone,is_default:addresses.length===0})}>Agregar nueva dirección</button>
                {selectedAddressId&&<button type="button" className="mb-4 ml-3 min-h-11 text-blue-800 underline" onClick={()=>setAddressEditor(addresses.find(address=>address.id===selectedAddressId)||null)}>Editar dirección seleccionada</button>}

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
                          aria-pressed={selectedAddressId===addr.id}
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
                              <p className="text-sm font-medium text-gray-800">{addr.recipient_name}</p><p className="text-sm text-gray-600">{addr.address} {addr.complement}</p>
                              <p className="text-sm text-gray-600">{addr.neighborhood} · {addr.phone}</p>
                              {addr.is_default&&<span className="text-sm font-semibold text-green-800">Predeterminada</span>}
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

                  <TCCAddressFields value={form} onChange={patch=>{setSelectedAddressId(null);setForm(prev=>({...prev,...patch}))}}/>
                  <div className="grid md:grid-cols-3 gap-4">
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
                  disabled={tccEnabled===null || (tccEnabled && (!activeQuote||quoting))}
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
                      para completar el pago de <strong>{tccEnabled!==false&&!activeQuote?"pendiente de cotización":formatPrice(total)}</strong>. La orden se confirmará cuando Wompi confirme el pago.
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
                      disabled={submitting||tccEnabled===null||(!!tccEnabled&&!activeQuote)}
                      className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-60"
                    >
                      {submitting ? 'Procesando...' : 'Confirmar Pedido'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleWompiConfirm}
                      disabled={submitting||tccEnabled===null||(!!tccEnabled&&!activeQuote)}
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
                  <span className="text-gray-600">Subtotal de productos</span>
                  <span className="font-medium">{formatPrice(subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm"><span>Descuentos adicionales</span><span>{formatPrice(Number(activeQuote?.discounts||0))}</span></div>
                <div className="flex justify-between text-sm"><span>Impuestos adicionales</span><span>{formatPrice(Number(activeQuote?.taxes||0))}</span></div>
                {tccEnabled ? <div className="flex justify-between"><span>Costo de envío</span><span>{shipping===null?'Pendiente de cotización':formatPrice(shipping)}</span></div>
                  : <p className="text-sm text-gray-600">El valor del envío no está incluido en esta compra. Las condiciones de entrega serán confirmadas posteriormente.</p>}
                <div className="border-t pt-3">
                  <div className="flex justify-between">
                    <span className="text-lg font-semibold text-gray-900">Total</span>
                    <span className="text-lg font-bold text-gray-900">{tccEnabled!==false&&!activeQuote?'Pendiente de cotización':formatPrice(total)}</span>
                  </div>
                </div>
              </div>

              {tccEnabled && <div className="mt-4 space-y-2 text-sm" aria-live="polite">
                {quoting&&<p>Calculando el costo de envío…</p>}
                {activeQuote&&<><p>Costo de envío: {formatPrice(Number(activeQuote.tcc_rate))}</p><p>Preparación del envío: {formatPrice(Number(activeQuote.surcharge))}</p><p>Precio válido hasta {new Date(activeQuote.expires_at).toLocaleTimeString('es-CO')}</p></>}
                <button type="button" className="text-blue-700 underline" disabled={quoting} onClick={()=>setQuoteVersion(value=>value+1)}>Volver a cotizar</button>
              </div>}
              {rateNotice&&<p role="status" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">{rateNotice}</p>}
              {shippingError&&<p role="alert" className="mt-3 text-sm text-red-700">{shippingError}</p>}

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Truck className="w-4 h-4 text-blue-600" />
                  <span>{tccEnabled?'El costo del transporte se valida antes del pago':'Las condiciones de entrega serán confirmadas posteriormente'}</span>
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
