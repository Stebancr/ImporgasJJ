import {useId} from 'react'
import locations from '../data/delivery-locations.json'

type Destination={department:string;city:string}
const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim()
const departments=[...new Set(locations.map(item=>item.department))].sort((a,b)=>a.localeCompare(b,'es'))

/** Geographic names only: independent of carriers, credentials and external APIs. */
export default function DeliveryLocationFields({value,onChange}:{value:Destination;onChange:(patch:Partial<Destination>)=>void}){
 const id=useId()
 const choices=locations.filter(item=>normalize(item.department)===normalize(value.department)).map(item=>item.city)
 const options=(values:string[],current:string)=>[...(current?[current]:[]),...values.filter(item=>normalize(item)!==normalize(current))]
 const input='mt-1 min-h-11 w-full min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-700'
 return <div className="grid min-w-0 gap-4 sm:grid-cols-2">
  <label className="min-w-0 text-sm" htmlFor={`${id}-department`}>Departamento<select id={`${id}-department`} aria-label="Departamento" required className={input} value={value.department} onChange={event=>onChange({department:event.target.value,city:''})}>
   <option value="">Selecciona un departamento</option>{options(departments,value.department).map(item=><option key={item} value={item}>{item}</option>)}
  </select></label>
  <label className="min-w-0 text-sm" htmlFor={`${id}-city`}>Ciudad<select id={`${id}-city`} aria-label="Ciudad" required disabled={!value.department} className={input} value={value.city} onChange={event=>onChange({city:event.target.value})}>
   <option value="">Selecciona una ciudad</option>{options(choices,value.city).map(item=><option key={item} value={item}>{item}</option>)}
  </select></label>
 </div>
}
