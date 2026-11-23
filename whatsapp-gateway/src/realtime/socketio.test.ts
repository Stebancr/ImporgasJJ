import crypto from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { env } from '../config/env.js'
import { verifyRealtimeToken, validateRealtimeToken, secureSocketIo } from './socketio.js'
import { vi, beforeEach } from 'vitest'
import { crmPost } from '../crm/client.js'
import { createServer } from 'node:http'
import { Server as SocketServer } from 'socket.io'

vi.mock('../crm/client.js', () => ({ crmPost: vi.fn() }))
const claims = () => ({ role: 'admin', token_type: 'gateway_realtime', user_id: 17,
  global_auth_version: 1, password_version: 0, session_id: 'synthetic-session',
  iat: Math.floor(Date.now() / 1000), exp: Math.floor(Date.now() / 1000) + 60 })

const token = (payload: object) => {
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url')
  const signature = crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN).update(encoded).digest('base64url')
  return `${encoded}.${signature}`
}

describe('admin realtime tokens', () => {
  it('accepts a current admin token', () => {
    expect(verifyRealtimeToken(token(claims()))).toBe(true)
  })

  it('rejects an expired token', () => {
    expect(verifyRealtimeToken(token({ role: 'admin', exp: Math.floor(Date.now() / 1000) - 1 }))).toBe(false)
  })

  it('rejects non-admin and tampered tokens', () => {
    expect(verifyRealtimeToken(token({ role: 'customer', exp: Math.floor(Date.now() / 1000) + 60 }))).toBe(false)
    expect(verifyRealtimeToken(`${token({ role: 'admin', exp: Math.floor(Date.now() / 1000) + 60 })}x`)).toBe(false)
  })
})

describe('versioned realtime authorization', () => {
  beforeEach(() => { vi.clearAllMocks(); vi.useRealTimers() })

  it('rejects legacy, wrong type, missing versions, and malformed signatures', () => {
    for (const missing of ['global_auth_version', 'password_version', 'user_id', 'session_id', 'iat']) {
      const payload: Record<string, unknown> = claims()
      delete payload[missing]
      expect(verifyRealtimeToken(token(payload))).toBe(false)
    }
    expect(verifyRealtimeToken(token({ ...claims(), token_type: 'access' }))).toBe(false)
    expect(verifyRealtimeToken(token(claims()) + '.extra')).toBe(false)
    expect(verifyRealtimeToken('abc.' + 'é'.repeat(43))).toBe(false)
  })

  it('requires backend approval on every validation and fails closed', async () => {
    vi.mocked(crmPost).mockResolvedValueOnce({ valid: true }).mockResolvedValueOnce({ valid: false }).mockRejectedValueOnce(new Error('offline'))
    const credential = token(claims())
    expect(await validateRealtimeToken(credential)).toBe(true)
    expect(await validateRealtimeToken(credential)).toBe(false)
    expect(await validateRealtimeToken(credential)).toBe(false)
    expect(crmPost).toHaveBeenCalledTimes(3)
  })

  it('disconnects multiple open tabs after revocation, clearing timers', async () => {
    vi.useFakeTimers()
    const handlers: Record<string, any> = {}
    const io = { use: vi.fn(), on: vi.fn((name, fn) => { handlers[name] = fn }) }
    secureSocketIo(io as any)
    vi.mocked(crmPost).mockResolvedValue({ valid: false })
    const tabs = [1, 2].map(() => {
      let close: () => void = () => {}
      const socket = { connected: true, handshake: { auth: { token: token(claims()) } },
        emit: vi.fn(), once: vi.fn((_name, fn) => { close = fn }),
        disconnect: vi.fn(() => { close() }) }
      handlers.connection(socket)
      return socket
    })
    await vi.advanceTimersByTimeAsync(2100)
    tabs.forEach(socket => { expect(socket.disconnect).toHaveBeenCalledWith(true); expect(socket.emit).toHaveBeenCalledWith('auth.revalidate') })
    expect(vi.getTimerCount()).toBe(0)
    vi.useRealTimers()
  })

  it('performs real polling handshakes and closes connected tabs after backend revocation', async () => {
    const http = createServer()
    const io = new SocketServer(http)
    secureSocketIo(io)
    vi.mocked(crmPost).mockResolvedValue({ valid: true })
    await new Promise<void>(resolve => http.listen(0, '127.0.0.1', resolve))
    const address = http.address() as { port: number }
    const base = `http://127.0.0.1:${address.port}/socket.io/?EIO=4&transport=polling`
    try {
      const tabs: string[] = []
      for (let index = 0; index < 2; index += 1) {
        const opening = await (await fetch(base)).text()
        const sid = JSON.parse(opening.slice(1)).sid
        const url = `${base}&sid=${encodeURIComponent(sid)}`
        await fetch(url, { method: 'POST', body: '40' + JSON.stringify({ token: token(claims()) }) })
        const accepted = await (await fetch(url)).text()
        expect(accepted.startsWith('40')).toBe(true)
        tabs.push(url)
      }
      const next = tabs.map(async url => (await fetch(url)).text())
      vi.mocked(crmPost).mockResolvedValue({ valid: false })
      for (const packet of await Promise.all(next)) expect(packet).toContain('auth.revalidate')
      // A fresh transport cannot reconnect using the same revoked credential.
      const opening = await (await fetch(base)).text()
      const url = `${base}&sid=${encodeURIComponent(JSON.parse(opening.slice(1)).sid)}`
      await fetch(url, { method: 'POST', body: '40' + JSON.stringify({ token: token(claims()) }) })
      expect(await (await fetch(url)).text()).toContain('unauthorized')
    } finally {
      await new Promise<void>(resolve => io.close(() => resolve()))
      http.closeAllConnections()
    }
  }, 10_000)
})
