import type { ShippingProfile } from '../services/shipping'

export default function ShippingProfileFields({ value, onChange, price }: {value:ShippingProfile;onChange:(value:ShippingProfile)=>void;price?:string}) {
  return <fieldset className="space-y-3 rounded-lg border p-4">
    <legend className="px-2 font-semibold">Transporte del producto</legend>
    <label className="flex items-center gap-2"><input type="checkbox" checked={value.requires_shipping} onChange={e=>onChange({...value,requires_shipping:e.target.checked})}/>Requiere envío físico</label>
    {value.requires_shipping && <>
      <p className="text-sm text-gray-600">Registra peso, dimensiones y valor declarado de cada paquete. Cada unidad vendida usa la cantidad de paquetes indicada; sus dimensiones se conservan por separado.</p>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!value.declared_value_from_price} onChange={e=>onChange({...value,declared_value_from_price:e.target.checked})}/>Usar el precio de venta como valor declarado</label>
      {value.declared_value_from_price && <p className="text-sm text-muted-foreground">Valor por unidad vendida: {Number(price || 0).toLocaleString('es-CO')} COP. Se reparte entre sus paquetes; no se suma como cargo adicional al precio.</p>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {(['weight_kg','height_cm','width_cm','length_cm','declared_value'] as const).filter(field=>field!=='declared_value'||!value.declared_value_from_price).map(field=><label key={field} className="text-sm">
          {{weight_kg:'Peso por paquete (kg)',height_cm:'Alto por paquete (cm)',width_cm:'Ancho por paquete (cm)',length_cm:'Largo por paquete (cm)',declared_value:'Valor declarado por paquete (COP)'}[field]}
          <input className="mt-1 w-full rounded border px-3 py-2" type="number" min={field==='weight_kg'?'0.001':'0.01'} step={field==='weight_kg'?'0.001':'0.01'} value={value[field]??''} onChange={e=>onChange({...value,[field]:e.target.value===''?null:e.target.value})}/>
        </label>)}
        <label className="text-sm">Paquetes por unidad vendida<input className="mt-1 w-full rounded border px-3 py-2" type="number" min="1" max="100" step="1" value={value.packages_per_unit ?? ''} onChange={e=>onChange({...value,packages_per_unit:e.target.value===''?null:Number(e.target.value)})}/></label>
        <label className="text-sm">Clase de empaque<select className="mt-1 w-full rounded border px-3 py-2" value={value.packaging_code} onChange={e=>onChange({...value,packaging_code:e.target.value})}><option value="CLEM_CAJA">Caja</option><option value="CLEM_MEDIANA">Mediana</option></select></label>
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value.fragile} onChange={e=>onChange({...value,fragile:e.target.checked})}/>Frágil (indicación operativa interna)</label>
    </>}
  </fieldset>
}
