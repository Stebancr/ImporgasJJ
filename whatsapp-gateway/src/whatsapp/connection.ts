import { EventEmitter } from 'node:events'
import { Boom } from '@hapi/boom'
import makeWASocket, { Browsers, DisconnectReason, makeCacheableSignalKeyStore } from '@whiskeysockets/baileys'
import pino from 'pino'
import QRCode from 'qrcode'
import { env } from '../config/env.js'
import { crmPost } from '../crm/client.js'
import { clearAuthState, loadAuthState } from './auth-state.js'
import { maskJid, processIncoming, sendOutbound } from './messages.js'
import { loadOutboundResults, saveOutboundResults } from './outbound-state.js'

export type GatewayStatus = 'disconnected'|'waiting_for_qr'|'qr_ready'|'connecting'|'connected'|'logged_out'|'reconnecting'|'error'
export type State = { connection_id:string; status:GatewayStatus; qr_data_url?:string; qr_expires_at?:string; phone_number?:string; last_connected_at?:string; last_error?:string }

export class ConnectionManager extends EventEmitter {
  private socket: ReturnType<typeof makeWASocket> | null = null
  private connecting: Promise<void> | null = null
  private retry = 0
  private qrTimer?: NodeJS.Timeout
  private outbound: Map<string, { external_message_id:string; status:string }> | null = null
  private outboundByExternal = new Map<string, string>()
  private allowReconnect = true
  private crmSyncTimers = new Set<NodeJS.Timeout>()
  state: State = { connection_id: env.WHATSAPP_CONNECTION_ID, status: 'disconnected' }

  private publish(patch: Partial<State>) {
    this.state = { ...this.state, ...patch }
    this.emit('state', this.state)
    const payload = { ...this.state, qr_data_url: undefined }
    void crmPost('/internal/whatsapp/status/', payload).catch(() => {
      // Django puede estar reiniciándose mientras Baileys ya conserva la
      // sesión. Reintentar el último estado evita que el gateway quede
      // conectado, pero la integración permanezca inactiva en el CRM.
      const retry = (attempt: number) => {
        const timer = setTimeout(() => {
          this.crmSyncTimers.delete(timer)
          // El estado puede haber cambiado mientras Django arrancaba. Enviar
          // siempre el valor actual evita que un reintento antiguo (por
          // ejemplo, "connecting") sobrescriba una conexión ya abierta.
          const currentPayload = { ...this.state, qr_data_url: undefined }
          void crmPost('/internal/whatsapp/status/', currentPayload).catch(() => {
            if (attempt < 5) retry(attempt + 1)
          })
        }, Math.min(30_000, 1000 * 2 ** attempt))
        this.crmSyncTimers.add(timer)
      }
      retry(0)
    })
  }

  private async ensureOutboundState() {
    if (!this.outbound) this.outbound = await loadOutboundResults()
    this.outboundByExternal.clear()
    for (const [clientMessageId, result] of this.outbound) {
      if (result.external_message_id) this.outboundByExternal.set(result.external_message_id, clientMessageId)
    }
  }

  private crmClientMessageId(externalMessageId: string): string | undefined {
    return this.outboundByExternal.get(externalMessageId)
  }

  async connect(forceQr = false): Promise<void> {
    if (this.connecting) return this.connecting
    this.connecting = this.open(forceQr).finally(() => { this.connecting = null })
    return this.connecting
  }

  private async open(forceQr: boolean): Promise<void> {
    this.allowReconnect = true
    if (forceQr) await clearAuthState(env.WHATSAPP_CONNECTION_ID)
    const previous = this.socket
    this.socket = null
    previous?.end(undefined)
    this.publish({ status: 'connecting', last_error: '', qr_data_url: undefined, qr_expires_at: undefined })
    const { state, saveCreds } = await loadAuthState(env.WHATSAPP_CONNECTION_ID)
    const logger = pino({ level: 'silent' })
    const sock = makeWASocket({
      auth: { creds: state.creds, keys: makeCacheableSignalKeyStore(state.keys, logger) },
      logger,
      browser: Browsers.ubuntu('IMPORGAS CRM'),
      markOnlineOnConnect: false,
      syncFullHistory: false,
      generateHighQualityLinkPreview: false,
    })
    this.socket = sock
    sock.ev.on('creds.update', saveCreds)
    await this.ensureOutboundState()
    sock.ev.on('messages.upsert', ({ messages, type }) => {
      const resolvePhoneJid = (jid: string) => sock.signalRepository.lidMapping.getPNForLID(jid)
      for (const message of messages) {
        const eventSource = type === 'notify' ? 'notify' : 'append'
        console.log(JSON.stringify({
          event: 'gateway.baileys_message', source: eventSource,
          jid: maskJid(message.key.remoteJid), external_message_id: message.key.id || '-',
          from_me: Boolean(message.key.fromMe),
        }))
        void processIncoming(env.WHATSAPP_CONNECTION_ID, message, resolvePhoneJid, {
          eventSource,
          crmClientMessageId: id => this.crmClientMessageId(id),
        })
          .then(result => console.log(JSON.stringify({ event: 'gateway.message', result, external_message_id: message.key.id || '-' })))
          .catch(error => {
            const safeError = String(error?.message || error).slice(0, 300)
            console.error(JSON.stringify({ event: 'gateway.message_failed', external_message_id: message.key.id || '-', error: safeError }))
            this.publish({ last_error: safeError })
          })
      }
    })
    sock.ev.on('messaging-history.set', ({ messages }) => {
      console.log(JSON.stringify({ event: 'gateway.history_received', messages: messages.length }))
      const resolvePhoneJid = (jid: string) => sock.signalRepository.lidMapping.getPNForLID(jid)
      for (const message of messages) {
        void processIncoming(env.WHATSAPP_CONNECTION_ID, message, resolvePhoneJid, {
          eventSource: 'history',
          crmClientMessageId: id => this.crmClientMessageId(id),
        }).then(result => console.log(JSON.stringify({
          event: 'gateway.history_message', result, external_message_id: message.key.id || '-',
        }))).catch(error => console.error(JSON.stringify({
          event: 'gateway.history_failed', external_message_id: message.key.id || '-',
          error: String(error?.message || error).slice(0, 300),
        })))
      }
    })
    sock.ev.on('chats.upsert', chats => console.log(JSON.stringify({ event: 'gateway.chats_upsert', count: chats.length })))
    sock.ev.on('chats.update', chats => console.log(JSON.stringify({ event: 'gateway.chats_update', count: chats.length })))
    sock.ev.on('contacts.upsert', contacts => console.log(JSON.stringify({ event: 'gateway.contacts_upsert', count: contacts.length })))
    sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
      if (sock !== this.socket) return
      console.log(JSON.stringify({ event: 'gateway.connection_update', connection: connection || '-', qr: Boolean(qr) }))
      if (qr) {
        const qrData = await QRCode.toDataURL(qr, { errorCorrectionLevel: 'M', margin: 2, width: 320 })
        const expires = new Date(Date.now() + env.WHATSAPP_QR_TTL_SECONDS * 1000).toISOString()
        this.publish({ status: 'qr_ready', qr_data_url: qrData, qr_expires_at: expires })
        if (this.qrTimer) clearTimeout(this.qrTimer)
        this.qrTimer = setTimeout(() => this.publish({ status: 'waiting_for_qr', qr_data_url: undefined, qr_expires_at: undefined }), env.WHATSAPP_QR_TTL_SECONDS * 1000)
      } else if (connection === 'open') {
        this.retry = 0
        if (this.qrTimer) clearTimeout(this.qrTimer)
        const phone = String(sock.user?.id || '').split(':')[0]?.split('@')[0] || ''
        this.publish({ status: 'connected', phone_number: phone, last_connected_at: new Date().toISOString(), qr_data_url: undefined, qr_expires_at: undefined })
      } else if (connection === 'close') {
        if (!this.allowReconnect) return
        const statusCode = (lastDisconnect?.error as Boom | undefined)?.output?.statusCode
        if (statusCode === DisconnectReason.loggedOut || statusCode === DisconnectReason.badSession) {
          await clearAuthState(env.WHATSAPP_CONNECTION_ID)
          this.publish({ status: 'logged_out', phone_number: '', qr_data_url: undefined, last_error: 'WhatsApp cerró o invalidó la sesión.' })
          return
        }
        this.retry += 1
        if (this.retry > 8) { this.publish({ status: 'error', last_error: 'Se agotaron los intentos de reconexión.' }); return }
        this.publish({ status: 'reconnecting', last_error: 'Conexión temporalmente interrumpida.' })
        const delay = Math.min(60_000, 1000 * 2 ** (this.retry - 1))
        setTimeout(() => { if (this.allowReconnect) void this.connect() }, delay)
      }
    })
  }

  async logout(): Promise<void> {
    this.allowReconnect = false
    if (this.qrTimer) clearTimeout(this.qrTimer)
    const socket = this.socket
    this.socket = null
    if (socket) await socket.logout().catch(() => undefined)
    await clearAuthState(env.WHATSAPP_CONNECTION_ID)
    this.publish({ status: 'logged_out', phone_number: '', qr_data_url: undefined, qr_expires_at: undefined })
  }

  async send(payload: any) {
    if (payload.connection_id !== env.WHATSAPP_CONNECTION_ID) throw new Error('Conexión desconocida.')
    if (!this.socket || this.state.status !== 'connected') throw new Error('La sesión de WhatsApp Web no está conectada.')
    const key = String(payload.client_message_id || '')
    if (!key) throw new Error('client_message_id es obligatorio.')
    if (!this.outbound) await this.ensureOutboundState()
    if (this.outbound!.has(key)) return this.outbound!.get(key)
    const proposedExternalId = `CRM${key.replace(/-/g, '').slice(0, 29).toUpperCase()}`
    this.outboundByExternal.set(proposedExternalId, key)
    let sent
    try {
      sent = await sendOutbound(this.socket, payload, proposedExternalId)
    } catch (error) {
      this.outboundByExternal.delete(proposedExternalId)
      throw error
    }
    const externalMessageId = sent?.key?.id || proposedExternalId
    if (externalMessageId !== proposedExternalId) this.outboundByExternal.delete(proposedExternalId)
    this.outboundByExternal.set(externalMessageId, key)
    const result = { external_message_id: externalMessageId, status: 'sent' }
    this.outbound!.set(key, result)
    if (this.outbound!.size > 5000) this.outbound!.delete(this.outbound!.keys().next().value!)
    await saveOutboundResults(this.outbound!)
    console.log(JSON.stringify({ event: 'gateway.outbound_sent', external_message_id: externalMessageId, jid: maskJid(payload.to) }))
    return result
  }
}

export const connectionManager = new ConnectionManager()
