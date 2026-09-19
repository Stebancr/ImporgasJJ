import crypto from 'node:crypto'
import type { NextFunction, Request, Response } from 'express'
import { env } from '../config/env.js'

const seen = new Map<string, number>()

export function signatureFor(timestamp: string, requestId: string, rawBody: string): string {
  return crypto.createHmac('sha256', env.CRM_INTERNAL_SERVICE_TOKEN)
    .update(`${timestamp}.${requestId}.${rawBody}`).digest('hex')
}

export function requireInternalAuth(req: Request, res: Response, next: NextFunction): void {
  const bearer = req.header('authorization') || ''
  const timestamp = req.header('x-whatsapp-gateway-timestamp') || ''
  const requestId = req.header('x-whatsapp-gateway-request-id') || ''
  const signature = req.header('x-whatsapp-gateway-signature') || ''
  const expectedBearer = `Bearer ${env.CRM_INTERNAL_SERVICE_TOKEN}`
  const body = JSON.stringify(req.body ?? {})
  const expected = signatureFor(timestamp, requestId, body)
  const maxAgeMs = env.WHATSAPP_GATEWAY_REQUEST_MAX_AGE * 1000
  const recent = Math.abs(Date.now() - Number(timestamp) * 1000) <= maxAgeMs
  const duplicate = seen.has(requestId)
  const valid = bearer.length === expectedBearer.length
    && crypto.timingSafeEqual(Buffer.from(bearer), Buffer.from(expectedBearer))
    && signature.length === expected.length
    && crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))
  if (!requestId || !recent || duplicate || !valid) {
    res.status(401).json({ detail: 'Autenticación interna inválida.' })
    return
  }
  seen.set(requestId, Date.now())
  for (const [key, time] of seen) if (Date.now() - time > maxAgeMs) seen.delete(key)
  next()
}
