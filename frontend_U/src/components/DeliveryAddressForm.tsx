import {useRef,useState,useId,useEffect,type FormEvent} from 'react'
import addressesService,{type CreateAddressPayload,type UserAddress} from '../services/addresses'
import TCCAddressFields from './TCCAddressFields'

export default function DeliveryAddressForm({initial,onSaved,onCancel}:{
  initial:Partial<CreateAddressPayload>&{id?:number};onSaved:(address:UserAddress)=>void;onCancel:()=>void
}){
  const id=useId(),lock=useRef(false)
  const mounted=useRef(true)
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[])
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  const [errors,setErrors]=useState<Record<string,string>>({})
  const fieldError=(field:string)=>errors[field]?<p id={id+'-'+field+'-error'} role="alert" className="mt-1 text-sm text-red-700">{errors[field]}</p>:null
  const [form,setForm]=useState<CreateAddressPayload>({label:'Casa',recipient_name:'',phone:'',address:'',city:'',department:'',postal_code:'',is_default:false,tcc_city_code:'',complement:'',neighborhood:'',delivery_instructions:'',...initial})
  const input='mt-1 min-h-11 w-full min-w-0 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-700'
  const submit=async(e:FormEvent)=>{
    e.preventDefault()
    if(lock.current)return
    const invalid:Record<string,string>={}
    for(const [field,message] of [['recipient_name','Escribe el nombre de quien recibe.'],['phone','Escribe un teléfono válido.'],['address','Escribe la dirección.'],['department','Selecciona un departamento.'],['tcc_city_code','Selecciona una ciudad o municipio.'],['label','Escribe el nombre de la dirección.']] as const){
      if(!String(form[field]||'').trim())invalid[field]=message
    }
    if(form.phone&&!/^[+0-9() .-]{7,30}$/.test(form.phone))invalid.phone='Escribe un teléfono válido.'
    setErrors(invalid)
    if(Object.keys(invalid).length)return
    lock.current=true;setBusy(true);setError('')
    try{
      const saved=initial.id?await addressesService.update(initial.id,form):await addressesService.create(form)
      if(mounted.current)onSaved(saved)
    }catch(e){
      if(!mounted.current)return
      const fields=(e as {fields?:Record<string,unknown>}).fields||{}
      const invalid=Object.fromEntries(Object.entries(fields).filter(([key])=>key in form).map(([key,value])=>[key,Array.isArray(value)?value.join(' '):String(value)]))
      setErrors(invalid)
      setError(Object.keys(invalid).length?'Revisa los campos indicados. Tus datos se conservan.':e instanceof Error?e.message:'No fue posible guardar la dirección. Tus datos se conservan.')
    }
    finally{lock.current=false;if(mounted.current)setBusy(false)}
  }
  return <form noValidate onSubmit={submit} className="min-w-0 space-y-4 rounded-xl border bg-white p-4 sm:p-6" aria-label="Formulario de dirección de entrega">
    <h3 className="text-lg font-semibold">{initial.id?'Editar dirección de entrega':'Nueva dirección de entrega'}</h3>
    <p className="text-sm text-gray-600">Agrega la dirección en la que deseas recibir tus productos.</p>
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
    <fieldset disabled={busy} className="min-w-0 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm" htmlFor={`${id}-name`}>Nombre de quien recibe<input id={`${id}-name`} aria-label="Nombre de quien recibe" required maxLength={200} autoComplete="name" className={input} value={form.recipient_name} aria-invalid={!!errors.recipient_name} aria-describedby={errors.recipient_name ? id+'-recipient_name-error' : undefined} onChange={e=>setForm({...form,recipient_name:e.target.value})}/>{fieldError('recipient_name')}</label>
        <label className="text-sm" htmlFor={`${id}-phone`}>Número de teléfono<input id={`${id}-phone`} aria-label="Número de teléfono" required type="tel" pattern="[+0-9() .-]{7,30}" maxLength={30} title="Escribe un número de teléfono válido." autoComplete="tel" className={input} value={form.phone} aria-invalid={!!errors.phone} aria-describedby={errors.phone ? id+'-phone-error' : undefined} onChange={e=>setForm({...form,phone:e.target.value})}/>{fieldError('phone')}</label>
      </div>
      <TCCAddressFields compact errors={errors} value={{...form,tcc_city_code:form.tcc_city_code||'',complement:form.complement||'',neighborhood:form.neighborhood||'',delivery_instructions:form.delivery_instructions||''}} onChange={patch=>setForm(previous=>({...previous,...patch}))}/>
      <label className="block text-sm" htmlFor={`${id}-street`}>Dirección<input id={`${id}-street`} aria-label="Dirección" required maxLength={500} autoComplete="street-address" className={input} value={form.address} aria-invalid={!!errors.address} aria-describedby={errors.address ? id+'-address-error' : undefined} onChange={e=>setForm({...form,address:e.target.value})}/>{fieldError('address')}</label>
      <div className="grid gap-4 sm:grid-cols-2">
        {(['neighborhood','complement','postal_code','label'] as const).map(field=><label className="text-sm" key={field}>{{neighborhood:'Barrio (opcional)',complement:'Apartamento o complemento (opcional)',postal_code:'Código postal (opcional)',label:'Nombre de la dirección'}[field]}<input required={field==='label'} maxLength={{neighborhood:100,complement:200,postal_code:20,label:50}[field]} className={input} value={form[field]||''} onChange={e=>setForm({...form,[field]:e.target.value})}/>{fieldError(field)}</label>)}
      </div>
      <label className="block text-sm">Indicaciones para llegar (opcional)<textarea maxLength={300} className={input} value={form.delivery_instructions||''} onChange={e=>setForm({...form,delivery_instructions:e.target.value})}/></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!form.is_default} onChange={e=>setForm({...form,is_default:e.target.checked})}/>Establecer como dirección predeterminada</label>
      <div className="flex flex-wrap gap-3"><button className="min-h-11 rounded-lg bg-[#001575] px-4 py-2 text-white disabled:opacity-60" type="submit">{busy?'Guardando…':'Guardar dirección'}</button><button type="button" className="min-h-11 rounded-lg border px-4 py-2" onClick={onCancel}>Cancelar</button></div>
    </fieldset>
  </form>
}
