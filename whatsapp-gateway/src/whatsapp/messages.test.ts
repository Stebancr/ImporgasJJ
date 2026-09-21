import { beforeEach, describe, expect, it, vi } from 'vitest'

const { crmPost, forwardMedia } = vi.hoisted(() => ({ crmPost: vi.fn(), forwardMedia: vi.fn() }))
vi.mock('../crm/client.js', () => ({ crmPost }))
vi.mock('./media.js', () => ({ forwardMedia }))

import { processIncoming, sendOutbound } from './messages.js'

describe('WhatsApp message normalization', () => {
  beforeEach(() => {
    crmPost.mockReset().mockResolvedValue({})
    forwardMedia.mockReset()
  })

  it('forwards a direct incoming text with an idempotency key', async () => {
    await processIncoming('primary', {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: false, id: 'message-1' },
      message: { conversation: 'Hola' }, messageTimestamp: 123, pushName: 'Cliente',
    } as any)
    expect(crmPost).toHaveBeenCalledOnce()
    expect(crmPost.mock.calls[0]![1]).toMatchObject({
      idempotency_key: 'primary:message-1', text: 'Hola', number: '573001112233',
    })
  })

  it('synchronizes own phone messages and ignores group and broadcast messages', async () => {
    await processIncoming('primary', { key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: true, id: '1' }, message: { conversation: 'own' } } as any)
    await processIncoming('primary', { key: { remoteJid: '123@g.us', fromMe: false, id: '2' }, message: { conversation: 'group' } } as any)
    await processIncoming('primary', { key: { remoteJid: 'status@broadcast', fromMe: false, id: '3' }, message: { conversation: 'status' } } as any)
    expect(crmPost).toHaveBeenCalledOnce()
    expect(crmPost.mock.calls[0]![1]).toMatchObject({ origin: 'mobile', idempotency_key: 'primary:1' })
  })

  it('classifies the echo of a CRM message without creating a new logical message', async () => {
    await processIncoming('primary', {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: true, id: 'CRM-MESSAGE-1' },
      message: { conversation: 'Respuesta' },
    } as any, undefined, { crmClientMessageId: id => id === 'CRM-MESSAGE-1' ? 'client-1' : undefined })
    expect(crmPost.mock.calls[0]![1]).toMatchObject({
      origin: 'crm', client_message_id: 'client-1', message_id: 'CRM-MESSAGE-1',
    })
  })

  it('removes the device suffix and keeps the real WhatsApp message id stable', async () => {
    await processIncoming('primary', {
      key: { remoteJid: '573001112233:0@s.whatsapp.net', fromMe: false, id: 'stable-id' },
      message: { conversation: 'Hola' },
    } as any)
    expect(crmPost.mock.calls[0]![1]).toMatchObject({
      remote_jid: '573001112233@s.whatsapp.net',
      reply_jid: '573001112233@s.whatsapp.net',
      idempotency_key: 'primary:stable-id',
    })
  })

  it('coalesces concurrent retries of the same WhatsApp message', async () => {
    let release!: () => void
    crmPost.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve({}) }))
    const message = {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: false, id: 'concurrent-id' },
      message: { conversation: 'Rápido' },
    } as any
    const first = processIncoming('primary', message)
    const second = await processIncoming('primary', message)
    expect(second).toBe('ignored_in_flight_duplicate')
    release()
    await expect(first).resolves.toBe('processed_customer_notify')
    expect(crmPost).toHaveBeenCalledOnce()
  })

  it('maps a multi-device LID to its phone JID when Baileys provides the alternate address', async () => {
    await processIncoming('primary', {
      key: {
        remoteJid: '123456789012345@lid', remoteJidAlt: '573001112233@s.whatsapp.net',
        fromMe: false, id: 'lid-message-1',
      },
      message: { conversation: 'Mensaje LID' },
    } as any)
    expect(crmPost.mock.calls[0]![1]).toMatchObject({
      remote_jid: '573001112233@s.whatsapp.net', source_jid: '123456789012345@lid', number: '573001112233',
    })
  })

  it('uses the Baileys LID repository when the event has no alternate phone JID', async () => {
    const resolver = vi.fn().mockResolvedValue('573009998877@s.whatsapp.net')
    await processIncoming('primary', {
      key: { remoteJid: '123456789012345@lid', fromMe: false, id: 'lid-message-2' },
      message: { conversation: 'Mensaje resuelto' },
    } as any, resolver)
    expect(resolver).toHaveBeenCalledWith('123456789012345@lid')
    expect(crmPost.mock.calls[0]![1]).toMatchObject({ remote_jid: '573009998877@s.whatsapp.net' })
  })

  it('downloads media before forwarding the normalized event', async () => {
    forwardMedia.mockResolvedValue({ media_id: 'media-1', url: '' })
    await processIncoming('primary', {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: false, id: 'image-1' },
      message: { imageMessage: { caption: 'Foto', mimetype: 'image/jpeg' } },
    } as any)
    expect(forwardMedia).toHaveBeenCalledOnce()
    expect(crmPost.mock.calls[0]![1]).toMatchObject({ type: 'image', text: 'Foto', media: { media_id: 'media-1' } })
  })

  it.each([
    ['audio', { audioMessage: { mimetype: 'audio/ogg' } }],
    ['document', { documentMessage: { mimetype: 'application/pdf', fileName: 'factura.pdf' } }],
    ['video', { videoMessage: { mimetype: 'video/mp4', caption: 'Video' } }],
    ['sticker', { stickerMessage: { mimetype: 'image/webp' } }],
  ])('normalizes incoming %s media', async (expectedType, content) => {
    forwardMedia.mockResolvedValue({ media_id: `media-${expectedType}`, url: '' })
    await processIncoming('primary', {
      key: { remoteJid: '573001112233@s.whatsapp.net', fromMe: false, id: `message-${expectedType}` },
      message: content,
    } as any)
    expect(crmPost.mock.calls[0]![1]).toMatchObject({ type: expectedType, media: { media_id: `media-${expectedType}` } })
  })
})

describe('single-recipient outbound messages', () => {
  it('sends text to one normalized user JID', async () => {
    const sendMessage = vi.fn().mockResolvedValue({ key: { id: 'wa-1' } })
    await sendOutbound({ sendMessage } as any, { to: '+57 300 111 2233', type: 'text', text: 'Respuesta' })
    expect(sendMessage).toHaveBeenCalledWith('573001112233@s.whatsapp.net', { text: 'Respuesta' }, undefined)
  })

  it('can reply directly to a validated LID conversation', async () => {
    const sendMessage = vi.fn().mockResolvedValue({ key: { id: 'wa-lid-1' } })
    await sendOutbound({ sendMessage } as any, { to: '123456789012345@lid', type: 'text', text: 'Respuesta' })
    expect(sendMessage).toHaveBeenCalledWith('123456789012345@lid', { text: 'Respuesta' }, undefined)
  })

  it('normalizes a device-qualified destination before sending', async () => {
    const sendMessage = vi.fn().mockResolvedValue({ key: { id: 'wa-device-1' } })
    await sendOutbound({ sendMessage } as any, { to: '573001112233:4@s.whatsapp.net', type: 'text', text: 'Respuesta' })
    expect(sendMessage).toHaveBeenCalledWith('573001112233@s.whatsapp.net', { text: 'Respuesta' }, undefined)
  })

  it('rejects invalid destination numbers', async () => {
    await expect(sendOutbound({ sendMessage: vi.fn() } as any, { to: '123', type: 'text', text: 'x' })).rejects.toThrow('Número de destino inválido')
  })
})
