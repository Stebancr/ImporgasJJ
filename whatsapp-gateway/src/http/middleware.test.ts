import { beforeEach, describe, expect, it, vi } from 'vitest'
import { requireInternalAuth, signatureFor } from './middleware.js'
import { env } from '../config/env.js'

const request = (requestId: string, body: object, timestamp = String(Math.floor(Date.now() / 1000))) => {
  const raw = JSON.stringify(body)
  const headers: Record<string, string> = {
    authorization: `Bearer ${env.CRM_INTERNAL_SERVICE_TOKEN}`,
    'x-whatsapp-gateway-timestamp': timestamp,
    'x-whatsapp-gateway-request-id': requestId,
    'x-whatsapp-gateway-signature': signatureFor(timestamp, requestId, raw),
  }
  return { body, header: (name: string) => headers[name.toLowerCase()] } as any
}

const response = () => {
  const json = vi.fn()
  const status = vi.fn(() => ({ json }))
  return { value: { status, json } as any, status, json }
}

describe('internal HMAC middleware', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('accepts a valid signed request', () => {
    const res = response()
    const next = vi.fn()
    requireInternalAuth(request(`valid-${Date.now()}`, { connection_id: 'primary' }), res.value, next)
    expect(next).toHaveBeenCalledOnce()
    expect(res.status).not.toHaveBeenCalled()
  })

  it('rejects a bad signature', () => {
    const req = request(`bad-${Date.now()}`, {})
    req.header = (name: string) => name.toLowerCase() === 'x-whatsapp-gateway-signature' ? '0'.repeat(64) : request('unused', {}).header(name)
    const res = response()
    requireInternalAuth(req, res.value, vi.fn())
    expect(res.status).toHaveBeenCalledWith(401)
  })

  it('rejects an expired timestamp', () => {
    const res = response()
    requireInternalAuth(request(`old-${Date.now()}`, {}, String(Math.floor(Date.now() / 1000) - 301)), res.value, vi.fn())
    expect(res.status).toHaveBeenCalledWith(401)
  })

  it('rejects replayed request IDs', () => {
    const id = `replay-${Date.now()}`
    requireInternalAuth(request(id, {}), response().value, vi.fn())
    const res = response()
    requireInternalAuth(request(id, {}), res.value, vi.fn())
    expect(res.status).toHaveBeenCalledWith(401)
  })
})
