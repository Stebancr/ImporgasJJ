import { useEffect, useRef, useState, useId } from 'react'
import { useAuth } from '../context/AuthContext'
import addressesService, { type UserAddress } from '../services/addresses'
import { shippingService, shippingDestinationKey, type ShippingCalculation } from '../services/shipping'
import TCCAddressFields from './TCCAddressFields'

type Destination = {address_id:number|null;customer_name:string;customer_phone:string;customer_email:string;
  shipping_address:string;city:string;department:string;postal_code:string;tcc_city_code:string;
  complement:string;neighborhood:string;delivery_instructions:string}
const empty:Destination={address_id:null,customer_name:'',customer_phone:'',customer_email:'',shipping_address:'',city:'',department:'',
  postal_code:'',tcc_city_code:'',complement:'',neighborhood:'',delivery_instructions:''}
const fmt=(value:string)=>Number(value).toLocaleString('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0,maximumFractionDigits:2})

export default function ShippingCalculator({items,cart=false,onQuote}:{items:{product_id:number;quantity:number}[];cart?:boolean;onQuote?:(value:ShippingCalculation|null)=>void}) {
  const {user,isAuthenticated}=useAuth()
  const id=useId()
  const [form,setForm]=useState<Destination>(empty),[addresses,setAddresses]=useState<UserAddress[]>([])
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
    if(!cart||!isAuthenticated)return
    let active=true
    addressesService.getAll().then(values=>{
      if(!active)return
      setAddresses(values)
      const address=values.find(value=>value.is_default)
      if(address)applyAddress(address)
    }).catch(()=>{ /* The customer can still enter a destination manually. */ })
    return()=>{active=false}
  },[cart,isAuthenticated,user?.id])
  useEffect(()=>{
    let active=true
    const force=forceRefresh.current;forceRefresh.current=false
    setResult(null);callback.current?.(null);setError('');setBusy(false)
    if(cart&&user?.id&&form.tcc_city_code){try{sessionStorage.setItem(shippingDestinationKey(user.id),JSON.stringify(form))}catch{/* Storage is optional; server quotation still validates the destination. */}}
    if(!started)return
    if(!form.tcc_city_code){if(!cart)setError('Selecciona el departamento y municipio de entrega.');return}
    setBusy(true)
    const timer=setTimeout(()=>{
      const complete=cart&&isAuthenticated&&form.customer_name&&form.customer_phone&&form.customer_email&&form.shipping_address
      const request=complete?shippingService.quote({...form,items,force}):shippingService.estimate({items,tcc_city_code:form.tcc_city_code,force})
      request.then(value=>{
        if(!active)return
        setResult({key,value});callback.current?.(value)
      }).catch((e:unknown)=>{if(active)setError(e instanceof Error?e.message:'No fue posible calcular el envío.')})
        .finally(()=>{if(active)setBusy(false)})
    },500)
    return()=>{active=false;clearTimeout(timer)}
  },[key,started,revision,cart,isAuthenticated,user?.id])
  useEffect(()=>{
    if(!result)return
    const timer=setTimeout(()=>setRevision(value=>value+1),Math.max(0,Date.parse(result.value.expires_at)-Date.now()))
    return()=>clearTimeout(timer)
  },[result])
  return <section className="my-5 min-w-0 space-y-3 rounded-xl border border-blue-100 bg-blue-50/40 p-4" aria-label="Cotizador de envío TCC">
    <h3 className="font-semibold">Calcula tu envío con TCC</h3>
    {cart&&addresses.length>0&&<label className="block text-sm">Dirección guardada<select aria-label="Dirección guardada para cotizar" className="mt-1 w-full min-w-0 rounded border bg-white p-2" value={form.address_id??''} onChange={e=>{
      const address=addresses.find(value=>value.id===Number(e.target.value));if(address)applyAddress(address);else setForm(previous=>({...previous,address_id:null}))
    }}><option value="">Otra dirección</option>{addresses.map(address=><option key={address.id} value={address.id}>{address.label} — {address.city}</option>)}</select></label>}
    <TCCAddressFields value={form} compact={!cart} onChange={patch=>setForm(previous=>({...previous,...patch,address_id:null}))}/>
    <label htmlFor={`${id}-street`} className="block text-sm">Dirección {cart?'de entrega':'(opcional para estimar)'}<input id={`${id}-street`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={500} value={form.shipping_address} onChange={e=>setForm(previous=>({...previous,shipping_address:e.target.value,address_id:null}))}/></label>
    <label htmlFor={`${id}-postal`} className="block text-sm">Código postal (opcional)<input id={`${id}-postal`} className="mt-1 w-full min-w-0 rounded border p-2" maxLength={20} value={form.postal_code} onChange={e=>setForm(previous=>({...previous,postal_code:e.target.value,address_id:null}))}/></label>
    <button type="button" disabled={busy} className="min-h-11 rounded-lg bg-blue-700 px-4 py-2 text-white disabled:opacity-60" onClick={()=>{forceRefresh.current=true;setStarted(true);setRevision(value=>value+1)}}>{busy?'Calculando envío…':'Calcular envío'}</button>
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
    {current&&<div aria-live="polite" className="space-y-1 text-sm">
      <p className="font-semibold">{current.approximate?'Envío estimado':'Envío cotizado'}: {fmt(current.total)}</p>
      <p>Destino: {current.destination?.city||form.city}, {current.destination?.department||form.department}</p>
      {Number(current.surcharge)>0&&<p>Tarifa TCC {fmt(current.tcc_rate)} + recargo {fmt(current.surcharge)}</p>}
      {current.estimated_delivery&&<p>Entrega estimada: {current.estimated_delivery}</p>}
      <p>{current.approximate?'Valor aproximado; se confirmará con la dirección completa y los productos del checkout.':'La tarifa y el total se vuelven a verificar antes del pago.'}</p>
    </div>}
  </section>
}
