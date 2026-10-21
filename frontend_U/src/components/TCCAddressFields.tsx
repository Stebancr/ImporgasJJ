import {useEffect,useMemo,useState,useId} from 'react'
import {Autocomplete,TextField} from '@mui/material'
import {shippingService,type TCCAddress,type TCCCity} from '../services/shipping'

const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es').trim()
const readable=(text:string)=>text.toLocaleLowerCase('es').replace(/(^|\s)\S/g,char=>char.toLocaleUpperCase('es'))
const uniqueBy=<T,>(values:T[],key:(value:T)=>string)=>{
  const seen=new Set<string>()
  return values.filter(value=>{const id=key(value);if(seen.has(id))return false;seen.add(id);return true})
}

export default function TCCAddressFields({value,onChange,compact=false,errors={}}:{
  value:TCCAddress&{department?:string;city?:string};
  onChange:(patch:Partial<TCCAddress>&{city?:string;department?:string})=>void;compact?:boolean;errors?:Record<string,string>
}){
  const id=useId()
  const [cities,setCities]=useState<TCCCity[]>([])
  const [loading,setLoading]=useState(true),[error,setError]=useState(false),[retry,setRetry]=useState(0)
  useEffect(()=>{let active=true;setLoading(true);setError(false)
    shippingService.cities().then(data=>{if(active)setCities(data)}).catch(()=>{if(active)setError(true)}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[retry])
  useEffect(()=>{
    if(value.tcc_city_code||!value.city||!value.department)return
    const matches=cities.filter(item=>normalize(item.city)===normalize(value.city!)&&normalize(item.department)===normalize(value.department!))
    const codes=Array.from(new Set(matches.map(item=>item.code)))
    if(codes.length===1)onChange({tcc_city_code:matches[0].code,city:matches[0].city,department:matches[0].department})
  },[cities,value.tcc_city_code,value.city,value.department])
  const selected=cities.find(city=>city.code===value.tcc_city_code)
  const department=selected?.department||value.department||''
  const departments=useMemo(()=>uniqueBy(cities.map(city=>city.department),normalize).sort((a,b)=>a.localeCompare(b,'es')),[cities])
  const options=useMemo(()=>uniqueBy(cities.filter(city=>normalize(city.department)===normalize(department)),city=>normalize(city.city)).sort((a,b)=>a.city.localeCompare(b.city,'es')),[cities,department])
  const canonicalDepartment=departments.find(item=>normalize(item)===normalize(department))||null
  const canonicalCity=options.find(item=>item.code===value.tcc_city_code)||options.find(item=>normalize(item.city)===normalize(value.city||''))||null
  const input='mt-1 min-h-11 w-full min-w-0 rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-700'
  const sx={'& .MuiOutlinedInput-root':{minHeight:48,borderRadius:2},'& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline':{borderColor:'#001575'}}
  return <div className="min-w-0 space-y-3">
    {loading&&<p role="status" className="text-sm">Cargando ubicaciones de entrega…</p>}
    {error&&<p role="alert" className="text-sm text-red-700">No fue posible cargar las ubicaciones. <button type="button" className="underline min-h-11" onClick={()=>setRetry(n=>n+1)}>Reintentar</button></p>}
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Autocomplete id={`${id}-department`} disablePortal options={departments} value={canonicalDepartment}
        disabled={loading||error} loading={loading} getOptionLabel={readable} noOptionsText="No se encontraron departamentos"
        onChange={(_,next)=>onChange({department:next||'',city:'',tcc_city_code:''})} sx={sx}
        renderInput={params=><TextField {...params} slotProps={{...params.slotProps,htmlInput:{...params.slotProps.htmlInput,'aria-label':'Departamento de entrega'}}} label="Departamento de entrega" placeholder="Busca un departamento" required error={!!errors.department} helperText={errors.department||"Escribe para buscar y selecciona una opción"}/>}/>
      <Autocomplete id={`${id}-city`} disablePortal options={options} value={canonicalCity}
        disabled={!canonicalDepartment||loading||error} loading={loading} getOptionLabel={option=>readable(option.city)}
        isOptionEqualToValue={(option,current)=>option.code===current.code} noOptionsText="No se encontraron ciudades o municipios"
        onChange={(_,next)=>onChange({tcc_city_code:next?.code||'',city:next?.city||'',department:next?.department||canonicalDepartment||''})} sx={sx}
        renderInput={params=><TextField {...params} slotProps={{...params.slotProps,htmlInput:{...params.slotProps.htmlInput,'aria-label':'Ciudad o municipio de entrega'}}} label="Ciudad o municipio de entrega" placeholder="Busca una ciudad o municipio" required error={!!(errors.city||errors.tcc_city_code)} helperText={errors.city||errors.tcc_city_code||(!canonicalDepartment?'Selecciona primero un departamento':'Escribe para buscar y selecciona una opción')}/>}/>
    </div>
    {!compact&&(['complement','neighborhood','delivery_instructions'] as const).map(field=><label className="block text-sm" key={field}>{{complement:'Apartamento, interior u otro complemento (opcional)',neighborhood:'Barrio (opcional)',delivery_instructions:'Indicaciones para llegar (opcional)'}[field]}<input className={input} maxLength={field==='delivery_instructions'?300:field==='neighborhood'?100:200} value={value[field]} onChange={e=>onChange({[field]:e.target.value})}/></label>)}
  </div>
}
