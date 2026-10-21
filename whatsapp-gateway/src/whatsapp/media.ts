import { mkdir, writeFile, unlink } from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import { downloadMediaMessage, type WAMessage } from '@whiskeysockets/baileys'
import { env } from '../config/env.js'
import { crmPost } from '../crm/client.js'

export async function forwardMedia(connectionId: string, message: WAMessage, mimeType: string, fileName: string) {
  const stream = await downloadMediaMessage(message, 'stream', {})
  const chunks: Buffer[] = []
  let size = 0
  const timer = setTimeout(() => stream.destroy(new Error('Tiempo de descarga excedido.')), 60_000)
  try {
    for await (const chunk of stream) {
      const buffer = Buffer.from(chunk)
      size += buffer.length
      if (size > env.WHATSAPP_MAX_MEDIA_BYTES) throw new Error('Archivo demasiado grande.')
      chunks.push(buffer)
    }
  } finally { clearTimeout(timer); stream.destroy() }
  if (!size) throw new Error('Archivo vacío.')
  const data = Buffer.concat(chunks, size)
  await mkdir(env.WHATSAPP_MEDIA_DIR, { recursive: true, mode: 0o700 })
  const mediaKey = crypto.createHash('sha256').update(`${connectionId}:${message.key.remoteJid}:${message.key.id}`).digest('hex')
  const temporary = path.join(env.WHATSAPP_MEDIA_DIR, `${mediaKey}.tmp`)
  await writeFile(temporary, data, { mode: 0o600 })
  const result = await crmPost<{ media_id: string; url: string }>('/internal/whatsapp/media/', {
      connection_id: connectionId,
      mime_type: mimeType,
      file_name: path.basename(fileName || 'archivo'),
      media_key: mediaKey,
      data_base64: data.toString('base64'),
  })
  // Keep the local copy if CRM persistence fails; never delete an unconfirmed upload.
  await unlink(temporary).catch(() => undefined)
  return result
}
