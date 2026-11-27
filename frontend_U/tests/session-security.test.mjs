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
    location: { origin: 'https://store.example.test' },
    addEventListener: (name, fn) => listeners.set(name, fn),
    dispatchEvent: event => events.push(event.type),
  }
  const source = await readFile(new URL('../src/services/sessionSecurity.ts', import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
  const module = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'))
  assert.equal(module.safeLoginReturn('/carrito?q=1#entrega'), '/carrito?q=1#entrega')
  assert.equal(module.safeLoginReturn('/admin/productos?page=2', true), '/admin/productos?page=2')
  for (const unsafe of ['//other.example', '/\\other.example', '/%2fother.example', '/login?redirect=/perfil', '/admin/dashboard']) {
    assert.equal(module.safeLoginReturn(unsafe), '/')
  }
  assert.equal(module.safeLoginReturn('/perfil', true), '/admin/dashboard')
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

test('concurrent and delayed 401s share one refresh; retries terminate on a second 401', async () => {
  const data = new Map()
  globalThis.localStorage = {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: key => data.delete(key),
  }
  globalThis.sessionStorage = { ...localStorage }
  globalThis.window = { addEventListener() {}, dispatchEvent() {} }
  const compile = async name => ts.transpileModule(
    await readFile(new URL(`../src/services/${name}.ts`, import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.ESNext } },
  ).outputText
  const asModule = source => 'data:text/javascript;base64,' + Buffer.from(source).toString('base64')
  const security = asModule(await compile('sessionSecurity') + '\n// refresh test')
  const source = (await compile('api')).replace('./sessionSecurity', security).replace('import.meta.env.VITE_API_URL', 'undefined')
  const { api } = await import(asModule(source))
  const signed = exp => 'mock.' + Buffer.from(JSON.stringify({ session_id: 'qa', user_id: 1, global_auth_version: 2, password_version: 0, exp })).toString('base64url') + '.mock'
  const before = signed(1), after = signed(2)
  localStorage.setItem('authToken', before)
  localStorage.setItem('refreshToken', 'synthetic')
  let refreshes = 0, retries = 0, accept = true
  let releaseLate
  const late = new Promise(resolve => { releaseLate = resolve })
  globalThis.fetch = async (url, config) => {
    if (url.endsWith('/auth/token/refresh/')) {
      refreshes += 1
      return Response.json({ access: after })
    }
    if (config.headers.Authorization === `Bearer ${before}`) {
      if (url.endsWith('/late')) await late
      return Response.json({ detail: 'expired' }, { status: 401 })
    }
    assert.equal(config.headers.Authorization, `Bearer ${after}`)
    retries += 1
    return accept ? Response.json({ ok: true }) : Response.json({ detail: 'expired' }, { status: 401 })
  }
  const delayed = api.get('/late')
  await Promise.all([api.get('/one'), api.get('/two')])
  releaseLate()
  await delayed
  assert.equal(refreshes, 1)
  assert.equal(retries, 3)
  accept = false
  await assert.rejects(api.get('/terminal'))
  assert.equal(refreshes, 2)
  assert.equal(localStorage.getItem('authToken'), null)
})
