import { useEffect, useState } from 'react'
import { shippingService, type TCCAddress, type TCCCity } from '../services/shipping'

export default function TCCAddressFields({value,onChange}:{value:TCCAddress;onChange:(patch:Partial<TCCAddress>&{city?:string;department?:string})=>void}) {
  const [cities,setCities]=useState<TCCCity[]>([])
  const [error,setError]=useState(false)
  useEffect(()=>{let active=true;shippingService.cities().then(data=>{if(active)setCities(data)}).catch(()=>{if(active)setError(true)});return()=>{active=false}},[])
  return <div className="space-y-3 rounded-lg border p-4">
    <label className="block text-sm font-medium">Ciudad de entrega TCC
      <select aria-label="Ciudad de entrega TCC" required className="mt-1 w-full rounded border bg-white px-3 py-2" value={value.tcc_city_code} onChange={e=>{const city=cities.find(city=>city.code===e.target.value);onChange({tcc_city_code:e.target.value,city:city?.city||'',department:city?.department||''})}}>
        <option value="">Selecciona departamento y municipio</option>{cities.map(city=><option key={city.code} value={city.code}>{city.department} — {city.city}</option>)}
      </select>
    </label>
    {error&&<p role="alert" className="text-sm text-red-600">No fue posible cargar las ciudades TCC. Actualiza la página antes de cotizar.</p>}
    {(['complement','neighborhood','delivery_instructions'] as const).map(field=><label className="block text-sm" key={field}>{{complement:'Complemento (opcional)',neighborhood:'Barrio (opcional)',delivery_instructions:'Indicaciones de entrega (opcional)'}[field]}<input className="mt-1 w-full rounded border px-3 py-2" maxLength={field==='delivery_instructions'?300:field==='neighborhood'?100:200} value={value[field]} onChange={e=>onChange({[field]:e.target.value})}/></label>)}
  </div>
}
