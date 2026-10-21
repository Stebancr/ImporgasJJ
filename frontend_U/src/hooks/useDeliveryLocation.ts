import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import addressesService from '../services/addresses'
import { shippingDestinationKey, shippingService, type TCCCity } from '../services/shipping'

export const deliveryLocationChanged = 'delivery:location-changed'
export function notifyDeliveryLocation() { window.dispatchEvent(new Event(deliveryLocationChanged)) }

/** Validate stored codes against the carrier catalogue; never persist prices or coordinates. */
export async function resolveDeliveryLocation(userId: string | undefined): Promise<TCCCity | null> {
  const catalog = await shippingService.cities()
  const valid = (code: unknown) => catalog.find(city => city.code === code) || null
  let stored: {tcc_city_code?: string; manual_location?: boolean} | null = null
  try {
    stored = JSON.parse(sessionStorage.getItem(shippingDestinationKey(userId || 'guest')) || 'null')
  } catch { /* Storage is optional. */ }
  // A deliberate change by this customer overrides automatic defaults for this session.
  if (stored?.manual_location) return valid(stored.tcc_city_code)
  if (userId) {
    const addresses = await addressesService.getAll()
    const defaultAddress = addresses.find(address => address.is_default && valid(address.tcc_city_code))
    if (defaultAddress) return valid(defaultAddress.tcc_city_code)
    const previous = await shippingService.destination()
    if (valid(previous.destination?.code)) return valid(previous.destination?.code)
  }
  if (valid(stored?.tcc_city_code)) return valid(stored?.tcc_city_code)
  if (userId) {
    try {
      const guest = JSON.parse(sessionStorage.getItem(shippingDestinationKey('guest')) || 'null')
      return valid(guest?.tcc_city_code)
    } catch { /* No trusted fallback. */ }
  }
  return null
}

export function useDeliveryLocation() {
  const { user, isLoading } = useAuth()
  const cache = useQueryClient()
  const key = ['delivery-location', user?.id || 'guest']
  useEffect(() => {
    const update = () => { void cache.invalidateQueries({queryKey: ['delivery-location']}) }
    window.addEventListener(deliveryLocationChanged, update)
    return () => window.removeEventListener(deliveryLocationChanged, update)
  }, [cache])
  return useQuery({queryKey: key, queryFn: () => resolveDeliveryLocation(user?.id), enabled: !isLoading,
    staleTime: 60000, retry: false})
}
