import { rm } from 'node:fs/promises'
import { beforeEach, describe, expect, it } from 'vitest'
import { env } from '../config/env.js'
import { loadOutboundResults, saveOutboundResults } from './outbound-state.js'

describe('durable outbound idempotency', () => {
  beforeEach(async () => {
    await rm(`${env.WHATSAPP_AUTH_DIR}/outbound-${env.WHATSAPP_CONNECTION_ID}.json`, { force: true })
  })

  it('reloads a sent result from the authentication volume', async () => {
    await saveOutboundResults(new Map([[
      '99114326-37d2-5dc3-9cbb-24b76f224f0c',
      { external_message_id: 'wa-message-1', status: 'sent' },
    ]]))
    const restored = await loadOutboundResults()
    expect(restored.get('99114326-37d2-5dc3-9cbb-24b76f224f0c')).toEqual({
      external_message_id: 'wa-message-1', status: 'sent',
    })
  })
})
