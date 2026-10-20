import { useEffect, useState } from 'react'
import { shippingService } from '../services/shipping'

export function useShippingConfig() {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [error, setError] = useState('')
  const [requiresConfirmation, setRequiresConfirmation] = useState(true)
  useEffect(() => {
    let active = true
    shippingService.config().then(result => {
      if (typeof result.enabled !== 'boolean') throw new Error('Invalid shipping config')
      if (active) { setEnabled(result.enabled);setRequiresConfirmation(result.requires_shipping_confirmation===true) }
    })
      .catch(() => { if (active) setError('No fue posible consultar la configuración de envíos. Actualiza la página.') })
    return () => { active = false }
  }, [])
  return { enabled, error, requiresConfirmation }
}
