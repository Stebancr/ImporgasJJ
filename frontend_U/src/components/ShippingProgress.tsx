import {useQuery} from '@tanstack/react-query'
import {shippingService} from '../services/shipping'
import {useAuth} from '../context/AuthContext'

/** Informational progress from server prices; a successful quote grants the benefit. */
export default function ShippingProgress({items}:{items:{product_id:number;quantity:number}[]}){
  const {user}=useAuth()
  const key=JSON.stringify(items)
  const query=useQuery({queryKey:['shipping-promotion',user?.id||'guest',key],
    queryFn:({signal})=>shippingService.promotion(items,signal),staleTime:30000,retry:false})
  const remaining=Number(query.data?.amount_to_free_shipping)
  if(!query.data||!Number.isFinite(remaining)||remaining<=0)return null
  return <p className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-[#001575]" aria-live="polite">Agrega {remaining.toLocaleString('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0})} más para obtener envío gratis. Sujeto a cobertura y cotización de entrega.</p>
}
