import {useEffect,useState} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {useAuth} from '../../context/AuthContext'
import addressesService,{type UserAddress,type CreateAddressPayload} from '../../services/addresses'
import DeliveryAddressForm from '../../components/DeliveryAddressForm'
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '../../components/ui/dialog'

export default function AddressesPage(){
  const {user}=useAuth()
  const [params]=useSearchParams()
  const [addresses,setAddresses]=useState<UserAddress[]>([])
  const [loading,setLoading]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [draft,setDraft]=useState<(Partial<CreateAddressPayload>&{id?:number})|null>(params.get('nueva')==='1'?{recipient_name:user?.name||'',phone:user?.phone||''}:null)
  const [deleting,setDeleting]=useState<UserAddress|null>(null)
  const load=async()=>{setLoading(true);setError('');try{setAddresses(await addressesService.getAll())}catch(e){setError(e instanceof Error?e.message:'No fue posible cargar tus direcciones.')}finally{setLoading(false)}}
  useEffect(()=>{void load()},[])
  const saved=(address:UserAddress)=>{setAddresses(previous=>[address,...previous.filter(item=>item.id!==address.id).map(item=>address.is_default?{...item,is_default:false}:item)]);setDraft(null);try{sessionStorage.removeItem('delivery-address-invitation')}catch{/* Optional storage. */}}
  const remove=async()=>{if(!deleting||busy)return;setBusy(true);setError('');try{await addressesService.delete(deleting.id);setAddresses(previous=>previous.filter(item=>item.id!==deleting.id));setDeleting(null)}catch(e){setError(e instanceof Error?e.message:'No fue posible eliminar la dirección.')}finally{setBusy(false)}}
  const makeDefault=async(address:UserAddress)=>{setBusy(true);setError('');try{saved(await addressesService.update(address.id,{is_default:true}))}catch(e){setError(e instanceof Error?e.message:'No fue posible seleccionar la dirección.')}finally{setBusy(false)}}
  return <div className="min-h-screen bg-gray-50 py-8"><div className="mx-auto max-w-4xl space-y-5 px-4">
    <h1 className="text-3xl font-bold">Direcciones de entrega</h1><p>Agrega la dirección en la que deseas recibir tus productos.</p>
    {params.get('nueva')==='1'&&<Link className="block underline min-h-11" to="/productos" onClick={()=>{try{sessionStorage.removeItem('delivery-address-invitation')}catch{/* Optional. */}}}>Ahora no, seguir explorando productos</Link>}
    {error&&<p role="alert" className="text-red-700">{error} <button type="button" className="underline" onClick={load}>Reintentar</button></p>}
    {loading&&<p role="status">Cargando direcciones…</p>}
    {!draft&&<button className="min-h-11 rounded-lg bg-[#001575] px-4 py-2 text-white" onClick={()=>setDraft({recipient_name:user?.name||'',phone:user?.phone||'',is_default:addresses.length===0})}>Nueva dirección</button>}
    {draft&&<DeliveryAddressForm key={draft.id||'new'} initial={draft} onSaved={saved} onCancel={()=>setDraft(null)}/>}
    {!loading&&!addresses.length&&<p>No tienes direcciones guardadas.</p>}
    {addresses.map(address=><article key={address.id} className="rounded-xl border bg-white p-5 space-y-2 break-words">
      <div className="flex flex-wrap justify-between gap-2"><h2 className="font-semibold">{address.label}</h2>{address.is_default&&<span className="rounded bg-green-100 px-2 py-1 text-sm text-green-800">Predeterminada</span>}</div>
      <p>{address.recipient_name} · {address.phone}</p><p>{address.address} {address.complement}</p><p>{address.neighborhood}</p><p>{address.city}, {address.department} {address.postal_code}</p><p>{address.delivery_instructions}</p>
      <div className="flex flex-wrap gap-3"><button disabled={busy} className="min-h-11 underline text-[#001575]" onClick={()=>setDraft(address)}>Editar</button>{!address.is_default&&<button disabled={busy} className="min-h-11 underline text-[#001575]" onClick={()=>makeDefault(address)}>Usar como predeterminada</button>}<button disabled={busy} className="min-h-11 underline text-red-700" onClick={()=>setDeleting(address)}>Eliminar</button></div>
    </article>)}
    <Dialog open={!!deleting} onOpenChange={open=>{if(!open&&!busy)setDeleting(null)}}><DialogContent><DialogTitle>Eliminar dirección</DialogTitle><DialogDescription>¿Eliminar «{deleting?.label}»? Los pedidos existentes conservarán su dirección de entrega.</DialogDescription><div className="flex gap-3"><button disabled={busy} onClick={()=>setDeleting(null)} className="min-h-11 rounded border px-4">Cancelar</button><button disabled={busy} onClick={remove} className="min-h-11 rounded bg-red-700 px-4 text-white">Confirmar eliminación</button></div></DialogContent></Dialog>
  </div></div>
}
