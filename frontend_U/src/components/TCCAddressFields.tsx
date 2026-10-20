import {useEffect,useMemo,useState,useId} from 'react'
import {shippingService,type TCCAddress,type TCCCity} from '../services/shipping'

const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es').trim()
const readable=(text:string)=>text.toLocaleLowerCase('es').replace(/(^|\s)\S/g,char=>char.toLocaleUpperCase('es'))

export default function TCCAddressFields({value,onChange,compact=false}:{
  value:TCCAddress&{department?:string;city?:string};
  onChange:(patch:Partial<TCCAddress>&{city?:string;department?:string})=>void;compact?:boolean
}){
  const id=useId()
  const [cities,setCities]=useState<TCCCity[]>([])
  const [loading,setLoading]=useState(true),[error,setError]=useState(false),[retry,setRetry]=useState(0)
  useEffect(()=>{let active=true;setLoading(true);setError(false)
    shippingService.cities().then(data=>{if(active)setCities(data)}).catch(()=>{if(active)setError(true)}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[retry])
  const selected=cities.find(city=>city.code===value.tcc_city_code)
  const department=selected?.department||value.department||''
  const departments=useMemo(()=>Array.from(new Set(cities.map(city=>city.department))).sort((a,b)=>a.localeCompare(b,'es')),[cities])
  const options=useMemo(()=>Array.from(new Map(cities.filter(city=>city.department===department).map(city=>[normalize(city.city),city])).values()).sort((a,b)=>a.city.localeCompare(b.city,'es')),[cities,department])
  const input='mt-1 min-h-11 w-full min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-700 disabled:bg-gray-100 disabled:text-gray-500'
  return <div className="min-w-0 space-y-3">
    {loading&&<p role="status" className="text-sm">Cargando ubicaciones de entrega…</p>}
    {error&&<p role="alert" className="text-sm text-red-700">No fue posible cargar las ubicaciones. <button type="button" className="underline min-h-11" onClick={()=>setRetry(n=>n+1)}>Reintentar</button></p>}
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="min-w-0">
        <label htmlFor={`${id}-department`} className="block text-sm font-medium">Departamento de entrega</label>
        <select id={`${id}-department`} required className={input} disabled={loading||error} value={department} onChange={e=>onChange({department:e.target.value,city:'',tcc_city_code:''})}>
          <option value="">Selecciona un departamento</option>
          {departments.map(d=><option key={d} value={d}>{readable(d)}</option>)}
        </select>
      </div>
      <div className="min-w-0">
        <label htmlFor={`${id}-city`} className="block text-sm font-medium">Ciudad o municipio de entrega</label>
        <select id={`${id}-city`} required className={input} disabled={!department||loading||error} value={value.tcc_city_code} onChange={e=>{const city=options.find(city=>city.code===e.target.value);onChange({tcc_city_code:city?.code||'',city:city?.city||'',department})}}>
          <option value="">{department?'Selecciona una ciudad o municipio':'Selecciona primero un departamento'}</option>
          {options.map(city=><option key={city.code} value={city.code}>{readable(city.city)}</option>)}
        </select>
        {department&&!loading&&!error&&!options.length&&<p className="text-sm">No hay municipios disponibles para este departamento.</p>}
      </div>
    </div>
    {!compact&&(['complement','neighborhood','delivery_instructions'] as const).map(field=><label className="block text-sm" key={field}>{{complement:'Apartamento, interior u otro complemento (opcional)',neighborhood:'Barrio (opcional)',delivery_instructions:'Indicaciones para llegar (opcional)'}[field]}<input className={input} maxLength={field==='delivery_instructions'?300:field==='neighborhood'?100:200} value={value[field]} onChange={e=>onChange({[field]:e.target.value})}/></label>)}
  </div>
}
