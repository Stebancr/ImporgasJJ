import {useQuery} from '@tanstack/react-query'
import {shippingService} from '../services/shipping'

/** Catalogue state is independent from provider configuration and product data. */
export function useDeliveryCatalog() {
  const query=useQuery({queryKey:['delivery-catalog'],queryFn:()=>shippingService.cities(),
    staleTime:300000,retry:false,refetchOnWindowFocus:false})
  return {...query,status:query.isPending?'loading':query.isError?'error':query.data?.length?'success':'empty'}
}
