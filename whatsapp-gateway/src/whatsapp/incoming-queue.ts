type IncomingJob = () => Promise<void>

// A history sync can contain thousands of messages. Keep only a small number
// of requests in flight and let new messages pass queued history.
export class IncomingMessageQueue {
  private active = 0
  private readonly live: IncomingJob[] = []
  private readonly historyBatches: Array<() => IncomingJob | undefined> = []

  constructor(private readonly concurrency = 4) {
    if (!Number.isInteger(concurrency) || concurrency < 1) {
      throw new Error('Incoming message concurrency must be positive')
    }
  }

  enqueueLive(job: IncomingJob): void {
    this.live.push(job)
    this.drain()
  }

  enqueueHistory<T>(messages: readonly T[], handler: (message: T) => Promise<void>): void {
    let index = 0
    // Retain one batch rather than creating a promise and closure for every
    // message in a potentially large history sync.
    this.historyBatches.push(() => index < messages.length ? () => handler(messages[index++]!) : undefined)
    this.drain()
  }

  private next(): IncomingJob | undefined {
    const live = this.live.shift()
    if (live) return live
    while (this.historyBatches.length) {
      const history = this.historyBatches[0]!()
      if (history) return history
      this.historyBatches.shift()
    }
    return undefined
  }

  private drain(): void {
    while (this.active < this.concurrency) {
      const job = this.next()
      if (!job) return
      this.active += 1
      // Each job handles and logs its own failure, so one bad message cannot
      // stop the rest of the queue.
      void job().catch(error => {
        console.error(JSON.stringify({ event: 'gateway.incoming_queue_failed', error: String(error).slice(0, 300) }))
      }).finally(() => {
        this.active -= 1
        this.drain()
      })
    }
  }
}
