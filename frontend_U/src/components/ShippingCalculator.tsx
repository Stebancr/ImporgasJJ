import { useEffect, useRef, useState, useId } from 'react'
import { useAuth } from '../context/AuthContext'
import { type UserAddress } from '../services/addresses'
import {useQueryClient} from '@tanstack/react-query'
import DeliveryAddressForm from './DeliveryAddressForm'
import { shippingService, deliveryError, deliveryFailureHint, shippingDestinationKey, type ShippingCalculation } from '../services/shipping'
import TCCAddressFields from './TCCAddressFields'
import {Truck,MapPin} from 'lucide-react'
import {Link} from 'react-router-dom'
import { notifyDeliveryLocation, readDeliverySelection, addressLocation } from '../hooks/useDeliveryLocation'
import {useShippingConfig} from '../hooks/useShippingConfig'
import {useDeliveryCatalog} from '../hooks/useDeliveryCatalog'
import {useDeliveryAddresses} from '../hooks/useDeliveryAddresses'

type Destination = {address_id:number|null;customer_name:string;customer_phone:string;customer_email:string;
  shipping_address:string;city:string;department:string;postal_code:string;tcc_city_code:string;
  complement:string;neighborhood:string;delivery_instructions:string}
const empty:Destination={address_id:null,customer_name:'',customer_phone:'',customer_email:'',shipping_address:'',city:'',department:'',
  postal_code:'',tcc_city_code:'',complement:'',neighborhood:'',delivery_instructions:''}
const fmt=(value:string)=>Number(value).toLocaleString('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0,maximumFractionDigits:2})

export default function ShippingCalculator({items,cart=false,onQuote,productPrice,enabled,initiallyEditing=false,shippingReady,missingFields=[]}:{items:{product_id:number;quantity:number}[];cart?:boolean;onQuote?:(value:ShippingCalculation|null)=>void;productPrice?:number;enabled?:boolean;initiallyEditing?:boolean;shippingReady?:boolean;missingFields?:string[]}) {
  const config=useShippingConfig()
  const catalog=useDeliveryCatalog()
  const canQuote=config.status==='success'&&enabled!==false&&shippingReady!==false&&catalog.status==='success'
  const {user,isAuthenticated,isLoading}=useAuth()
  const cache=useQueryClient()
  const savedAddresses=useDeliveryAddresses()
  const addresses=savedAddresses.data??[]
  const owner=user?.id||'guest'
  const [formOwner,setFormOwner]=useState(owner)
  const [addressEditor,setAddressEditor]=useState(false)
  const id=useId()
  const [form,setForm]=useState<Destination>(empty)
  const [editing,setEditing]=useState(cart||initiallyEditing)
  const manualLocation=useRef(false)
  const [ready,setReady]=useState(false)
  const [errorCode,setErrorCode]=useState('')
  const [started,setStarted]=useState(cart),[revision,setRevision]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const [result,setResult]=useState<{key:string;value:ShippingCalculation}|null>(null)
  const callback=useRef(onQuote);callback.current=onQuote
  const forceRefresh=useRef(false)
  const sessionReady=ready&&formOwner===owner&&!isLoading
  const key=JSON.stringify({owner,items,form})
  const current=canQuote&&sessionReady&&result?.key===key && Date.parse(result.value.expires_at)>Date.now()?result.value:null
  const persistAddress=(address:UserAddress)=>{
    const location=addressLocation(address,catalog.data||[])
    try{sessionStorage.setItem(shippingDestinationKey(owner),JSON.stringify({address_id:address.id,tcc_city_code:location?.code||'',city:address.city,department:address.department,manual_location:true}))}catch{/* Optional storage. */}
  }
  const applyAddress=(address:UserAddress)=>setForm(previous=>({...previous,address_id:address.id,customer_name:address.recipient_name,
    customer_phone:address.phone,shipping_address:address.address,city:address.city,department:address.department,
    postal_code:address.postal_code||'',tcc_city_code:addressLocation(address,catalog.data||[])?.code||'',complement:address.complement||'',
    neighborhood:address.neighborhood||'',delivery_instructions:address.delivery_instructions||''}))
  const selectAddress=(address:UserAddress)=>{manualLocation.current=true;persistAddress(address);applyAddress(address);notifyDeliveryLocation()}
  const saveAddress=(address:UserAddress)=>{
    persistAddress(address)
    cache.setQueryData<UserAddress[]>(['delivery-addresses',user?.id],previous=>[address,...(previous||[]).filter(item=>item.id!==address.id).map(item=>address.is_default?{...item,is_default:false}:item)])
    selectAddress(address);setAddressEditor(false)
  }
  useEffect(()=>{
    setForm(previous=>({...previous,customer_name:previous.customer_name||user?.name||'',customer_email:user?.email||'',customer_phone:previous.customer_phone||user?.phone||''}))
  },[user?.id,user?.name,user?.email,user?.phone])
  useEffect(()=>{
    setReady(false);setResult(null);setAddressEditor(false);manualLocation.current=false
    setForm({...empty,customer_name:user?.name||'',customer_email:user?.email||'',customer_phone:user?.phone||''})
    if(isLoading||catalog.status==='loading'||(isAuthenticated&&savedAddresses.isPending))return
    const selection=readDeliverySelection(user?.id,catalog.data??[],addresses)
    if(selection.address){
      const address=selection.address
      setForm({...empty,address_id:address.id,customer_name:address.recipient_name,customer_email:user?.email||'',customer_phone:address.phone,
        shipping_address:address.address,city:address.city,department:address.department,postal_code:address.postal_code||'',
        tcc_city_code:selection.location?.code||'',complement:address.complement||'',neighborhood:address.neighborhood||'',delivery_instructions:address.delivery_instructions||''})
    }else if(selection.location){
      let details:Partial<Destination>={}
      if(cart&&isAuthenticated){
        try{
          const stored=JSON.parse(sessionStorage.getItem(shippingDestinationKey(owner))||'null')
          if(!stored?.address_id&&stored?.tcc_city_code===selection.location.code){
            for(const field of ['shipping_address','postal_code','complement','neighborhood','delivery_instructions','customer_name','customer_phone'] as const){
              if(typeof stored[field]==='string')details[field]=stored[field]
            }
          }
        }catch{/* Only this account's optional draft is read. */}
      }
      setForm({...empty,customer_name:user?.name||'',customer_email:user?.email||'',customer_phone:user?.phone||'',
        ...details,
        tcc_city_code:selection.location.code,city:selection.location.city,department:selection.location.department})
    }
    setFormOwner(owner);setReady(true);setStarted(true)
  },[isAuthenticated,user?.id,isLoading,catalog.status,savedAddresses.isPending,savedAddresses.data,savedAddresses.isError])
  useEffect(()=>{
    let active=true
    const controller=new AbortController()
    const force=forceRefresh.current;forceRefresh.current=false
    setResult(null);callback.current?.(null);setError('');setErrorCode('');setBusy(false)
    if(!sessionReady||!started)return
    // Remember a valid selection even if this product has incomplete logistics
    // or the carrier is temporarily unavailable. Never persist tariff amounts.
    try{
      const storageKey=shippingDestinationKey(user?.id||'guest')
      const previous=JSON.parse(sessionStorage.getItem(storageKey)||'null')
      const destination={tcc_city_code:form.tcc_city_code,city:form.city,department:form.department}
      sessionStorage.setItem(storageKey,JSON.stringify({...((cart&&isAuthenticated)?form:destination),...(isAuthenticated&&form.address_id?{address_id:form.address_id}:{}),manual_location:manualLocation.current||previous?.manual_location||false}))
      if(manualLocation.current)notifyDeliveryLocation()
    }catch{/* Storage is optional. */}
    if(!form.tcc_city_code||!canQuote)return
    setBusy(true)
    const timer=setTimeout(()=>{
      const complete=cart&&isAuthenticated&&form.customer_name&&form.customer_phone&&form.customer_email&&form.shipping_address
      const request=complete?shippingService.quote({...form,items,force},controller.signal):shippingService.estimate({items,...(isAuthenticated&&form.address_id?{address_id:form.address_id}:{tcc_city_code:form.tcc_city_code}),force},controller.signal)
      request.then(value=>{
        if(!active)return
        setResult({key,value});callback.current?.(value)
      }).catch((e:unknown)=>{if(active){setError(deliveryError(e));setErrorCode(typeof (e as {code?:unknown})?.code==='string'?(e as {code:string}).code:'')}})
        .finally(()=>{if(active)setBusy(false)})
    },500)
    return()=>{active=false;clearTimeout(timer);controller.abort()}
  },[key,started,sessionReady,revision,cart,isAuthenticated,user?.id,canQuote])
  useEffect(()=>{
    if(!result)return
    const timer=setTimeout(()=>setRevision(value=>value+1),Math.max(0,Date.parse(result.value.expires_at)-Date.now()))
    return()=>clearTimeout(timer)
  },[result])
  return <section className="my-5 min-w-0 space-y-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5" aria-label="Información de envío">
    <div className="flex items-center gap-3"><span className="rounded-xl bg-blue-50 p-2 text-[#001575]"><Truck aria-hidden="true" className="h-5 w-5"/></span><div><h3 className="font-semibold text-gray-900">Entrega de tu pedido</h3><p className="text-xs text-gray-600">Conoce el costo según tu destino</p></div></div>
    {!cart&&<><p className="font-semibold">Precio del producto: {fmt(String(productPrice??0))}</p><p className="text-sm">El precio mostrado corresponde únicamente al producto. El costo de envío se calcula según la ubicación de entrega.</p></>}
    {shippingReady===false ? <div data-shipping-state="incomplete"><p className="font-semibold">Envío pendiente por configurar</p><p className="text-sm">Este producto todavía no cuenta con la información necesaria para calcular automáticamente el costo de entrega.</p>{missingFields.length>0&&<p className="mt-2 text-sm">Falta: {missingFields.join(', ')}.</p>}</div>
      :config.status==='error'?<div role="alert" data-shipping-state="configuration-error"><p>{config.error}</p><p className="text-sm">{deliveryFailureHint(config.cause)}</p><button type="button" disabled={config.loading} className="min-h-11 underline" onClick={()=>config.retry()}>Reintentar configuración</button></div>
      :config.status==='loading'?<p role="status">Consultando opciones de entrega…</p>
      :config.status==='success'&&enabled!==false&&catalog.status==='error'?<div role="alert" data-shipping-state="catalog-error"><p>No fue posible cargar los departamentos y ciudades.</p><p className="text-sm">{deliveryFailureHint(catalog.error)}</p><button type="button" className="min-h-11 underline" disabled={catalog.isFetching} onClick={()=>catalog.refetch()}>Reintentar ubicaciones</button></div>
      :config.status==='success'&&enabled!==false&&catalog.status==='loading'?<p role="status">Consultando opciones de entrega…</p>
      :config.status==='success'&&enabled!==false&&catalog.status==='empty'?<p className="text-sm">No hay departamentos y ciudades disponibles por el momento.</p>
      :!canQuote?<p data-shipping-state="disabled" className="text-sm">La cotización automática de envío no está disponible en este momento.</p>
      :!sessionReady?<p role="status" className="text-sm">Cargando ubicación de entrega…</p>
      :!current&&!error&&!busy&&<div data-shipping-state="idle"><p className="text-sm font-semibold">{isAuthenticated&&savedAddresses.isSuccess&&!addresses.length?'Agrega tu ubicación de entrega':'Calcula el costo de entrega'}</p><p className="text-sm">{isAuthenticated?'Para calcular el costo del envío, indícanos dónde deseas recibir el producto.':'Selecciona el lugar donde deseas recibir el producto.'}</p></div>}
    {isAuthenticated&&savedAddresses.isError&&<div role="alert" className="text-sm text-red-700">No fue posible cargar tus direcciones. {deliveryFailureHint(savedAddresses.error)} <button type="button" disabled={savedAddresses.isFetching} className="min-h-11 underline" onClick={()=>savedAddresses.refetch()}>Reintentar direcciones</button></div>}
    {canQuote&&sessionReady&&isAuthenticated&&savedAddresses.isSuccess&&!addresses.length&&<p className="text-sm text-gray-600">Todavía no tienes una dirección de entrega. Puedes ingresar una ubicación para calcular el envío o guardar una dirección completa.</p>}
    {canQuote&&sessionReady&&isAuthenticated&&form.address_id&&<div className="rounded-lg bg-gray-50 p-3 text-sm" aria-label="Dirección de entrega seleccionada"><p className="font-semibold">Entregar en:</p><p>{form.shipping_address}, {form.city}, {form.department}</p><p>{form.customer_name} · {form.customer_phone}</p></div>}
    {canQuote&&sessionReady&&!cart&&<button type="button" className="flex min-h-11 w-full items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-left text-sm text-[#001575] hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-700" onClick={()=>setEditing(value=>!value)} aria-expanded={editing}><MapPin aria-hidden="true" className="h-4 w-4 shrink-0"/>{form.address_id?'Cambiar dirección':form.city?`Envío a ${form.city} · Cambiar ubicación`:'Configurar ubicación de entrega'}</button>}
    {editing&&canQuote&&sessionReady&&!addressEditor&&<>
    {isAuthenticated&&addresses.length>0&&<label className="block text-sm">Dirección guardada<select aria-label="Dirección guardada para cotizar" className="mt-1 w-full min-w-0 rounded border bg-white p-2" value={form.address_id??''} onChange={e=>{
      const address=addresses.find(value=>value.id===Number(e.target.value));if(address)selectAddress(address);else{manualLocation.current=true;setForm(previous=>({...previous,address_id:null,shipping_address:'',postal_code:'',complement:'',neighborhood:'',delivery_instructions:''}))}
    }}><option value="">Otra dirección</option>{addresses.map(address=><option key={address.id} value={address.id}>{address.label} — {address.city}</option>)}</select></label>}
    <TCCAddressFields value={form} compact={!cart} onChange={patch=>{manualLocation.current=true;setForm(previous=>({...previous,...patch,address_id:null,...(!cart?{shipping_address:'',postal_code:'',complement:'',neighborhood:'',delivery_instructions:''}:{})}))}}/>
    {cart&&<><label htmlFor={`${id}-street`} className="block text-sm">Dirección de entrega<input id={`${id}-street`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={500} value={form.shipping_address} onChange={e=>setForm(previous=>({...previous,shipping_address:e.target.value,address_id:null}))}/></label>
    <label htmlFor={`${id}-postal`} className="block text-sm">Código postal (opcional)<input id={`${id}-postal`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={20} value={form.postal_code} onChange={e=>setForm(previous=>({...previous,postal_code:e.target.value,address_id:null}))}/></label>
    </>}
    <p className="text-xs text-gray-600">El envío se calcula automáticamente al seleccionar tu ciudad.</p>
    <button type="button" disabled={busy||!canQuote||!form.tcc_city_code} className="min-h-11 rounded-lg bg-blue-700 px-4 py-2 text-white disabled:opacity-60" onClick={()=>{forceRefresh.current=true;setStarted(true);setRevision(value=>value+1)}}>{busy?'Calculando envío…':'Calcular envío'}</button>
    </>}
    {canQuote&&sessionReady&&isAuthenticated&&!cart&&!addressEditor&&<button type="button" className="min-h-11 font-semibold text-[#001575] underline" onClick={()=>setAddressEditor(true)}>Agregar nueva dirección</button>}
    {isAuthenticated&&sessionReady&&addressEditor&&<DeliveryAddressForm initial={{recipient_name:user?.name||'',phone:user?.phone||'',city:form.city,department:form.department,tcc_city_code:form.tcc_city_code,is_default:addresses.length===0}} onSaved={saveAddress} onCancel={()=>setAddressEditor(false)}/>}
    {busy&&canQuote&&<p role="status" className="text-sm">Consultando opciones de entrega…</p>}
    {error&&canQuote&&<div role={errorCode==='shipping_profile_incomplete'?'status':'alert'} className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">{errorCode==='shipping_profile_incomplete'?<><p className="font-semibold">Envío pendiente por configurar</p><p>Este producto todavía no cuenta con la información necesaria para calcular automáticamente el costo de entrega.</p><Link className="inline-flex min-h-11 items-center font-semibold underline" to="/contacto">Contactar a un asesor</Link></>:<><p>No fue posible calcular el costo de envío.</p><p>{errorCode==='route_not_configured'?'Prueba otra ciudad o consulta con un asesor la disponibilidad de entrega.':'Verifica la ubicación o inténtalo nuevamente.'}</p><p className="text-xs">{error}</p><button type="button" disabled={busy} className="min-h-11 underline" onClick={()=>{forceRefresh.current=true;setRevision(value=>value+1)}}>Reintentar cotización</button></>}</div>}
    {current&&<div aria-live="polite" className="space-y-2 rounded-xl bg-gray-50 p-4 text-sm">
      <p className="font-semibold">{current.approximate?'Envío estimado':'Envío cotizado'}: {fmt(current.total)}</p>
      {!cart&&<><p>Subtotal de productos: {fmt(current.subtotal)}</p><p className="font-semibold">Total estimado: {fmt(current.order_total)}</p></>}
      <p>Cobertura disponible para esta cotización.</p>
      <p>Destino: {current.destination?.city||form.city}, {current.destination?.department||form.department}</p>
      {Number(current.surcharge)>0&&<p>Transporte {fmt(current.tcc_rate)} + preparación {fmt(current.surcharge)}</p>}
      {current.estimated_delivery&&<p>Entrega estimada: {current.estimated_delivery}</p>}
      <p>{current.approximate?'El valor definitivo se validará con la dirección completa antes del pago.':'La tarifa y el total se vuelven a verificar antes del pago.'}</p>
    </div>}
  </section>
}
