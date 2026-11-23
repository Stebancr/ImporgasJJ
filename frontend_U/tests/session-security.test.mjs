import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

test('global logout clears both identities once and notifies every realtime owner', async () => {
  const listeners = new Map()
  const events = []
  const storage = () => {
    const data = new Map()
    return { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) }
  }
  globalThis.localStorage = storage()
  globalThis.sessionStorage = storage()
  globalThis.window = {
    addEventListener: (name, fn) => listeners.set(name, fn),
    dispatchEvent: event => events.push(event.type),
  }
  const source = await readFile(new URL('../src/services/sessionSecurity.ts', import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
  const module = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'))
  for (const key of ['authToken', 'refreshToken', 'user', 'token', 'refresh', 'adminUser']) localStorage.setItem(key, 'synthetic')
  module.revokeBrowserSession()
  module.revokeBrowserSession()
  assert.equal(events.filter(x => x === 'auth:logout').length, 1)
  assert.equal(events.filter(x => x === 'admin:logout').length, 1)
  assert.equal(events.filter(x => x === 'session:revoked').length, 1)
  assert.equal(localStorage.getItem('token'), null)
  assert.equal(localStorage.getItem('refreshToken'), null)
  assert.equal(sessionStorage.getItem('auth:revoked'), '1')
  listeners.get('storage')({ key: 'auth:revocation' })
  assert.equal(events.length, 3)
  const signed = claims => 'synthetic.' + Buffer.from(JSON.stringify(claims)).toString('base64url') + '.signature'
  const claims = { session_id: 'one', user_id: 17, global_auth_version: 1, password_version: 0, exp: 1 }
  const before = signed(claims), refreshed = signed({ ...claims, exp: 2 })
  assert.equal(module.isSameBrowserSession(before, refreshed), true)
  assert.equal(module.isSameBrowserSession(before, signed({ ...claims, session_id: 'new-login' })), false)
  assert.equal(module.isSameBrowserSession(before, signed({ ...claims, global_auth_version: 2 })), false)
  assert.equal(module.isSameBrowserSession(before, signed({ ...claims, password_version: 1 })), false)
  assert.equal(module.isSameBrowserSession('malformed', refreshed), false)
  sessionStorage.removeItem('auth:revoked')
  localStorage.setItem('token', 'new-synthetic-session')
  module.revokeBrowserSession({ key: 'token', value: 'old-synthetic-session' })
  assert.equal(localStorage.getItem('token'), 'new-synthetic-session')
  assert.equal(events.length, 3)
})
