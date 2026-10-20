// Synthetic browser traffic only; database and provider contracts have Docker backend tests.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP crm.localhost nginx'] })
  const page = await browser.newPage()
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.addInitScript(() => {
    localStorage.setItem('authToken', 'synthetic')
    localStorage.setItem('user', JSON.stringify({ id: 990, email: 'qa@example.invalid', name: 'QA' }))
    sessionStorage.setItem('chatSessionId', '990')
  })
  await page.routeWebSocket('**/ws/**', socket => socket.close())
  const session = { id: 990, status: 'active', agent_name: 'QA' }
  const messages = []
  let attempts = 0, firstId = ''
  await page.route('**/api/**', async route => {
    const { pathname: path } = new URL(route.request().url())
    let json = [], status = 200
    if (path.endsWith('/user/perfil')) json = { id: 990, estado: 1, nombre_completo: 'QA' }
    else if (path.endsWith('/sessions/990/')) json = session
    else if (path.endsWith('/messages/')) {
      if (route.request().method() === 'POST') {
        attempts++
        const raw = route.request().postDataBuffer().toString()
        const id = raw.match(/name="client_message_id"\r\n\r\n([^\r]+)/)[1]
        if (attempts === 1) { firstId = id; status = 503; json = { error: 'Synthetic network error' } }
        else {
          assert.equal(id, firstId, 'Retry must reuse idempotency key')
          assert(raw.includes('foto-qa.png'))
          messages.push({ id: 701, sender_type: 'user', text: '**Hola**\nSegunda línea 😃', created_at: new Date().toISOString(), attachments: [{ id: 702, name: 'foto-qa.png', mime_type: 'image/png', size: 68, state: 'stored', url: '/api/crm-chat/attachments/702/' }] })
          json = messages[0]
        }
      } else json = { ...session, messages }
    } else if (path.endsWith('/attachments/702/')) {
      return route.fulfill({ contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9WQAAAAASUVORK5CYII=', 'base64') })
    }
    await route.fulfill({ status, json })
  })
  await page.goto('http://crm.localhost/contacto')
  await page.getByRole('button', { name: 'Abrir chat de ayuda' }).click()
  const chat = page.getByRole('dialog', { name: 'Chat de ayuda' })
  const input = chat.getByLabel('Mensaje', { exact: true })
  await input.fill('**Hola**\nSegunda línea 😃')
  await chat.getByLabel('Adjuntar archivo', { exact: true }).setInputFiles({ name: 'foto-qa.png', mimeType: 'image/png', buffer: Buffer.from('qa') })
  await chat.getByRole('button', { name: 'Enviar mensaje', exact: true }).click()
  await chat.getByRole('alert').waitFor()
  assert.equal(await input.inputValue(), '**Hola**\nSegunda línea 😃')
  await chat.getByRole('button', { name: 'Quitar archivo' }).waitFor()
  await chat.getByRole('button', { name: 'Enviar mensaje', exact: true }).click()
  await chat.getByRole('button', { name: 'Ampliar foto-qa.png' }).waitFor()
  assert.equal(await input.inputValue(), '')
  assert.equal(await chat.locator('strong').innerText(), 'Hola')
  await page.reload()
  await page.getByRole('button', { name: 'Abrir chat de ayuda' }).click()
  await chat.getByRole('button', { name: 'Ampliar foto-qa.png' }).waitFor()
  assert.equal(await chat.getByRole('button', { name: 'Ampliar foto-qa.png' }).count(), 1)
  for (const width of [1280, 768, 390]) {
    await page.setViewportSize({ width, height: 900 })
    assert(await chat.evaluate(el => el.scrollWidth <= el.clientWidth), `overflow at ${width}`)
  }
  assert.equal(attempts, 2)
  assert.deepEqual(errors, [])
  console.log('PASS: ecommerce file + text, failure preserves draft, stable retry, authenticated preview, reload, no duplicate, responsive')
  await browser.close()
})().catch(error => { console.error(error.stack); process.exit(1) })
