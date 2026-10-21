import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Dialog, DialogContent, DialogTitle } from '@mui/material'
import { MapPin } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useDeliveryLocation } from '../hooks/useDeliveryLocation'
import { useShippingConfig } from '../hooks/useShippingConfig'
import { deliveryError, shippingService } from '../services/shipping'
import ShippingCalculator from './ShippingCalculator'

const money = (value: string) => Number(value).toLocaleString('es-CO', {style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 2})

/** Only visible cards request a rate. Queries are scoped by customer, product and destination. */
export default function ProductShippingEstimate({productId, price}: {productId: number; price: number}) {
  const {user} = useAuth()
  const location = useDeliveryLocation()
  const config = useShippingConfig()
  const element = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  const [editing, setEditing] = useState(false)
  const code = location.data?.code
  useEffect(() => {
    if (!element.current) return
    const observer = new IntersectionObserver(entries => { setVisible(entries.some(entry => entry.isIntersecting)) })
    observer.observe(element.current)
    return () => observer.disconnect()
  }, [])
  const quote = useQuery({queryKey: ['product-delivery', user?.id || 'guest', productId, price, code,location.data?.address_id],
    queryFn: ({signal}) => shippingService.estimate({items: [{product_id: productId, quantity: 1}], ...(user?{address_id:location.data?.address_id}:{tcc_city_code:code!}), force: false}, signal),
    enabled: visible && config.enabled === true && !!code, staleTime: 30000, retry: false,
    refetchInterval: query => query.state.data ? Math.max(1000, Date.parse(query.state.data.expires_at) - Date.now()) : false})
  const current = quote.data && Date.parse(quote.data.expires_at) > Date.now() ? quote.data : null
  const error = quote.error || location.error
  return <div ref={element} className="mb-4 min-w-0 rounded-xl border border-blue-100 bg-blue-50/50 p-3 text-xs" aria-label="Envío de este producto">
    <div aria-live="polite">
      {current ? <><p className="font-semibold text-[#001575]">Envío a {location.data?.city}: {current.free_shipping_applied?'Gratis':money(current.total)}</p>
        {current.estimated_delivery && <p>Entrega estimada: {current.estimated_delivery}</p>}
        <p className="mt-1 font-semibold">Total estimado: {money(current.order_total)}</p>
        <p className="mt-1 text-gray-600">Cobertura disponible. Se confirma en el checkout.</p></>
        : <><p className="font-medium">Envío: pendiente por calcular</p>
          <p className="mt-1 text-gray-600">{quote.isFetching ? 'Calculando costo de envío…' : error ? deliveryError(error) : config.error || (code ? 'Se confirmará con tu dirección de entrega.' : 'Selecciona tu ubicación para conocer el costo.')}</p></>}
    </div>
    <button type="button" onClick={() => setEditing(true)} className="mt-2 inline-flex min-h-11 items-center gap-1 text-left font-semibold text-[#001575] underline decoration-blue-200 underline-offset-4 focus-visible:outline focus-visible:outline-2">
      <MapPin size={14} aria-hidden="true"/>{user?(location.data?'Cambiar dirección':'Agregar nueva dirección'):location.data ? `${location.data.city} · Cambiar ubicación` : 'Configurar ubicación de entrega'}
    </button>
    {quote.isError && <button type="button" disabled={quote.isFetching} className="min-h-11 underline disabled:opacity-50" onClick={() => { void quote.refetch() }}>Reintentar envío</button>}
    <Dialog open={editing} onClose={() => setEditing(false)} fullWidth maxWidth="sm" aria-labelledby={`delivery-${productId}`}>
      <DialogTitle id={`delivery-${productId}`}>Ubicación de entrega</DialogTitle>
      <DialogContent><ShippingCalculator items={[{product_id: productId, quantity: 1}]} productPrice={price} enabled={config.enabled === true} initiallyEditing />
        <Button onClick={() => setEditing(false)}>Continuar viendo productos</Button></DialogContent>
    </Dialog>
  </div>
}
