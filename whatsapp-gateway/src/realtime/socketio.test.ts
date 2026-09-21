import crypto from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { env } from '../config/env.js'
import { verifyRealtimeToken } from './socketio.js'

const token = (payload: object) => {
  const encoded = Buffer.from(JSON.stringify(payload)).toString('base64url')
  const signature = crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN).update(encoded).digest('base64url')
  return `${encoded}.${signature}`
}

describe('admin realtime tokens', () => {
  it('accepts a current admin token', () => {
    expect(verifyRealtimeToken(token({ role: 'admin', exp: Math.floor(Date.now() / 1000) + 60 }))).toBe(true)
  })

  it('rejects an expired token', () => {
    expect(verifyRealtimeToken(token({ role: 'admin', exp: Math.floor(Date.now() / 1000) - 1 }))).toBe(false)
  })

  it('rejects non-admin and tampered tokens', () => {
    expect(verifyRealtimeToken(token({ role: 'customer', exp: Math.floor(Date.now() / 1000) + 60 }))).toBe(false)
    expect(verifyRealtimeToken(`${token({ role: 'admin', exp: Math.floor(Date.now() / 1000) + 60 })}x`)).toBe(false)
  })
})
