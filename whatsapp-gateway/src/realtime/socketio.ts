import crypto from 'node:crypto'
import type { Server } from 'socket.io'
import { env } from '../config/env.js'

export function verifyRealtimeToken(token: string): boolean {
  const [encoded, signature] = String(token || '').split('.')
  if (!encoded || !signature) return false
  const expected = crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN).update(encoded).digest('base64url')
  if (signature.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return false
  try {
    const payload = JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8'))
    return payload.role === 'admin' && Number(payload.exp) * 1000 > Date.now()
  } catch { return false }
}

export function secureSocketIo(io: Server): void {
  io.use((socket, next) => {
    if (verifyRealtimeToken(socket.handshake.auth?.token)) return next()
    console.warn(JSON.stringify({
      event: 'gateway.realtime_rejected',
      transport: socket.conn.transport.name,
      reason: 'invalid_or_expired_token',
    }))
    return next(new Error('unauthorized'))
  })
}
