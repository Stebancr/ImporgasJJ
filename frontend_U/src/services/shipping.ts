import api from './api'
export const shippingDestinationKey = (userId:string) => `tcc-checkout-destination:${userId}`

export interface ShippingProfile {
  declared_value_from_price?: boolean
  requires_shipping: boolean
  weight_kg: string | null
  height_cm: string | null
  width_cm: string | null
  length_cm: string | null
  packages_per_unit: number | null
  declared_value: string | null
  packaging_code: string
  fragile: boolean
}
export const emptyShippingProfile: ShippingProfile = { declared_value_from_price: true, requires_shipping: true, weight_kg: null, height_cm: null,
  width_cm: null, length_cm: null, packages_per_unit: 1, declared_value: null, packaging_code: 'CLEM_CAJA', fragile: false }

export interface TCCCity { code: string; city: string; department: string }
export interface ShippingCalculation {
  id?: string; carrier: string; tcc_rate: string; surcharge: string; total: string; subtotal: string; order_total: string
  discounts?: string; taxes?: string; approximate?: boolean; quoted_at?: string
  destination?: {city:string;department:string}; estimated_delivery?: string | null
  expires_at: string; package_count: number; real_kg: string; volumetric_kg: string; billable_kg: string
}
export interface ShippingQuote extends ShippingCalculation {id:string}
export interface ShipmentInfo {
  id: number; carrier: string; state: string; state_label: string; waybill: string | null; last_update: string
  last_sync_at: string | null; tracking_url: string; tracking_api_available: boolean
  history: Array<{state: string; description: string; created_at: string}>
  account_type?: string; account?: string; real_kg?: string; volumetric_kg?: string; billable_kg?: string
  tcc_rate?: string; surcharge?: string; charged?: string; last_error?: string; retry_allowed?: boolean
  documents?: Record<string,string>; environment?: string
}

export interface TCCAddress {
  tcc_city_code: string; complement: string; neighborhood: string; delivery_instructions: string
}
export function deliveryFailureHint(error:unknown):string {
  const value=error as {status?:number;name?:string}
  if(value?.status===401)return 'Tu sesión no es válida. Inicia sesión nuevamente.'
  if(value?.status===403)return 'No tienes permiso para realizar esta consulta.'
  if(value?.status===404)return 'Este servicio no está disponible. Inténtalo más tarde.'
  if(value?.status&&value.status>=500)return 'El servicio no está disponible temporalmente.'
  if(value?.name==='TimeoutError')return 'La solicitud tardó demasiado. Inténtalo nuevamente.'
  if(error instanceof TypeError)return 'Revisa tu conexión a internet.'
  return ''
}
export function deliveryError(error:unknown):string {
  const code=(error as {code?:string})?.code
  if(code==='configuration'||code==='carrier_authentication')return 'El cálculo de entrega no está disponible en este momento. Contacta a un asesor.'
  if(code==='route_not_configured'&&error instanceof Error)return error.message.replace(/\bTCC\b/gi,'el servicio de transporte')
  const hint=deliveryFailureHint(error)
  if(hint)return hint
  return (error instanceof Error?error.message:'No fue posible calcular el envío.').replace(/\bTCC\b/gi,'el servicio de transporte')
}
let catalogue: {value:TCCCity[]; expires:number} | null = null
let catalogueRequest: Promise<TCCCity[]> | null = null
function cities():Promise<TCCCity[]> {
  if(catalogue&&catalogue.expires>Date.now())return Promise.resolve(catalogue.value)
  if(catalogueRequest)return catalogueRequest
  catalogueRequest=api.get<TCCCity[]>('/shipping/cities').then(value=>{
    if(!Array.isArray(value))throw new Error('El catálogo de entrega no tiene el formato esperado.')
    catalogue={value,expires:Date.now()+300000};return value
  }).finally(()=>{catalogueRequest=null})
  return catalogueRequest
}
let activeEstimates=0
const estimateQueue:Array<()=>void>=[]
type EstimateInput={items:{product_id:number;quantity:number}[];tcc_city_code:string}
const recentEstimates=new Map<string,ShippingCalculation>()
const estimateKey=(value:EstimateInput)=>JSON.stringify([value.tcc_city_code,[...value.items].sort((a,b)=>a.product_id-b.product_id)])
/** Informational only; checkout always requests its own server quote and never charges this value. */
export function previousEstimate(value:EstimateInput):ShippingCalculation|null {
  const result=recentEstimates.get(estimateKey(value))
  return result&&Date.parse(result.expires_at)>Date.now()?result:null
}
/** Bound catalogue traffic; aborted cards leave the queue without making an HTTP request. */
async function estimate(payload:EstimateInput&{force?:boolean},signal?:AbortSignal):Promise<ShippingCalculation> {
  if(activeEstimates>=3)await new Promise<void>(resolve=>estimateQueue.push(resolve))
  else activeEstimates++
  try {
    if(signal?.aborted)throw new DOMException('Solicitud cancelada','AbortError')
    const result=await api.post<ShippingCalculation>('/shipping/estimate',payload,signal)
    if(recentEstimates.size>=100)recentEstimates.delete(recentEstimates.keys().next().value!)
    recentEstimates.set(estimateKey(payload),result)
    return result
  } finally {const next=estimateQueue.shift();if(next)next();else activeEstimates--}
}
export const shippingService = {
  config: () => api.get<{enabled:boolean; tracking_api_available:boolean}>('/shipping/config'),
  cities,
  destination: () => api.get<{destination: {code:string;city:string;department:string}|null}>('/shipping/destination'),
  quote: (payload: unknown, signal?:AbortSignal) => api.post<ShippingQuote>('/shipping/quote',payload,signal),
  estimate,
}
