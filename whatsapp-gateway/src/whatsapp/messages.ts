import type { WAMessage, WASocket } from '@whiskeysockets/baileys'
import { crmPost } from '../crm/client.js'
import { forwardMedia } from './media.js'

function unwrap(content: any): any {
  return content?.ephemeralMessage?.message
    || content?.viewOnceMessage?.message
    || content?.viewOnceMessageV2?.message
    || content
}

function messageDetails(content: any) {
  const value = unwrap(content)
  if (value?.conversation) return { type: 'text', text: value.conversation }
  if (value?.extendedTextMessage) return { type: 'text', text: value.extendedTextMessage.text || '', context: value.extendedTextMessage.contextInfo }
  if (value?.imageMessage) return { type: 'image', text: value.imageMessage.caption || '', media: value.imageMessage, context: value.imageMessage.contextInfo }
  if (value?.audioMessage) return { type: 'audio', text: '', media: value.audioMessage, context: value.audioMessage.contextInfo }
  if (value?.videoMessage) return { type: 'video', text: value.videoMessage.caption || '', media: value.videoMessage, context: value.videoMessage.contextInfo }
  if (value?.documentMessage) return { type: 'document', text: value.documentMessage.caption || '', media: value.documentMessage, context: value.documentMessage.contextInfo }
  if (value?.stickerMessage) return { type: 'sticker', text: '', media: value.stickerMessage, context: value.stickerMessage.contextInfo }
  const interactive = value?.buttonsResponseMessage?.selectedDisplayText || value?.listResponseMessage?.title || value?.templateButtonReplyMessage?.selectedDisplayText
  if (interactive) return { type: 'interactive', text: interactive }
  return null
}

export function normalizeUserJid(value: unknown): string | null {
  const raw = String(value || '').trim().toLowerCase()
  const match = raw.match(/^(\d{8,30})(?::\d+)?@(s\.whatsapp\.net|lid)$/)
  if (!match) return null
  if (match[2] === 's.whatsapp.net' && match[1]!.length > 15) return null
  return `${match[1]}@${match[2]}`
}

export function maskJid(value: unknown): string {
  const normalized = normalizeUserJid(value)
  if (!normalized) return 'invalid'
  const [identifier, server] = normalized.split('@')
  return `***${identifier!.slice(-4)}@${server}`
}

type PhoneJidResolver = (lid: string) => Promise<string | null>
type MessageEventSource = 'notify' | 'append' | 'history'
type ProcessingOptions = {
  eventSource?: MessageEventSource
  crmClientMessageId?: (externalMessageId: string) => string | undefined
}

const inFlight = new Set<string>()

export async function processIncoming(
  connectionId: string,
  message: WAMessage,
  resolvePhoneJid?: PhoneJidResolver,
  options: ProcessingOptions = {},
): Promise<string> {
  if (!message.message) return 'ignored_empty'
  const messageId = String(message.key.id || '').trim()
  if (!messageId) return 'ignored_message_id'
  const sourceJid = String(message.key.remoteJid || '')
  const normalizedSource = normalizeUserJid(sourceJid)
  if (!normalizedSource) return 'ignored_jid'

  const eventKey = `${connectionId}:${messageId}`
  if (inFlight.has(eventKey)) return 'ignored_in_flight_duplicate'
  inFlight.add(eventKey)
  try {
    const alternateCandidates = [message.key.remoteJidAlt, message.key.participantAlt]
      .map(normalizeUserJid)
      .filter((value): value is string => Boolean(value))
    let resolvedPhone = ''
    if (normalizedSource.endsWith('@lid') && resolvePhoneJid) {
      resolvedPhone = normalizeUserJid(await resolvePhoneJid(normalizedSource)) || ''
    }
    const phoneJid = [...alternateCandidates, resolvedPhone]
      .find(value => value.endsWith('@s.whatsapp.net')) || ''
    const remoteJid = phoneJid || normalizedSource
    const aliases = [...new Set([normalizedSource, ...alternateCandidates, resolvedPhone].filter(Boolean))]
    const details = messageDetails(message.message)
    if (!details) return 'ignored_type'

    let media: { media_id: string; url: string } | undefined
    let mediaError = ''
    if (details.media) {
      try {
        media = await forwardMedia(
          connectionId, message, details.media.mimetype || 'application/octet-stream',
          details.media.fileName || `${details.type}-${messageId}`,
        )
      } catch (error: any) {
        mediaError = String(error?.message || 'No fue posible descargar el archivo.').slice(0, 200)
      }
    }

    const clientMessageId = message.key.fromMe ? options.crmClientMessageId?.(messageId) : undefined
    const origin = message.key.fromMe ? (clientMessageId ? 'crm' : 'mobile') : 'customer'
    const eventSource = options.eventSource || 'notify'
    const number = remoteJid.endsWith('@s.whatsapp.net') ? remoteJid.split('@')[0]! : ''
    await crmPost('/internal/whatsapp/webhook/', {
      connection_id: connectionId,
      idempotency_key: eventKey,
      remote_jid: remoteJid,
      reply_jid: normalizedSource,
      source_jid: sourceJid,
      jid_aliases: aliases,
      number,
      push_name: message.pushName || '',
      message_id: messageId,
      client_message_id: clientMessageId || '',
      timestamp: Number(message.messageTimestamp || Math.floor(Date.now() / 1000)),
      type: details.type,
      text: details.text,
      quoted_message_id: details.context?.stanzaId || '',
      origin,
      event_source: eventSource,
      is_group: false,
      media,
      media_error: mediaError,
    })
    return `processed_${origin}_${eventSource}`
  } finally {
    inFlight.delete(eventKey)
  }
}

export async function sendOutbound(sock: WASocket, payload: any, messageId?: string) {
  const rawDestination = String(payload.to || '').trim()
  const jid = rawDestination.includes('@')
    ? normalizeUserJid(rawDestination)
    : normalizeUserJid(`${rawDestination.replace(/\D/g, '')}@s.whatsapp.net`)
  if (!jid) throw new Error(rawDestination.includes('@') ? 'JID de destino inválido.' : 'Número de destino inválido.')

  const options: any = { ...(messageId ? { messageId } : {}) }
  if (payload.reply_to) options.quoted = { key: { remoteJid: jid, id: payload.reply_to } }
  const sendOptions = Object.keys(options).length ? options : undefined
  const type = String(payload.type || 'text')
  if (type === 'text') return sock.sendMessage(jid, { text: String(payload.text || '') }, sendOptions)
  const mediaUrl = new URL(String(payload.url || ''))
  const crmOrigin = new URL(process.env.CRM_API_URL!).origin
  if (mediaUrl.origin !== crmOrigin) throw new Error('La URL multimedia no pertenece al CRM.')
  const content: any = { [type === 'document' ? 'document' : type]: { url: mediaUrl.toString() } }
  if (payload.text && ['image', 'video', 'document'].includes(type)) content.caption = String(payload.text)
  if (type === 'document') {
    content.fileName = String(payload.file_name || 'archivo')
    content.mimetype = String(payload.mime_type || 'application/octet-stream')
  }
  return sock.sendMessage(jid, content, sendOptions)
}
