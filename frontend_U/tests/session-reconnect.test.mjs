import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

async function harness(refresh) {
  const sockets = [], revocations = [], cleanup = []
  const values = new Map([['token', 'synthetic-old']])
  globalThis.localStorage = { getItem: key => values.get(key) ?? null }
  globalThis.window = { location: { protocol: 'https:', host: 'qa.invalid' }, addEventListener() {}, removeEventListener() {} }
  globalThis.WebSocket = class {
    constructor() { sockets.push(this) }
    close() { void this.onclose?.({ code: 1000 }) }
  }
  globalThis.__securityHookMocks = {
    useEffect: effect => cleanup.push(effect()), useRef: current => ({ current }), useState: initial => [initial, () => {}],
    revokeBrowserSession: expected => revocations.push(expected),
    refreshAdminToken: async () => { const next = await refresh(); if (next) values.set('token', next); return next },
  }
  const source = await readFile(new URL('../src/admin/hooks/useCRMWebSocket.ts', import.meta.url), 'utf8')
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
    .replace(/import \{([^}]+)\} from ['"][^'"]+['"];?/g, 'const {$1} = globalThis.__securityHookMocks;')
  const module = await import('data:text/javascript;base64,' + Buffer.from(js + `\n// ${Math.random()}`).toString('base64'))
  module.useCRMWebSocket(() => {})
  return { sockets, revocations, values, close: () => cleanup.forEach(fn => fn?.()) }
}

test('expired socket renews successfully without discarding valid browser credentials', async () => {
  const h = await harness(() => 'synthetic-refreshed')
  try {
    await h.sockets[0].onclose({ code: 4401 })
    assert.equal(h.sockets.length, 2)
    assert.equal(h.revocations.length, 0)
    assert.equal(h.values.get('token'), 'synthetic-refreshed')
  } finally { h.close() }
})

test('revoked refresh stops reconnection and requests one session cleanup', async () => {
  const h = await harness(() => null)
  try {
    await h.sockets[0].onclose({ code: 4401 })
    assert.equal(h.sockets.length, 1)
    assert.equal(h.revocations.length, 1)
  } finally { h.close() }
})

test('a socket from before a new login cannot clear the current login', async () => {
  let refreshCalls = 0
  const h = await harness(() => { refreshCalls++; return null })
  try {
    h.values.set('token', 'synthetic-new-login')
    await h.sockets[0].onclose({ code: 4401 })
    assert.equal(h.sockets.length, 2)
    assert.equal(h.revocations.length, 0)
    assert.equal(refreshCalls, 0)
  } finally { h.close() }
})
