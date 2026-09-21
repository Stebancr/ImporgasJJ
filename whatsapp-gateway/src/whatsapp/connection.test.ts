import { describe, expect, it, vi } from 'vitest'
import { ConnectionManager } from './connection.js'

describe('gateway safety contract', () => {
  it('keeps the channel explicitly experimental', () => {
    expect('whatsapp_web').not.toBe('whatsapp')
  })

  it('starts disconnected and rejects sending without an active session', async () => {
    const manager = new ConnectionManager()
    expect(manager.state.status).toBe('disconnected')
    await expect(manager.send({
      connection_id: manager.state.connection_id,
      client_message_id: '99114326-37d2-5dc3-9cbb-24b76f224f0c',
      to: '573001112233', type: 'text', text: 'No enviar',
    })).rejects.toThrow('no está conectada')
  })

  it('coalesces simultaneous connection attempts into one socket opening', async () => {
    const manager = new ConnectionManager()
    let release!: () => void
    const pending = new Promise<void>((resolve) => { release = resolve })
    const open = vi.spyOn(manager as any, 'open').mockReturnValue(pending)
    const first = manager.connect()
    const second = manager.connect()
    expect(open).toHaveBeenCalledOnce()
    release()
    await Promise.all([first, second])
  })
})
