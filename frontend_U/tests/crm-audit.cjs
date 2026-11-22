// Synthetic fixtures only. Browser network stays on the isolated CRM origin.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP crm.localhost nginx'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(15000)
  const errors = [], escapes = [], offsets = [], cursors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    if (location.hostname !== 'crm.localhost') return
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now()/1000)+3600 }))
    localStorage.setItem('token', `test.${payload}.synthetic`)
  })
  await page.route('**/*', route => {
    const url = new URL(route.request().url())
    if (url.hostname !== 'crm.localhost') { escapes.push(url.hostname); return route.abort() }
    return route.continue()
  })
  await page.routeWebSocket('**/ws/**', socket => socket.close())
  const sessions = Array.from({length:201}, (_, i) => ({id:i+1, user_name:`Auditoría ${i+1}`,
    channel:'facebook', status:'active', priority:'normal', unread_by_agent:0, avatar_url:'', agent_name:'QA'}))
  const message = id => ({id, text:`Historia ${id}`, sender_type:id===200?'agent':'user',
    direction:id===200?'outbound':'inbound', status:id===200?'sent':'received',
    simulated:id===200, message_type:'text', attachments:[], origin:'crm',
    timestamp:new Date(1700000000000+id*1000).toISOString()})
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    let json = {}
    if (url.pathname.endsWith('/user/perfil')) json = {id:9001, tipo_usuario:4, estado:1, nombre_completo:'Auditoría'}
    else if (url.pathname.endsWith('/pending-count/')) json = {total:201, count:0, unread:0}
    else if (url.pathname.endsWith('/sessions/')) {
      const offset = Number(url.searchParams.get('offset') || 0); offsets.push(offset)
      json = sessions.slice(offset, offset+100)
    } else if (url.pathname.endsWith('/queues/')) json = []
    else if (url.pathname.endsWith('/messages/')) {
      const before = url.searchParams.get('before'); cursors.push(before)
      json = {status:'active', agent_name:'QA', has_more:!before, before:before?1:101,
        messages:Array.from({length:100}, (_, i) => message(i+(before?1:101)))}
    }
    await route.fulfill({json})
  })
  await page.goto('http://crm.localhost/admin/chat')
  await page.getByText('Auditoría 1', {exact:true}).waitFor()
  await page.getByRole('button', {name:'Siguiente', exact:true}).click()
  await page.getByText('Auditoría 101', {exact:true}).waitFor()
  await page.getByRole('button', {name:'Siguiente', exact:true}).click()
  await page.getByText('Auditoría 201', {exact:true}).click()
  await page.getByText('Simulado', {exact:true}).waitFor()
  await page.getByRole('button', {name:'Cargar mensajes anteriores', exact:true}).click()
  await page.getByText('Historia 1', {exact:true}).waitFor()
  assert.equal(await page.getByText('Historia 200', {exact:true}).count(), 1)
  assert.equal(await page.getByRole('button', {name:'Cargar mensajes anteriores', exact:true}).count(), 0)
  assert(offsets.includes(0) && offsets.includes(100) && offsets.includes(200))
  assert(cursors.includes('101'))
  for (const width of [1920,1440,1024,820,768,390,320]) {
    await page.setViewportSize({width,height:1000})
    await page.getByPlaceholder('Responder por facebook').waitFor({state:'visible'})
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow ${width}`)
    assert(await page.getByPlaceholder('Responder por facebook').isVisible(), `Composer ${width}`)
    if (process.env.EVIDENCE_DIR && [1440,768,390].includes(width))
      await page.screenshot({path:`${process.env.EVIDENCE_DIR}/crm-audit-${width}.png`,fullPage:true})
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(escapes, [])
  console.log('PASS CRM audit: 201 conversations, cursor history 200 messages without duplicates, simulator label, seven responsive widths, no browser errors or external requests')
  await browser.close()
})().catch(error => { console.error(error.stack); process.exit(1) })
