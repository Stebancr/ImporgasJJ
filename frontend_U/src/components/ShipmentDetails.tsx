import { useState } from 'react'
import type { ShipmentInfo } from '../services/shipping'
import adminApi from '../admin/services/admin_api'

export default function ShipmentDetails({shipment,orderId,admin=false,onUpdated}:{shipment?:ShipmentInfo|null;orderId?:number;admin?:boolean;onUpdated?:()=>void}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  if(!shipment)return null
  const retry=async()=>{setBusy(true);setError('');try{await adminApi.post(`/shipping/orders/${orderId}/retry`);onUpdated?.()}catch(e:any){setError(e.response?.data?.error||'No fue posible solicitar el reintento.')}finally{setBusy(false)}}
  return <section className="my-4 space-y-3 rounded-xl border bg-white p-4">
    <h3 className="font-semibold">Envío con TCC</h3>
    <p>{shipment.state_label}</p>
    <p>Guía o remesa: <strong>{shipment.waybill||'Pendiente de creación'}</strong></p>
    <p className="text-sm text-gray-600">Última actualización: {new Date(shipment.last_update).toLocaleString('es-CO')}</p>
    {shipment.tracking_url&&<a href={shipment.tracking_url} target="_blank" rel="noopener noreferrer" className="inline-block text-blue-700 underline">Rastrear en TCC</a>}
    <p className="text-sm text-gray-600">{shipment.tracking_url?'Consulta el estado de transporte en el enlace oficial de TCC.':'El enlace de seguimiento estará disponible cuando se cree el despacho.'}</p>
    {admin&&<>
      <p className="text-sm text-gray-600">Seguimiento por API pendiente del contrato de TCC. No se consultan ni modifican estados de entrega automáticamente.</p>
      <p>Cuenta: {shipment.account_type} ({shipment.account}) · Ambiente: {shipment.environment}</p>
      <p>Peso real: {shipment.real_kg} kg · Volumétrico: {shipment.volumetric_kg} kg · Facturable calculado: {shipment.billable_kg} kg</p>
      <p>Tarifa TCC: ${shipment.tcc_rate} · Recargo: ${shipment.surcharge} · Cobrado: ${shipment.charged}</p>
      {shipment.shipping_discount!==undefined&&<><p>Subsidio de envío: ${shipment.shipping_discount}</p><p>Envío gratis aplicado: {shipment.free_shipping_applied?'Sí':'No'}</p></>}
      {shipment.last_error&&<p role="alert" className="text-red-700">{shipment.last_error}</p>}
      {shipment.retry_allowed&&<button type="button" disabled={busy} onClick={retry} className="rounded border px-3 py-2">{busy?'Solicitando…':'Reintentar creación en TCC'}</button>}
      {Object.entries(shipment.documents||{}).map(([key,url])=><a key={key} className="mr-3 inline-block text-blue-700 underline" href={url} target="_blank" rel="noopener noreferrer">{{label:'Etiqueta TCC',relation:'Relación de despacho',waybill:'Documento de remesa'}[key]||'Documento TCC'}</a>)}
      {error&&<p role="alert" className="text-red-700">{error}</p>}
    </>}
    <ol className="space-y-2 border-l pl-4 text-sm">{shipment.history.map((event,index)=><li key={`${event.created_at}-${index}`}><time>{new Date(event.created_at).toLocaleString('es-CO')}</time> — {event.description}</li>)}</ol>
  </section>
}
