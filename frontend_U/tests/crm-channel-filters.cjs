// Synthetic browser fixtures only: no requests or messages reach real accounts.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
;(async () => {
  const browser = await chromium.launch({args: ['--host-resolver-rules=MAP crm.localhost nginx']})
  const page = await browser.newPage({viewport:{width:1280,height:1000}})
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))
    localStorage.setItem('token', `test.${payload}.synthetic`)
  })
  let socket, socketCount = 0
  await page.routeWebSocket('**/ws/crm-chat/', ws => { socket = ws; socketCount++ })
  const channels = ['whatsapp_web','whatsapp','instagram','facebook','ecommerce']
  const labels = ['WhatsApp Web','WhatsApp Cloud','Instagram','Facebook Messenger','Ecommerce']
  let sessions = channels.map((channel,index) => ({
    id:index+501,channel,user_name:`QA ${channel}`,status:'waiting',priority:'high',queue_id:8,
    unread_by_agent:2,avatar_url:'',external_thread_id:`synthetic-${channel}`,last_message:`Fixture ${channel}`,
  }))
  const message = (s,id=1000+s.id) => ({ id,text:`Mensaje ${s.channel}`,sender_type:'user',direction:'inbound',
    message_type:'text',status:'received',origin:'customer',attachments:[],created_at:'2026-10-14T12:00:00Z',timestamp:'2026-10-14T12:00:00Z' })
  let listRequests = 0, slowFacebook = false, failedSend = false, lateSend = false, pendingResolve
  let profileId = 998
  const sent = []
  const filtered = url => sessions.filter(s =>
    (!url.searchParams.get('channel') || url.searchParams.get('channel') === s.channel)
    && (!url.searchParams.get('status') || url.searchParams.get('status') === s.status)
    && (!url.searchParams.get('priority') || url.searchParams.get('priority') === s.priority)
    && (!url.searchParams.get('queue') || +url.searchParams.get('queue') === s.queue_id)
    && (!url.searchParams.get('search') || s.user_name.includes(url.searchParams.get('search'))))
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()), method = route.request().method()
    let body = {}, status = 200
    if (url.pathname.endsWith('/user/perfil')) body = {id:profileId,tipo_usuario:4,nombre_completo:'Admin QA',estado:1}
    else if (url.pathname.endsWith('/sessions/')) {
      listRequests++
      body = filtered(url)
      if (slowFacebook && url.searchParams.get('channel') === 'facebook') await sleep(500)
    } else if (url.pathname.endsWith('/pending-count/')) {
      const result = filtered(url)
      body = {total:result.length,count:result.filter(s=>s.status==='waiting').length,unread:result.reduce((n,s)=>n+s.unread_by_agent,0)}
    } else if (url.pathname.endsWith('/queues/')) body = [{id:8,name:'QA queue',active:true}]
    else if (/\/sessions\/\d+\/$/.test(url.pathname)) {
      const s = sessions.find(s => s.id === +url.pathname.match(/sessions\/(\d+)/)[1])
      if (method === 'PATCH') Object.assign(s, route.request().postDataJSON())
      body = s
    } else if (url.pathname.endsWith('/messages/')) {
      const s = sessions.find(s => s.id === +url.pathname.match(/sessions\/(\d+)/)[1])
      if (!s) { status=404;body={error:'Sesión no encontrada'} }
      else if (method === 'GET') {
        s.unread_by_agent=0
        // A repeated event must never produce duplicate bubbles.
        body = {messages:[message(s),message(s)],status:s.status,agent_name:''}
      } else {
        const payload = route.request().postData() || ''
        sent.push({sessionId:s.id,channel:s.channel,payload})
        if (lateSend) await new Promise(resolve => {pendingResolve=resolve})
        if (failedSend) {status=502;body={error:'Canal no disponible en prueba'}}
        else body = {...message(s,3000),sender_type:'agent',direction:'outbound',status:'sent'}
      }
    }
    try { await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)}) } catch { /* canceled old query */ }
  })
  const choose = async (label, value) => {
    await page.getByRole('combobox',{name:label,exact:true}).click()
    await page.getByRole('option',{name:value,exact:true}).click()
  }
  const list = () => page.locator('button').filter({has:page.getByText(/^QA (whatsapp_web|whatsapp|instagram|facebook|ecommerce)$/)})
  await page.goto('http://crm.localhost/admin/chat')
  await page.getByText('5 conversaciones · 5 pendientes · 10 no leídos',{exact:true}).waitFor()
  assert.equal(await list().count(),5)
  for (let i=0;i<channels.length;i++) {
    await choose('Canal',labels[i])
    await page.getByText(`QA ${channels[i]}`,{exact:true}).waitFor()
    assert.equal(await list().count(),1)
    await page.getByText(`QA ${channels[i]}`,{exact:true}).click()
    await page.getByText(`Mensaje ${channels[i]}`,{exact:true}).waitFor()
    assert.equal(await page.getByText(`Mensaje ${channels[i]}`,{exact:true}).count(),1)
    const composer = page.getByPlaceholder(`Responder por ${channels[i]}`)
    await composer.fill(`Respuesta sintética ${channels[i]}`)
    await page.getByRole('button',{name:'Enviar mensaje',exact:true}).click()
    await composer.waitFor()
    await page.waitForFunction(ch => document.querySelector(`textarea[placeholder="Responder por ${ch}"]`)?.value === '',channels[i])
    assert.equal(sent.at(-1).channel,channels[i])
    console.log(`UI FILTER ${channels[i]} expected=1 obtained=1 opening/manual mock send PASS`)
  }
  // Late old response cannot contaminate the currently selected filter.
  slowFacebook=true
  await choose('Canal','Facebook Messenger')
  await choose('Canal','Instagram')
  await page.getByText('QA instagram',{exact:true}).waitFor()
  await sleep(700)
  assert.equal(await list().count(),1)
  assert.equal(await page.getByText('QA facebook',{exact:true}).count(),0)
  slowFacebook=false
  await choose('Filtrar prioridad','Baja')
  await page.getByText('Sin conversaciones',{exact:true}).waitFor()
  await choose('Filtrar prioridad','Alta')
  await choose('Filtrar cola','QA queue')
  await page.getByPlaceholder('Buscar cliente o identificador').fill('QA instagram')
  await page.getByText('QA instagram',{exact:true}).waitFor()
  await choose('Estado','Cerrados')
  await page.getByText('Sin conversaciones',{exact:true}).waitFor()
  await choose('Estado','Pendientes')
  await page.getByText('QA instagram',{exact:true}).click()
  await page.getByText('1 conversaciones · 1 pendientes · 0 no leídos',{exact:true}).waitFor()
  const composer=page.getByPlaceholder('Responder por instagram')
  failedSend=true
  await composer.fill('Borrador conservado')
  await page.getByRole('button',{name:'Enviar mensaje',exact:true}).click()
  await page.getByText('Canal no disponible en prueba',{exact:true}).waitFor()
  assert.equal(await composer.inputValue(),'Borrador conservado')
  const clientId = sent.at(-1).payload.match(/name="client_message_id"\r?\n\r?\n([^\r\n]+)/)[1]
  // Switch filters and return: preserve draft and its idempotency key.
  await choose('Canal','Facebook Messenger')
  await page.getByPlaceholder('Buscar cliente o identificador').fill('')
  await page.getByText('QA facebook',{exact:true}).waitFor()
  await choose('Canal','Instagram')
  await page.getByText('QA instagram',{exact:true}).click()
  assert.equal(await composer.inputValue(),'Borrador conservado')
  failedSend=false
  await page.getByRole('button',{name:'Enviar mensaje',exact:true}).click()
  await page.waitForFunction(() => document.querySelector('textarea[placeholder="Responder por instagram"]')?.value === '')
  assert(sent.at(-1).payload.includes(clientId),'Retry after changing filter keeps idempotency key')
  // A late successful send cannot erase another session's draft.
  lateSend=true
  await composer.fill('Respuesta tardía QA')
  await page.getByRole('button',{name:'Enviar mensaje',exact:true}).click()
  while (!pendingResolve) await sleep(20)
  await choose('Canal','Facebook Messenger')
  await page.getByText('QA facebook',{exact:true}).click()
  const fbComposer=page.getByPlaceholder('Responder por facebook')
  await fbComposer.fill('Otro borrador')
  pendingResolve();lateSend=false
  await sleep(300)
  assert.equal(await fbComposer.inputValue(),'Otro borrador')
  // Events refetch authoritative counts; duplicate events cannot increment twice.
  await choose('Canal','Instagram')
  sessions.find(s=>s.channel==='instagram').unread_by_agent=1
  const before=listRequests
  socket.send(JSON.stringify({type:'message.created',session_id:503,message_id:9090}))
  socket.send(JSON.stringify({type:'message.created',session_id:503,message_id:9090}))
  await page.getByText('1 conversaciones · 1 pendientes · 1 no leídos',{exact:true}).waitFor()
  assert.equal(await list().count(),1)
  socket.send(JSON.stringify({type:'message.created',session_id:504,message_id:9091}))
  await sleep(150)
  assert.equal(await page.getByText('QA facebook',{exact:true}).count(),0)
  socket.close()
  await page.getByText('Reconectando tiempo real',{exact:true}).waitFor()
  sessions.find(s=>s.channel==='instagram').unread_by_agent=2
  await page.getByText('Tiempo real conectado',{exact:true}).waitFor()
  await page.getByText('1 conversaciones · 1 pendientes · 2 no leídos',{exact:true}).waitFor()
  assert(socketCount>=2 && listRequests>before)
  // Navigation restores per-user selections. Another account starts with all.
  await page.goto('http://crm.localhost/admin/chat/plantillas')
  await page.goto('http://crm.localhost/admin/chat')
  await page.getByText('QA instagram',{exact:true}).waitFor()
  assert.equal(await list().count(),1)
  const stored = await page.evaluate(() => sessionStorage.getItem('crm-inbox:998'))
  assert(stored && !stored.includes('search'))
  profileId=999
  await page.reload()
  await page.getByText('5 conversaciones',{exact:false}).waitFor()
  assert.equal(await list().count(),5)
  // Mobile selection closes dropdown and opens the correct conversation.
  await page.setViewportSize({width:390,height:900})
  await choose('Canal','WhatsApp Web')
  await page.getByText('QA whatsapp_web',{exact:true}).click()
  await page.getByPlaceholder('Responder por whatsapp_web').waitFor()
  assert.equal(await page.getByRole('listbox').count(),0)
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  if (process.env.EVIDENCE_DIR) await page.screenshot({path:`${process.env.EVIDENCE_DIR}/crm-channel-mobile.png`,fullPage:true})
  await page.getByRole('button',{name:'Volver a conversaciones'}).click()
  await page.getByText('QA whatsapp_web',{exact:true}).waitFor()
  assert.deepEqual(errors,[])
  console.log('PASS: all channels, combined/empty filters, cancellation, drafts/idempotency, late send, deduplication, counts, WebSocket reconnect, persistence/isolation, mobile')
  await browser.close()
})().catch(error=>{console.error(error.stack);process.exit(1)})
