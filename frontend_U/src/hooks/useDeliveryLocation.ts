import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import addressesService from '../services/addresses'
import { shippingDestinationKey, shippingService, type TCCCity } from '../services/shipping'
import {useDeliveryAddresses} from './useDeliveryAddresses'
import {useDeliveryCatalog} from './useDeliveryCatalog'

export const deliveryLocationChanged = 'delivery:location-changed'
export function notifyDeliveryLocation() { window.dispatchEvent(new Event(deliveryLocationChanged)) }

export function addressLocation(address:import('../services/addresses').UserAddress,catalog:TCCCity[]){
  if(address.tcc_city_code)return catalog.find(city=>city.code===address.tcc_city_code)||null
  const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'')
  const municipality=(text:string)=>normalize(text).replace(/^santiagodecali$/,'cali')
  const matches=catalog.filter(city=>municipality(city.city)===municipality(address.city)&&normalize(city.department)===normalize(address.department))
  return matches.length===1?matches[0]:null
}

export function readDeliverySelection(userId:string|undefined,catalog:TCCCity[],addresses:import('../services/addresses').UserAddress[]=[]){
  const valid=(code:unknown)=>catalog.find(city=>city.code===code)||null
  let stored:{address_id?:number;tcc_city_code?:string;manual_location?:boolean}|null=null
  try{stored=JSON.parse(sessionStorage.getItem(shippingDestinationKey(userId||'guest'))||'null')}catch{/* Optional storage. */}
  const chosen=userId?addresses.find(address=>address.id===stored?.address_id):undefined
  if(chosen&&addressLocation(chosen,catalog))return {location:addressLocation(chosen,catalog),address:chosen}
  if(userId){
    const address=addresses.find(value=>value.is_default&&addressLocation(value,catalog))||addresses.find(value=>addressLocation(value,catalog))
    return address?{location:addressLocation(address,catalog),address}:{location:null}
  }
  if(stored?.manual_location&&!stored.address_id)return {location:valid(stored.tcc_city_code)}
  if(valid(stored?.tcc_city_code))return {location:valid(stored?.tcc_city_code)}
  return {location:null}
}

/** Only municipalities are returned to catalogue cards; private addresses remain account scoped. */
export async function resolveDeliveryLocation(userId:string|undefined):Promise<TCCCity|null>{
  const catalog=await shippingService.cities()
  const addresses=userId?await addressesService.getAll():[]
  return readDeliverySelection(userId,catalog,addresses).location
}

export function useDeliveryLocation() {
  const { user, isLoading } = useAuth()
  const cache = useQueryClient()
  const catalog=useDeliveryCatalog()
  const addresses=useDeliveryAddresses()
  const key = ['delivery-location', user?.id || 'guest',catalog.dataUpdatedAt,addresses.dataUpdatedAt]
  useEffect(() => {
    const update = () => { void cache.invalidateQueries({queryKey: ['delivery-location']}) }
    window.addEventListener(deliveryLocationChanged, update)
    return () => window.removeEventListener(deliveryLocationChanged, update)
  }, [cache])
  return useQuery({queryKey: key, queryFn: () => {
    if(catalog.error)throw catalog.error
    if(user&&addresses.error)throw addresses.error
    const selected=readDeliverySelection(user?.id,catalog.data||[],addresses.data||[])
    return selected.location?{...selected.location,address_id:selected.address?.id}:null
  }, enabled: !isLoading&&!catalog.isPending&&(!user||!addresses.isPending),
    staleTime: 60000, retry: false})
}
