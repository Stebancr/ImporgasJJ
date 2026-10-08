// Browser-only fixtures. Persistence/permissions/provider errors are tested in Django.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--host-resolver-rules=MAP crm.localhost nginx'] })
  const page = await browser.newPage()
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now()/1000)+3600 }))
    localStorage.setItem('token', `test.${payload}.synthetic`)
    localStorage.setItem('adminUser', JSON.stringify({ email: 'qa@example.invalid' }))
  })
  await page.routeWebSocket('**/ws/**', ws => ws.close())
  let sent = 0
  let finalPayload = ''
  const session = { id: 991, user_name: 'Cliente QA', status: 'active', channel: 'instagram', agent_name: 'Asesor QA', avatar_url: '', priority: 'normal', unread_by_agent: 0 }
  const template = { id: 81, name: 'Saludo QA', text: 'Hola {{nombre_cliente}}, {{nombre_producto}}', category: 'Ventas', active: true, channels: ['instagram'], variables: ['nombre_cliente', 'nombre_producto'], favorite: false, last_used_at: null, author_name: 'QA', updated_at: new Date().toISOString(), attachment_url: '', attachment_metadata: {} }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    let body = {}
    let status = 200
    if (url.pathname.endsWith('/user/perfil')) body = { id: 998, tipo_usuario: 4, nombre_completo: 'Administrador QA', estado: 1 }
    else if (url.pathname.endsWith('/sessions/')) body = [session]
    else if (url.pathname.endsWith('/pending-count/')) body = { count: 0 }
    else if (url.pathname.endsWith('/queues/')) body = []
    else if (url.pathname.endsWith('/messages/') && method === 'GET') body = { messages: [], status: 'active' }
    else if (url.pathname.endsWith('/messages/') && method === 'POST') {
      sent++; finalPayload = route.request().postData() || ''
      body = { id: 901, status: 'sent', attachments: [] }
    }
    else if (url.pathname.endsWith('/templates/')) body = [template]
    else if (url.pathname.endsWith('/preview/')) {
      const data = route.request().postDataJSON()
      if (!data.variables.nombre_producto) { status = 400; body = { error: 'Completa las variables: nombre_producto' } }
      else body = { text: `Hola ${data.variables.nombre_cliente}, ${data.variables.nombre_producto}`, attachment_url: '' }
    }
    else if (url.pathname.endsWith('/favorite/')) { template.favorite = !template.favorite; body = { favorite: template.favorite } }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('http://crm.localhost/admin/chat')
  await page.getByText('Cliente QA', { exact: true }).click()
  await page.getByRole('button', { name: 'Plantillas', exact: true }).click()
  await page.getByRole('button', { name: 'Saludo QA', exact: true }).click()
  await page.getByRole('button', { name: 'Vista previa final', exact: true }).click()
  await page.getByText('Completa las variables: nombre_producto', { exact: true }).waitFor()
  await page.getByLabel('nombre_producto', { exact: true }).fill('Calentador de prueba')
  await page.getByRole('button', { name: 'Vista previa final', exact: true }).click()
  await page.getByRole('button', { name: 'Insertar y revisar en el chat', exact: true }).click()
  assert.equal(sent, 0, 'Inserting a template must never send')
  const composer = page.getByPlaceholder('Responder por instagram')
  await composer.fill('Hola Cliente QA, mensaje revisado')
  for (const width of [1280, 768, 390]) {
    await page.setViewportSize({ width, height: 900 })
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `Horizontal overflow at ${width}`)
  }
  assert.equal(await page.locator('input[type=file]').getAttribute('accept'), '.jpg,.jpeg,.png,.webp,.gif')
  const confirmed = page.waitForResponse(r => r.url().includes('/messages/') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Enviar mensaje', exact: true }).click()
  await confirmed
  assert.equal(sent, 1)
  assert(finalPayload.includes('Hola Cliente QA, mensaje revisado'))
  assert(finalPayload.includes('template_id'))
  assert(finalPayload.includes('client_message_id'))
  assert.deepEqual(errors, [])
  console.log('PASS: templates, missing variables, preview, editable insertion without sending, channel types, send metadata, responsive 1280/768/390, no browser errors')
  await browser.close()
})().catch(e => { console.error(e.message); process.exit(1) })
