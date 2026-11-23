const { chromium } = require('/tools/node_modules/playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const run = process.env.GLOBAL_AUTH_RUN_ID
let stage = 'startup'
let lastPage
let pageErrors = []
;(async () => {
  assert.equal(process.env.GLOBAL_AUTH_ISOLATED_QA, '1')
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP localhost nginx'] })
  try {
    const sizes = [[1440, 900], [768, 1024], [390, 844]].filter(([width]) => !process.env.QA_SECURITY_VIEWPORT || String(width) === process.env.QA_SECURITY_VIEWPORT)
    for (const [width, height] of sizes) {
      // Six logins would exceed the real 5/minute limit. Respect it, never disable it.
      if (sizes.length === 3 && width === 390) await new Promise(resolve => setTimeout(resolve, 61000))
      const context = await browser.newContext({ viewport: { width, height } })
      await context.addInitScript(() => {
        window.securityWsEvents = []
        const Original = window.WebSocket
        window.WebSocket = class extends Original {
          constructor(...args) {
            super(...args)
            if (String(args[0]).includes('/ws/crm-chat/')) {
              window.securityWsEvents.push('created')
              this.addEventListener('open', () => window.securityWsEvents.push('open'))
              this.addEventListener('close', event => window.securityWsEvents.push(`close:${event.code}`))
            }
          }
        }
      })
      await context.route('**/*', route => {
        const host = new URL(route.request().url()).hostname
        return ['nginx', 'localhost'].includes(host) ? route.continue() : route.abort()
      })
      const page = await context.newPage()
      lastPage = page
      const errors = []
      pageErrors = errors
      page.on('pageerror', error => errors.push(error.message))
      await page.goto('http://localhost/admin/login')
      stage = `login-${width}`
      await page.locator('#usuario').fill('security-browser-fixture')
      await page.locator('#password').fill('Synthetic@Browser937!')
      await page.locator('button[type=submit]').click()
      await page.waitForURL('**/admin/dashboard')
      await page.goto('http://localhost/admin/chat')
      stage = `chat-${width}`
      const other = await context.newPage()
      await other.goto('http://localhost/admin/chat')
      const credential = await page.evaluate(() => localStorage.getItem('token'))
      const response = await page.request.post('http://nginx/api/crm-chat/whatsapp-web/realtime-token/', { headers: { Authorization: `Bearer ${credential}` } })
      assert.equal(response.status(), 200)
      const realtime = (await response.json()).token
      await page.addScriptTag({ url: 'http://localhost/whatsapp-gateway/socket.io/socket.io.js' })
      await page.evaluate(async token => {
        window.securityClosures = 0
        window.addEventListener('admin:logout', () => { window.securityClosures += 1 })
        await new Promise((resolve, reject) => {
          const socket = window.io(location.origin, { path: '/whatsapp-gateway/socket.io', transports: ['websocket'], auth: { token }, reconnection: false })
          window.securitySocket = socket
          socket.once('connect', resolve)
          socket.once('connect_error', () => reject(new Error('Synthetic gateway handshake failed')))
          socket.once('disconnect', () => { window.gatewayClosed = true })
        })
      }, realtime)
      stage = `revocation-${width}`
      fs.writeFileSync(`/evidence/revoke-requested-${run}-${width}`, 'ready')
      const deadline = Date.now() + 180000
      while (!fs.existsSync(`/evidence/revoke-done-${run}-${width}`)) {
        if (Date.now() > deadline) throw new Error('QA controller did not execute revocation')
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      await page.waitForURL('**/admin/login', { timeout: 20000 })
      await other.waitForURL('**/admin/login', { timeout: 20000 })
      stage = `assertions-${width}`
      await page.waitForFunction(() => window.gatewayClosed === true, { timeout: 5000 })
      assert.equal(await page.evaluate(() => window.securityClosures), 1)
      for (const tab of [page, other]) {
        assert.equal(await tab.evaluate(() => localStorage.getItem('token')), null)
        assert.equal(await tab.evaluate(() => localStorage.getItem('refresh')), null)
        assert(await tab.getByRole('status').textContent().then(text => text.includes('inicia sesión nuevamente')))
        assert(await tab.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      }
      await page.screenshot({ path: `/evidence/revoked-${width}.png`, fullPage: true })
      const stale = await page.request.get('http://nginx/api/user/perfil', { headers: { Authorization: `Bearer ${credential}` } })
      assert.equal(stale.status(), 401)
      await page.locator('#usuario').fill('security-browser-fixture')
      await page.locator('#password').fill('Synthetic@Browser937!')
      await page.locator('button[type=submit]').click()
      await page.waitForURL('**/admin/dashboard')
      assert.equal(errors.length, 0)
      console.log(`PASS ${width}: login, two tabs, Channels, real Socket.IO, global revocation, old access denied, same-password relogin, responsive`)
      fs.writeFileSync(`/evidence/browser-passed-${width}`, 'passed')
      await context.close()
    }
  } finally {
    if (lastPage && !lastPage.isClosed()) {
      fs.writeFileSync('/evidence/browser-diagnostic.json', JSON.stringify({ stage, url: lastPage.url(), errors: pageErrors,
        state: await lastPage.evaluate(() => ({ hasAdminToken: !!localStorage.getItem('token'), revoked: sessionStorage.getItem('auth:revoked'),
          closures: window.securityClosures, gatewayClosed: window.gatewayClosed, wsEvents: window.securityWsEvents, text: document.body.innerText.slice(0, 200) })) }))
    }
    await browser.close()
  }
})().catch(error => { console.error(`FAIL ${stage}: ${String(error.message).replace(/eyJ[A-Za-z0-9_.-]+/g, '[redacted]')}`); process.exitCode = 1 })
