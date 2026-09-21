import { Router } from 'express'
import rateLimit from 'express-rate-limit'
import { z } from 'zod'
import { env } from '../config/env.js'
import { requireInternalAuth } from './middleware.js'
import { connectionManager } from '../whatsapp/connection.js'

export const routes = Router()
routes.get('/health', (_req, res) => res.json({ ok: true, status: connectionManager.state.status }))
routes.use('/internal', requireInternalAuth, rateLimit({ windowMs: 60_000, limit: 60, standardHeaders: true, legacyHeaders: false }))
routes.get('/internal/whatsapp/status/', (_req, res) => res.json({ ...connectionManager.state, qr_data_url: undefined }))
routes.post('/internal/whatsapp/connect/', async (req, res) => {
  if (req.body?.connection_id !== env.WHATSAPP_CONNECTION_ID) return res.status(404).json({ detail: 'Conexión desconocida.' })
  await connectionManager.connect(Boolean(req.body?.force_qr))
  return res.status(202).json({ status: connectionManager.state.status })
})
routes.post('/internal/whatsapp/logout/', async (req, res) => {
  if (req.body?.connection_id !== env.WHATSAPP_CONNECTION_ID) return res.status(404).json({ detail: 'Conexión desconocida.' })
  await connectionManager.logout()
  return res.json({ status: 'logged_out' })
})
routes.post('/internal/whatsapp/send/', async (req, res) => {
  try {
    const payload = z.object({
      connection_id: z.string(), to: z.string(), type: z.enum(['text','image','audio','video','document']),
      text: z.string().optional(), url: z.string().url().optional(), file_name: z.string().optional(),
      mime_type: z.string().optional(), reply_to: z.string().optional(), client_message_id: z.string().uuid(),
    }).parse(req.body)
    if (payload.type === 'text' && !payload.text?.trim()) throw new Error('El texto está vacío.')
    if (payload.type !== 'text' && !payload.url) throw new Error('El archivo requiere una URL interna.')
    return res.json(await connectionManager.send(payload))
  } catch (error: any) { return res.status(400).json({ detail: String(error?.message || error).slice(0, 300) }) }
})
