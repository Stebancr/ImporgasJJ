import { useQuery } from '@tanstack/react-query'
import { shippingService } from '../services/shipping'

export function useShippingConfig() {
  const query = useQuery({queryKey: ['shipping-config'], queryFn: async () => {
    const result = await shippingService.config()
    if (typeof result.enabled !== 'boolean') throw new Error('Invalid shipping config')
    return result
  }, staleTime: 60000, retry: false})
  return { enabled: query.data?.enabled ?? null, error: query.isError ? 'No fue posible consultar la configuración de envíos. Actualiza la página.' : '' }
}
