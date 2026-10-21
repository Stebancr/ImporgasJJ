import { useEffect, useRef, useState, useId } from 'react'
import { useAuth } from '../context/AuthContext'
import addressesService, { type UserAddress } from '../services/addresses'
import { shippingService, deliveryError, shippingDestinationKey, type ShippingCalculation } from '../services/shipping'
import TCCAddressFields from './TCCAddressFields'
import {Truck,MapPin} from 'lucide-react'
import {Link} from 'react-router-dom'
import { notifyDeliveryLocation, resolveDeliveryLocation } from '../hooks/useDeliveryLocation'

type Destination = {address_id:number|null;customer_name:string;customer_phone:string;customer_email:string;
  shipping_address:string;city:string;department:string;postal_code:string;tcc_city_code:string;
  complement:string;neighborhood:string;delivery_instructions:string}
const empty:Destination={address_id:null,customer_name:'',customer_phone:'',customer_email:'',shipping_address:'',city:'',department:'',
  postal_code:'',tcc_city_code:'',complement:'',neighborhood:'',delivery_instructions:''}
const fmt=(value:string)=>Number(value).toLocaleString('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0,maximumFractionDigits:2})

export default function ShippingCalculator({items,cart=false,onQuote,productPrice,enabled=true,initiallyEditing=false}:{items:{product_id:number;quantity:number}[];cart?:boolean;onQuote?:(value:ShippingCalculation|null)=>void;productPrice?:number;enabled?:boolean;initiallyEditing?:boolean}) {
  const {user,isAuthenticated}=useAuth()
  const id=useId()
  const [form,setForm]=useState<Destination>(empty),[addresses,setAddresses]=useState<UserAddress[]>([])
  const [editing,setEditing]=useState(cart||initiallyEditing)
  const manualLocation=useRef(false)
  const [ready,setReady]=useState(false)
  const [errorCode,setErrorCode]=useState('')
  const [started,setStarted]=useState(cart),[revision,setRevision]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const [result,setResult]=useState<{key:string;value:ShippingCalculation}|null>(null)
  const callback=useRef(onQuote);callback.current=onQuote
  const forceRefresh=useRef(false)
  const key=JSON.stringify({items,form})
  const current=result?.key===key && Date.parse(result.value.expires_at)>Date.now()?result.value:null
  const applyAddress=(address:UserAddress)=>setForm(previous=>({...previous,address_id:address.id,customer_name:address.recipient_name,
    customer_phone:address.phone,shipping_address:address.address,city:address.city,department:address.department,
    postal_code:address.postal_code||'',tcc_city_code:address.tcc_city_code||'',complement:address.complement||'',
    neighborhood:address.neighborhood||'',delivery_instructions:address.delivery_instructions||''}))
  useEffect(()=>{
    setForm(previous=>({...previous,customer_name:previous.customer_name||user?.name||'',customer_email:user?.email||'',customer_phone:previous.customer_phone||user?.phone||''}))
  },[user?.id,user?.name,user?.email,user?.phone])
  useEffect(()=>{
    let active=true
    manualLocation.current=false
    setReady(false);setForm({...empty,customer_name:user?.name||'',customer_email:user?.email||'',customer_phone:user?.phone||''});setResult(null)
    const restore=async()=>{
      let stored:Partial<Destination>|null=null
      try{
        stored=JSON.parse(sessionStorage.getItem(shippingDestinationKey(user?.id||'guest'))||'null')
        if(!stored&&isAuthenticated){
          const guest=JSON.parse(sessionStorage.getItem(shippingDestinationKey('guest'))||'null')
          if(guest)stored={tcc_city_code:guest.tcc_city_code,city:guest.city,department:guest.department}
        }
      }catch{/* Optional storage. */}
      const catalog=await shippingService.cities().catch(()=>[])
      const valid=(code:unknown)=>catalog.find(c=>c.code===code)
      const values=isAuthenticated?await addressesService.getAll().catch(()=>[]):[]
      const preferred = !cart ? await resolveDeliveryLocation(user?.id).catch(()=>null) : null
      if(!active)return
      setAddresses(values)
      // An explicit change in this session overrides the initial default.
      if(preferred){
        setForm(previous=>({...previous,tcc_city_code:preferred.code,city:preferred.city,department:preferred.department}))
      }else if(stored&&valid(stored.tcc_city_code)){
        const destination=valid(stored.tcc_city_code)!
        const saved=values.find(value=>value.tcc_city_code===destination.code&&value.is_default)
        if(cart&&saved&&!stored.shipping_address)applyAddress(saved)
        else
        setForm({...empty,customer_name:user?.name||'',customer_email:user?.email||'',customer_phone:user?.phone||'',
          ...(cart?{shipping_address:typeof stored.shipping_address==='string'?stored.shipping_address:'',
            complement:typeof stored.complement==='string'?stored.complement:'',neighborhood:typeof stored.neighborhood==='string'?stored.neighborhood:'',
            delivery_instructions:typeof stored.delivery_instructions==='string'?stored.delivery_instructions:'',
            postal_code:typeof stored.postal_code==='string'?stored.postal_code:''}:{}),
          tcc_city_code:destination.code,city:destination.city,department:destination.department})
      }else if(stored?.department&&catalog.some(city=>city.department===stored.department)){
        setForm(previous=>({...previous,department:stored!.department!,city:'',tcc_city_code:''}))
      }else{
        const address=values.find(value=>value.is_default&&valid(value.tcc_city_code))
        if(address)applyAddress(address)
        else if(isAuthenticated){
          const previous=await shippingService.destination().catch(()=>null)
          if(!active)return
          const destination=valid(previous?.destination?.code)
          if(destination)setForm(previous=>({...previous,tcc_city_code:destination.code,city:destination.city,department:destination.department}))
        }
      }
      if(active){setReady(true);setStarted(true)}
    }
    void restore()
    return()=>{active=false}
  },[isAuthenticated,user?.id])
  useEffect(()=>{
    let active=true
    const controller=new AbortController()
    const force=forceRefresh.current;forceRefresh.current=false
    setResult(null);callback.current?.(null);setError('');setErrorCode('');setBusy(false)
    if(!ready||!started)return
    // Remember a valid selection even if this product has incomplete logistics
    // or the carrier is temporarily unavailable. Never persist tariff amounts.
    try{
      const storageKey=shippingDestinationKey(user?.id||'guest')
      const previous=JSON.parse(sessionStorage.getItem(storageKey)||'null')
      const destination={tcc_city_code:form.tcc_city_code,city:form.city,department:form.department}
      sessionStorage.setItem(storageKey,JSON.stringify({...((cart||form.address_id)?form:{...(previous?.tcc_city_code===form.tcc_city_code?previous:{}),...destination}),manual_location:manualLocation.current||previous?.manual_location||false}))
      if(manualLocation.current)notifyDeliveryLocation()
    }catch{/* Storage is optional. */}
    if(!form.tcc_city_code||!enabled)return
    setBusy(true)
    const timer=setTimeout(()=>{
      const complete=cart&&isAuthenticated&&form.customer_name&&form.customer_phone&&form.customer_email&&form.shipping_address
      const request=complete?shippingService.quote({...form,items,force},controller.signal):shippingService.estimate({items,tcc_city_code:form.tcc_city_code,force},controller.signal)
      request.then(value=>{
        if(!active)return
        setResult({key,value});callback.current?.(value)
      }).catch((e:unknown)=>{if(active){setError(deliveryError(e));setErrorCode(typeof (e as {code?:unknown})?.code==='string'?(e as {code:string}).code:'')}})
        .finally(()=>{if(active)setBusy(false)})
    },500)
    return()=>{active=false;clearTimeout(timer);controller.abort()}
  },[key,started,ready,revision,cart,isAuthenticated,user?.id,enabled])
  useEffect(()=>{
    if(!result)return
    const timer=setTimeout(()=>setRevision(value=>value+1),Math.max(0,Date.parse(result.value.expires_at)-Date.now()))
    return()=>clearTimeout(timer)
  },[result])
  return <section className="my-5 min-w-0 space-y-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5" aria-label="Información de envío">
    <div className="flex items-center gap-3"><span className="rounded-xl bg-blue-50 p-2 text-[#001575]"><Truck aria-hidden="true" className="h-5 w-5"/></span><div><h3 className="font-semibold text-gray-900">Entrega de tu pedido</h3><p className="text-xs text-gray-600">Conoce el costo según tu destino</p></div></div>
    {!cart&&<><p className="font-semibold">Precio del producto: {fmt(String(productPrice??0))}</p><p className="text-sm">El precio mostrado corresponde únicamente al producto. El costo de envío se calcula según la ubicación de entrega.</p></>}
    {!current&&<p className="text-sm">Envío: pendiente por calcular{!form.tcc_city_code&&<span className="block">Selecciona tu departamento y ciudad para conocer el costo de entrega.</span>}</p>}
    {!enabled&&<p className="text-sm">El costo de envío se confirmará al continuar la compra.</p>}
    {!cart&&<button type="button" className="flex min-h-11 w-full items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-left text-sm text-[#001575] hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-700" onClick={()=>setEditing(value=>!value)} aria-expanded={editing}><MapPin aria-hidden="true" className="h-4 w-4 shrink-0"/>{form.city?`Envío a ${form.city} · Cambiar ubicación`:'Configurar ubicación de entrega'}</button>}
    {editing&&<>
    {cart&&addresses.length>0&&<label className="block text-sm">Dirección guardada<select aria-label="Dirección guardada para cotizar" className="mt-1 w-full min-w-0 rounded border bg-white p-2" value={form.address_id??''} onChange={e=>{
      const address=addresses.find(value=>value.id===Number(e.target.value));if(address)applyAddress(address);else setForm(previous=>({...previous,address_id:null}))
    }}><option value="">Otra dirección</option>{addresses.map(address=><option key={address.id} value={address.id}>{address.label} — {address.city}</option>)}</select></label>}
    <TCCAddressFields value={form} compact={!cart} onChange={patch=>{manualLocation.current=true;setForm(previous=>({...previous,...patch,address_id:null}))}}/>
    {cart&&<><label htmlFor={`${id}-street`} className="block text-sm">Dirección de entrega<input id={`${id}-street`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={500} value={form.shipping_address} onChange={e=>setForm(previous=>({...previous,shipping_address:e.target.value,address_id:null}))}/></label>
    <label htmlFor={`${id}-postal`} className="block text-sm">Código postal (opcional)<input id={`${id}-postal`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={20} value={form.postal_code} onChange={e=>setForm(previous=>({...previous,postal_code:e.target.value,address_id:null}))}/></label>
    </>}
    <p className="text-xs text-gray-600">El envío se calcula automáticamente al seleccionar tu ciudad.</p>
    <button type="button" disabled={busy||!enabled} className="min-h-11 rounded-lg bg-blue-700 px-4 py-2 text-white disabled:opacity-60" onClick={()=>{forceRefresh.current=true;setStarted(true);setRevision(value=>value+1)}}>{busy?'Calculando envío…':'Calcular envío'}</button>
    </>}
    {busy&&<p role="status" className="text-sm">Calculando costo de envío…</p>}
    {error&&<div role="alert" className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"><p>{error}</p>{errorCode==='shipping_profile_incomplete'?<Link className="inline-flex min-h-11 items-center font-semibold underline" to="/contacto">Contactar a un asesor</Link>:<><p>{errorCode==='route_not_configured'?'Prueba otra ciudad o consulta con un asesor la disponibilidad de entrega.':'Puedes intentarlo nuevamente. El pago requiere un costo de envío confirmado.'}</p><button type="button" disabled={busy} className="min-h-11 underline" onClick={()=>{forceRefresh.current=true;setRevision(value=>value+1)}}>Reintentar cotización</button></>}</div>}
    {current&&<div aria-live="polite" className="space-y-2 rounded-xl bg-gray-50 p-4 text-sm">
      <p className="font-semibold">{current.approximate?'Envío estimado':'Envío cotizado'}: {fmt(current.total)}</p>
      {!cart&&<><p>Subtotal de productos: {fmt(current.subtotal)}</p><p className="font-semibold">Total estimado: {fmt(current.order_total)}</p></>}
      <p>Cobertura disponible para esta cotización.</p>
      <p>Destino: {current.destination?.city||form.city}, {current.destination?.department||form.department}</p>
      {Number(current.surcharge)>0&&<p>Transporte {fmt(current.tcc_rate)} + preparación {fmt(current.surcharge)}</p>}
      {current.estimated_delivery&&<p>Entrega estimada: {current.estimated_delivery}</p>}
      <p>{current.approximate?'Valor aproximado; se confirmará con la dirección completa y los productos del checkout.':'La tarifa y el total se vuelven a verificar antes del pago.'}</p>
    </div>}
  </section>
}
