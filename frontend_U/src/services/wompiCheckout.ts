import type { WompiCheckoutIntent } from './orders'

type WidgetOptions = {
  currency: 'COP'; amountInCents: number; reference: string; publicKey: string
  signature: { integrity: string }
  customerData: { email: string; fullName: string }
}
type WidgetConstructor = new (options: WidgetOptions) => {
  open(callback: (result: { transaction?: { id: string } }) => void): void
}
declare global { interface Window { WidgetCheckout?: WidgetConstructor } }

let widgetPromise: Promise<WidgetConstructor> | undefined
export function loadWompiWidget(): Promise<WidgetConstructor> {
  if (window.WidgetCheckout) return Promise.resolve(window.WidgetCheckout)
  if (widgetPromise) return widgetPromise
  widgetPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const timeout = window.setTimeout(() => fail(), 15000)
    const fail = () => {
      window.clearTimeout(timeout)
      script.remove()
      widgetPromise = undefined
      reject(new Error('No se pudo cargar Wompi. Comprueba tu conexión e inténtalo de nuevo.'))
    }
    script.src = 'https://checkout.wompi.co/widget.js'
    script.async = true
    script.onerror = fail
    script.onload = () => {
      window.clearTimeout(timeout)
      if (!window.WidgetCheckout) { fail(); return }
      resolve(window.WidgetCheckout)
    }
    document.head.appendChild(script)
  })
  return widgetPromise
}
export function getWompiOptions(intent: WompiCheckoutIntent, fallbackKey: string, email: string, fullName: string): WidgetOptions {
  const publicKey = intent.wompi_public_key || fallbackKey
  const amountInCents = Math.round(Number(intent.total) * 100)
  if (!/^pub_(test|prod)_/.test(publicKey) || publicKey.includes('YOUR_KEY')) throw new Error('El pago con Wompi no está disponible en este momento.')
  if (!Number.isSafeInteger(amountInCents) || amountInCents <= 0 || !intent.wompi_reference || !/^[a-f0-9]{64}$/i.test(intent.wompi_signature)) {
    throw new Error('No se pudo validar el importe del pago. Inténtalo de nuevo.')
  }
  return { currency: 'COP', amountInCents, reference: intent.wompi_reference, publicKey,
    signature: { integrity: intent.wompi_signature }, customerData: { email, fullName } }
}

export function getWompiCheckoutUrl(options: WidgetOptions, redirectUrl?: string): string {
  const params = new URLSearchParams({
    'public-key': options.publicKey, currency: options.currency,
    'amount-in-cents': String(options.amountInCents), reference: options.reference,
    'signature:integrity': options.signature.integrity,
    'customer-data:email': options.customerData.email,
    'customer-data:full-name': options.customerData.fullName,
  })
  if (redirectUrl) params.set('redirect-url', redirectUrl)
  return `https://checkout.wompi.co/p/?${params}`
}
