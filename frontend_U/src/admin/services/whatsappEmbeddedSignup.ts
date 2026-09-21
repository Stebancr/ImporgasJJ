import type { WhatsAppCoexistenceConfig } from './admin_chat'

type FacebookLoginResponse = {
  authResponse?: { code?: string }
  status?: string
}

type EmbeddedSignupEvent = {
  type?: string
  event?: string
  data?: {
    waba_id?: string | number
    phone_number_id?: string | number
    business_id?: string | number
    error_message?: string
    error_code?: string | number
    current_step?: string
  }
}

declare global {
  interface Window {
    FB?: {
      init: (options: Record<string, unknown>) => void
      login: (
        callback: (response: FacebookLoginResponse) => void,
        options: Record<string, unknown>,
      ) => void
    }
    fbAsyncInit?: () => void
  }
}

const SDK_ID = 'facebook-jssdk'
const META_MESSAGE_ORIGINS = new Set([
  'https://www.facebook.com',
  'https://web.facebook.com',
  'https://business.facebook.com',
])

const loadFacebookSdk = (config: WhatsAppCoexistenceConfig): Promise<void> => new Promise((resolve, reject) => {
  const initialize = () => {
    if (!window.FB) {
      reject(new Error('Meta no cargó el SDK de Facebook.'))
      return
    }
    window.FB.init({
      appId: config.app_id,
      cookie: true,
      xfbml: true,
      version: config.graph_api_version,
    })
    resolve()
  }
  if (window.FB) {
    initialize()
    return
  }
  window.fbAsyncInit = initialize
  const existing = document.getElementById(SDK_ID)
  if (existing) return
  const script = document.createElement('script')
  script.id = SDK_ID
  script.src = 'https://connect.facebook.net/en_US/sdk.js'
  script.async = true
  script.defer = true
  script.crossOrigin = 'anonymous'
  script.onerror = () => reject(new Error('No fue posible cargar el SDK oficial de Meta.'))
  document.body.appendChild(script)
})

export interface WhatsAppEmbeddedSignupResult {
  code: string
  event: 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING'
  waba_id: string
  phone_number_id?: string
  business_id?: string
}

export async function launchWhatsAppCoexistence(
  config: WhatsAppCoexistenceConfig,
): Promise<WhatsAppEmbeddedSignupResult> {
  await loadFacebookSdk(config)
  return new Promise((resolve, reject) => {
    let authorizationCode = ''
    let completion: EmbeddedSignupEvent | null = null
    let settled = false

    const cleanup = () => {
      window.removeEventListener('message', onMessage)
      window.clearTimeout(timeout)
    }
    const fail = (message: string) => {
      if (settled) return
      settled = true
      cleanup()
      reject(new Error(message))
    }
    const finish = () => {
      const data = completion?.data
      if (settled || !authorizationCode || !data?.waba_id) return
      settled = true
      cleanup()
      resolve({
        code: authorizationCode,
        event: 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
        waba_id: String(data.waba_id),
        ...(data.phone_number_id ? { phone_number_id: String(data.phone_number_id) } : {}),
        ...(data.business_id ? { business_id: String(data.business_id) } : {}),
      })
    }
    const onMessage = (message: MessageEvent) => {
      if (!META_MESSAGE_ORIGINS.has(message.origin)) return
      let payload: EmbeddedSignupEvent
      try {
        payload = typeof message.data === 'string' ? JSON.parse(message.data) : message.data
      } catch {
        return
      }
      if (!payload || payload.type !== 'WA_EMBEDDED_SIGNUP') return
      if (payload.event === 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING') {
        completion = payload
        finish()
      } else if (payload.event === 'CANCEL') {
        fail('La conexión de WhatsApp fue cancelada antes de finalizar.')
      } else if (payload.event === 'ERROR') {
        const detail = String(payload.data?.error_message || 'Meta rechazó el flujo de conexión.')
          .replace(/\s+/g, ' ')
          .slice(0, 300)
        const code = payload.data?.error_code ? ` Código ${payload.data.error_code}.` : ''
        fail(`${detail}${code}`)
      }
    }
    window.addEventListener('message', onMessage)
    const timeout = window.setTimeout(
      () => fail('La conexión de WhatsApp expiró. Iníciala nuevamente.'),
      10 * 60 * 1000,
    )
    const extras: Record<string, unknown> = {
      setup: {
        app_only_install: false,
      },
      featureType: config.feature_type,
    }
    if (config.embedded_signup_version !== '4') extras.sessionInfoVersion = '3'
    window.FB!.login((response) => {
      const code = response.authResponse?.code
      if (!code) {
        fail('Meta no devolvió autorización para conectar WhatsApp.')
        return
      }
      authorizationCode = code
      finish()
    }, {
      config_id: config.config_id,
      response_type: 'code',
      override_default_response_type: true,
      extras,
    })
  })
}
