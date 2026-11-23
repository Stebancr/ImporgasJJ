import crypto from 'node:crypto'
import axios from 'axios'
import { env } from '../config/env.js'

export async function crmPost<T>(path: string, body: unknown, policy = { attempts: 5, timeout: 20_000 }): Promise<T> {
  const raw = JSON.stringify(body)
  let lastError: unknown
  for (let attempt = 0; attempt < policy.attempts; attempt += 1) {
    const timestamp = Math.floor(Date.now() / 1000).toString()
    const requestId = crypto.randomUUID()
    const signature = crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN)
      .update(`${timestamp}.${requestId}.${raw}`).digest('hex')
    try {
      const response = await axios.post<T>(`${env.CRM_API_URL}${path}`, body, {
        timeout: policy.timeout,
        headers: {
          Authorization: `Bearer ${env.CRM_INTERNAL_SERVICE_TOKEN}`,
          'Content-Type': 'application/json',
          'X-Forwarded-Proto': 'https',
          'X-WhatsApp-Gateway-Timestamp': timestamp,
          'X-WhatsApp-Gateway-Request-ID': requestId,
          'X-WhatsApp-Gateway-Signature': signature,
        },
      })
      console.log(JSON.stringify({ event: 'gateway.crm_post', path, status: response.status, attempt: attempt + 1 }))
      return response.data
    } catch (error) {
      lastError = error
      const status = axios.isAxiosError(error) ? error.response?.status : undefined
      const retryable = status === undefined || status === 408 || status === 429 || status >= 500
      console.error(JSON.stringify({
        event: 'gateway.crm_post_failed', path, status: status || 'network',
        attempt: attempt + 1, retrying: retryable && attempt < policy.attempts - 1,
      }))
      if (!retryable || attempt === policy.attempts - 1) {
        const responseData = axios.isAxiosError(error) ? error.response?.data as any : undefined
        const detail = String(responseData?.detail || (error as any)?.message || 'Falló la comunicación con Django.').slice(0, 300)
        throw new Error(detail)
      }
      await new Promise(resolve => setTimeout(resolve, Math.min(8_000, 500 * 2 ** attempt)))
    }
  }
  throw lastError
}
