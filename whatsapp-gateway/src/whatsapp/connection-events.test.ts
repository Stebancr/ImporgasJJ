import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const handlers = new Map<string, (...args: any[]) => any>()
  const socket = {
    ev: { on: vi.fn((event: string, handler: (...args: any[]) => any) => handlers.set(event, handler)) },
    end: vi.fn(), logout: vi.fn().mockResolvedValue(undefined), user: { id: '573001112233:1@s.whatsapp.net' },
    profilePictureUrl: vi.fn().mockResolvedValue('https://cdn.example.test/avatar.jpg'),
    signalRepository: { lidMapping: { getPNForLID: vi.fn().mockResolvedValue(null) } },
  }
  return {
    handlers, socket, makeWASocket: vi.fn(() => socket), clearAuthState: vi.fn().mockResolvedValue(undefined),
    saveCreds: vi.fn().mockResolvedValue(undefined),
    crmPost: vi.fn().mockResolvedValue({}), toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,qr'),
    processIncoming: vi.fn().mockResolvedValue('processed'),
    sendOutbound: vi.fn(),
  }
})

vi.mock('@whiskeysockets/baileys', () => ({
  default: mocks.makeWASocket,
  Browsers: { ubuntu: () => ['IMPORGAS', 'Chrome', '1'] },
  DisconnectReason: { 401: 'loggedOut', 500: 'badSession', 515: 'restartRequired', loggedOut: 401, badSession: 500, restartRequired: 515 },
  makeCacheableSignalKeyStore: (keys: unknown) => keys,
}))
vi.mock('qrcode', () => ({ default: { toDataURL: mocks.toDataURL } }))
vi.mock('../crm/client.js', () => ({ crmPost: mocks.crmPost }))
vi.mock('./auth-state.js', () => ({
  loadAuthState: vi.fn().mockResolvedValue({ state: { creds: {}, keys: {} }, saveCreds: mocks.saveCreds }),
  clearAuthState: mocks.clearAuthState,
}))
vi.mock('./messages.js', () => ({
  processIncoming: mocks.processIncoming,
  sendOutbound: mocks.sendOutbound,
  maskJid: (value: string) => value,
}))

import { env } from '../config/env.js'
import { ConnectionManager } from './connection.js'

describe('Baileys connection events', () => {
  beforeEach(() => {
    mocks.handlers.clear()
    mocks.makeWASocket.mockClear()
    mocks.clearAuthState.mockClear()
    mocks.saveCreds.mockClear()
    mocks.crmPost.mockClear()
    mocks.processIncoming.mockClear()
    mocks.sendOutbound.mockReset()
    mocks.socket.logout.mockClear()
    mocks.socket.profilePictureUrl.mockClear()
  })
  afterEach(() => vi.useRealTimers())

  it('publishes a temporary QR and then marks it expired', async () => {
    vi.useFakeTimers()
    const manager = new ConnectionManager()
    await manager.connect()
    await mocks.handlers.get('connection.update')!({ qr: 'temporary-qr' })
    expect(manager.state).toMatchObject({ status: 'qr_ready', qr_data_url: 'data:image/png;base64,qr' })
    await vi.advanceTimersByTimeAsync(env.WHATSAPP_QR_TTL_SECONDS * 1000)
    expect(manager.state.status).toBe('waiting_for_qr')
    expect(manager.state.qr_data_url).toBeUndefined()
  })

  it('publishes the connected phone without exposing credentials', async () => {
    const manager = new ConnectionManager()
    await manager.connect()
    await mocks.handlers.get('connection.update')!({ connection: 'open' })
    expect(manager.state.status).toBe('connected')
    expect(manager.state.phone_number).toBe('573001112233')
    expect(JSON.stringify(manager.state)).not.toContain('creds')
  })

  it('processes phone echoes and history instead of discarding fromMe messages', async () => {
    const manager = new ConnectionManager()
    await manager.connect()
    const ownMessage = {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: true, id: 'own-1' },
      message: { conversation: 'Desde celular' },
    }
    mocks.handlers.get('messages.upsert')!({ messages: [ownMessage], type: 'notify' })
    mocks.handlers.get('messaging-history.set')!({ messages: [ownMessage] })
    await vi.waitFor(() => expect(mocks.processIncoming).toHaveBeenCalledTimes(2))
    expect(mocks.processIncoming.mock.calls[0]![3]).toMatchObject({ eventSource: 'notify' })
    expect(mocks.processIncoming.mock.calls[1]![3]).toMatchObject({ eventSource: 'history' })
  })

  it('enriches a live customer message with an available profile picture', async () => {
    const manager = new ConnectionManager()
    await manager.connect()
    const customerMessage = {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: false, id: 'customer-avatar-1' },
      message: { conversation: 'Hola' },
    }
    mocks.handlers.get('messages.upsert')!({ messages: [customerMessage], type: 'notify' })
    await vi.waitFor(() => expect(mocks.processIncoming).toHaveBeenCalledOnce())
    expect(mocks.socket.profilePictureUrl).toHaveBeenCalledWith('573001112233@s.whatsapp.net', 'image')
    expect(mocks.processIncoming.mock.calls[0]![3]).toMatchObject({
      eventSource: 'notify', profilePictureUrl: 'https://cdn.example.test/avatar.jpg',
    })
  })

  it('backs off after a temporary network failure', async () => {
    vi.useFakeTimers()
    const manager = new ConnectionManager()
    await manager.connect()
    const reconnect = vi.spyOn(manager, 'connect').mockResolvedValue(undefined)
    await mocks.handlers.get('connection.update')!({ connection: 'close', lastDisconnect: { error: { output: { statusCode: 408 } } } })
    expect(manager.state.status).toBe('reconnecting')
    await vi.advanceTimersByTimeAsync(1000)
    expect(reconnect).toHaveBeenCalledOnce()
  })

  it('coalesces simultaneous retries for the same outbound operation', async () => {
    const manager = new ConnectionManager()
    await manager.connect()
    await mocks.handlers.get('connection.update')!({ connection: 'open' })
    mocks.sendOutbound.mockResolvedValue({ key: { id: 'single-external-id' } })
    const payload = {
      connection_id: manager.state.connection_id,
      client_message_id: '245ed47a-5a37-4e42-91a2-6ff80f952256',
      to: '573001112233@s.whatsapp.net', type: 'text', text: 'Prueba controlada',
    }

    const [first, second] = await Promise.all([manager.send(payload), manager.send(payload)])

    expect(first).toEqual(second)
    expect(mocks.sendOutbound).toHaveBeenCalledOnce()
  })

  it('persists credential updates without logging their contents', async () => {
    const manager = new ConnectionManager()
    await manager.connect()
    await mocks.handlers.get('creds.update')!({ privateKey: 'must-not-be-logged' })
    expect(mocks.saveCreds).toHaveBeenCalledOnce()
  })

  it('reopens immediately when pairing requires a socket restart', async () => {
    vi.useFakeTimers()
    const manager = new ConnectionManager()
    await manager.connect()
    const reconnect = vi.spyOn(manager, 'connect').mockResolvedValue(undefined)
    await mocks.handlers.get('connection.update')!({ connection: 'close', lastDisconnect: { error: { output: { statusCode: 515 } } } })
    expect(manager.state.status).toBe('reconnecting')
    await vi.advanceTimersByTimeAsync(250)
    expect(reconnect).toHaveBeenCalledOnce()
  })

  it('preserves invalid sessions for diagnosis and manual logout does not reconnect', async () => {
    vi.useFakeTimers()
    const invalid = new ConnectionManager()
    await invalid.connect()
    await mocks.handlers.get('connection.update')!({ connection: 'close', lastDisconnect: { error: { output: { statusCode: 401 } } } })
    expect(invalid.state.status).toBe('logged_out')
    expect(mocks.clearAuthState).not.toHaveBeenCalled()

    mocks.handlers.clear()
    const manual = new ConnectionManager()
    await manual.connect()
    await manual.logout()
    expect(manual.state.status).toBe('logged_out')
    expect(mocks.socket.logout).toHaveBeenCalled()
    await vi.runAllTimersAsync()
    expect(manual.state.status).toBe('logged_out')
  })
})
