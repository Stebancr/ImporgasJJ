import {useEffect} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {useAuth} from '../context/AuthContext'
import addressesService from '../services/addresses'

export function useDeliveryAddresses(){
  const {user,isAuthenticated,isLoading}=useAuth()
  const cache=useQueryClient()
  useEffect(()=>{
    const refresh=()=>{void cache.invalidateQueries({queryKey:['delivery-addresses',user?.id]})}
    window.addEventListener('delivery:addresses-changed',refresh)
    return()=>window.removeEventListener('delivery:addresses-changed',refresh)
  },[cache,user?.id])
  return useQuery({queryKey:['delivery-addresses',user?.id],queryFn:()=>addressesService.getAll(),
    enabled:isAuthenticated&&!isLoading,staleTime:60000,retry:false,refetchOnWindowFocus:false})
}
