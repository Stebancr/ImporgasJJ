import { describe, expect, it, vi } from 'vitest'
import { IncomingMessageQueue } from './incoming-queue.js'

describe('incoming message queue', () => {
  it('bounds concurrency and handles live messages before waiting history', async () => {
    const queue = new IncomingMessageQueue(2)
    const started: string[] = []
    const releases: Array<() => void> = []
    const job = (name: string) => () => new Promise<void>(resolve => {
      started.push(name)
      releases.push(resolve)
    })

    queue.enqueueHistory(['history-1', 'history-2', 'history-3', 'history-4'], name => job(name)())
    queue.enqueueLive(job('live-1'))
    expect(started).toEqual(['history-1', 'history-2'])

    releases.shift()!()
    await vi.waitFor(() => expect(started).toEqual(['history-1', 'history-2', 'live-1']))
    releases.shift()!()
    await vi.waitFor(() => expect(started).toEqual(['history-1', 'history-2', 'live-1', 'history-3']))
    while (releases.length) releases.shift()!()
    await vi.waitFor(() => expect(started).toHaveLength(5))
    releases.shift()?.()
  })
})
