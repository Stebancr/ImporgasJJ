import { useEffect, useRef } from 'react'

interface WompiCheckoutProps {
  /** Wompi public key – use test key for sandbox */
  publicKey: string
  /** Total in COP cents (multiply pesos × 100) */
  amountInCents: number
  /** Unique per-transaction reference (e.g. "ORDER-1234") */
  reference: string
  /** URL Wompi redirects after payment */
  redirectUrl?: string
  /** Optional SHA-256 integrity signature (required in production) */
  integrity?: string
  className?: string
}

/**
 * Renders the official Wompi widget button inside a hosted-checkout form.
 * Loads the Wompi script once and injects it into the form container.
 */
export default function WompiCheckout({
  publicKey,
  amountInCents,
  reference,
  redirectUrl,
  integrity,
  className = '',
}: WompiCheckoutProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Clear previous widget if any
    container.innerHTML = ''

    const form = document.createElement('form')
    form.action = 'https://checkout.wompi.co/p/'
    form.method = 'GET'

    const fields: Record<string, string> = {
      'public-key': publicKey,
      currency: 'COP',
      'amount-in-cents': String(amountInCents),
      reference,
    }
    if (redirectUrl) fields['redirect-url'] = redirectUrl
    if (integrity) fields['signature:integrity'] = integrity

    Object.entries(fields).forEach(([name, value]) => {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = name
      input.value = value
      form.appendChild(input)
    })

    const script = document.createElement('script')
    script.src = 'https://checkout.wompi.co/widget.js'
    script.setAttribute('data-render', 'button')
    form.appendChild(script)

    container.appendChild(form)

    return () => {
      container.innerHTML = ''
    }
  }, [publicKey, amountInCents, reference, redirectUrl, integrity])

  return <div ref={containerRef} className={className} />
}
