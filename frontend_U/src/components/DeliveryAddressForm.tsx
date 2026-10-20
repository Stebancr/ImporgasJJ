import {useRef,useState,useId,type FormEvent} from 'react'
import addressesService,{type CreateAddressPayload,type UserAddress} from '../services/addresses'
import DeliveryLocationFields from './DeliveryLocationFields'

export default function DeliveryAddressForm({initial,onSaved,onCancel}:{
  initial:Partial<CreateAddressPayload>&{id?:number};onSaved:(address:UserAddress)=>void;onCancel:()=>void
}){
  const id=useId(),lock=useRef(false)
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  const [form,setForm]=useState<CreateAddressPayload>({label:'Casa',recipient_name:'',phone:'',address:'',city:'',department:'',postal_code:'',is_default:false,complement:'',neighborhood:'',delivery_instructions:'',...initial})
  const input='mt-1 min-h-11 w-full min-w-0 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-700'
  const submit=async(e:FormEvent)=>{
    e.preventDefault()
    if(lock.current)return
    lock.current=true;setBusy(true);setError('')
    try{
      const saved=initial.id?await addressesService.update(initial.id,form):await addressesService.create(form)
      onSaved(saved)
    }catch(e){setError(e instanceof Error?e.message:'No fue posible guardar la dirección. Tus datos se conservan.')}
    finally{lock.current=false;setBusy(false)}
  }
  return <form onSubmit={submit} className="min-w-0 space-y-4 rounded-xl border bg-white p-4 sm:p-6" aria-label="Formulario de dirección de entrega">
    <h3 className="text-lg font-semibold">{initial.id?'Editar dirección de entrega':'Nueva dirección de entrega'}</h3>
    <p className="text-sm text-gray-600">Agrega la dirección en la que deseas recibir tus productos.</p>
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
    <fieldset disabled={busy} className="min-w-0 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm" htmlFor={`${id}-name`}>Nombre de quien recibe<input id={`${id}-name`} required maxLength={200} autoComplete="name" className={input} value={form.recipient_name} onChange={e=>setForm({...form,recipient_name:e.target.value})}/></label>
        <label className="text-sm" htmlFor={`${id}-phone`}>Número de teléfono<input id={`${id}-phone`} required type="tel" pattern="[+0-9() .-]{7,30}" maxLength={30} title="Escribe un número de teléfono válido." autoComplete="tel" className={input} value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label>
      </div>
      <DeliveryLocationFields value={form} onChange={patch=>setForm(previous=>({...previous,...patch}))}/>
      <label className="block text-sm" htmlFor={`${id}-street`}>Dirección<input id={`${id}-street`} required maxLength={500} autoComplete="street-address" className={input} value={form.address} onChange={e=>setForm({...form,address:e.target.value})}/></label>
      <div className="grid gap-4 sm:grid-cols-2">
        {(['neighborhood','complement','postal_code','label'] as const).map(field=><label className="text-sm" key={field}>{{neighborhood:'Barrio (opcional)',complement:'Apartamento o complemento (opcional)',postal_code:'Código postal (opcional)',label:'Nombre de la dirección'}[field]}<input required={field==='label'} maxLength={{neighborhood:100,complement:200,postal_code:20,label:50}[field]} className={input} value={form[field]||''} onChange={e=>setForm({...form,[field]:e.target.value})}/></label>)}
      </div>
      <label className="block text-sm">Indicaciones para llegar (opcional)<textarea maxLength={300} className={input} value={form.delivery_instructions||''} onChange={e=>setForm({...form,delivery_instructions:e.target.value})}/></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!form.is_default} onChange={e=>setForm({...form,is_default:e.target.checked})}/>Establecer como dirección predeterminada</label>
      <div className="flex flex-wrap gap-3"><button className="min-h-11 rounded-lg bg-[#001575] px-4 py-2 text-white disabled:opacity-60" type="submit">{busy?'Guardando…':'Guardar dirección'}</button><button type="button" className="min-h-11 rounded-lg border px-4 py-2" onClick={onCancel}>Cancelar</button></div>
    </fieldset>
  </form>
}
