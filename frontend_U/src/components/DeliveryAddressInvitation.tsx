import {useEffect,useState} from 'react'
import {Link,useLocation} from 'react-router-dom'
import {useAuth} from '../context/AuthContext'

export default function DeliveryAddressInvitation(){
  const {isAuthenticated}=useAuth()
  const {pathname}=useLocation()
  const [visible,setVisible]=useState(false)
  useEffect(()=>{try{setVisible(isAuthenticated&&sessionStorage.getItem('delivery-address-invitation')==='yes')}catch{setVisible(false)}},[isAuthenticated,pathname])
  const dismiss=()=>{setVisible(false);try{sessionStorage.removeItem('delivery-address-invitation')}catch{/* Optional. */}}
  if(!visible||pathname==='/direcciones'||pathname==='/login')return null
  return <aside aria-label="Dirección de entrega opcional" className="mx-auto my-4 max-w-7xl rounded-xl border bg-blue-50 p-4 text-sm">
    <p className="font-semibold">Tu cuenta está lista. ¿Dónde recibirás tus pedidos?</p>
    <p>Guarda tu dirección para agilizar la compra. El checkout mostrará la tarifa de envío antes del pago.</p>
    <div className="mt-2 flex flex-wrap gap-4"><Link className="min-h-11 inline-flex items-center font-semibold text-blue-800 underline" to="/direcciones?nueva=1">Agregar dirección de entrega</Link>
      <button type="button" className="min-h-11 underline" onClick={dismiss}>Ahora no, seguir navegando</button></div>
  </aside>
}
