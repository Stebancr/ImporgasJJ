import { useQuery } from '@tanstack/react-query'
import { shippingService } from '../services/shipping'

export function useShippingConfig() {
  const query = useQuery({queryKey: ['shipping-config'], queryFn: async () => {
    const result = await shippingService.config()
    if (typeof result.enabled !== 'boolean') throw new Error('Invalid shipping config')
    return result
  }, staleTime: 60000, retry: false, refetchOnWindowFocus:false})
  return { enabled: query.data?.enabled ?? null, status: query.isPending?'loading':query.isError?'error':query.data.enabled?'success':'unavailable',
    loading:query.isFetching, retry:query.refetch, cause:query.error,
    error: query.isError ? 'No fue posible consultar la configuración de envíos.' : '' }
}
