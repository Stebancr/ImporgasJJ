import crypto from 'node:crypto'
import type { Server } from 'socket.io'
import { env } from '../config/env.js'
import { crmPost } from '../crm/client.js'

export function verifyRealtimeToken(token: string): boolean {
  const parts = String(token || '').split('.')
  if (parts.length !== 2) return false
  const [encoded, signature] = parts
  if (!encoded || !signature) return false
  if (encoded.length > 8192 || !/^[A-Za-z0-9_-]+$/.test(encoded) || !/^[A-Za-z0-9_-]{43}$/.test(signature)) return false
  const expected = crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN).update(encoded).digest('base64url')
  if (signature.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return false
  try {
    const payload = JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8'))
    return payload.role === 'admin' && payload.token_type === 'gateway_realtime'
      && Number.isInteger(payload.user_id) && Number.isInteger(payload.global_auth_version)
      && Number.isInteger(payload.password_version) && typeof payload.session_id === 'string'
      && Number.isInteger(payload.iat) && payload.iat * 1000 <= Date.now()
      && Number.isInteger(payload.exp) && payload.exp * 1000 > Date.now()
      && payload.exp > payload.iat && payload.exp - payload.iat <= 120
  } catch { return false }
}

export async function validateRealtimeToken(token: string): Promise<boolean> {
  if (!verifyRealtimeToken(token)) return false
  try {
    const result = await crmPost<{ valid: boolean }>('/internal/whatsapp/realtime/validate/', { token }, { attempts: 1, timeout: 2000 })
    return result.valid === true
  } catch { return false }
}

export function secureSocketIo(io: Server): void {
  io.use(async (socket, next) => {
    if (await validateRealtimeToken(socket.handshake.auth?.token)) return next()
    console.warn(JSON.stringify({
      event: 'gateway.realtime_rejected',
      transport: socket.conn.transport.name,
      reason: 'invalid_or_expired_token',
    }))
    return next(new Error('unauthorized'))
  })
  io.on('connection', socket => {
    let checking = false
    const timer = setInterval(async () => {
      if (checking || !socket.connected) return
      checking = true
      try {
        if (!await validateRealtimeToken(socket.handshake.auth?.token)) {
          socket.emit('auth.revalidate')
          socket.disconnect(true)
        }
      } finally { checking = false }
    }, 2000)
    timer.unref()
    socket.once('disconnect', () => clearInterval(timer))
  })
}
