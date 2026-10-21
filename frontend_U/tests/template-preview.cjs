// Docker browser check. All API requests are intercepted; no messages are sent.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(()=>{
  const payload=btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))
  localStorage.setItem('token',`test.${payload}.synthetic`)
 })
 await page.routeWebSocket('**/ws/**',ws=>ws.close())
 let sends=0,savePayload=''
 const template={id:81,name:'Saludo multicanal QA',text:'Hola *{{nombre_cliente}}* 👋\n_Revisa tu pedido_ ~anterior~ `PED-123`\nhttps://example.invalid/producto\n<script>window.QA_INJECTED=1</script>',category:'Ventas',active:true,channels:['whatsapp_web','facebook','instagram'],variables:['nombre_cliente'],favorite:false,last_used_at:null,author_name:'QA',updated_at:new Date().toISOString(),attachment_url:'',attachment_metadata:{}}
 const pdf={...template,id:82,name:'Adjunto protegido QA',category:'',attachment_url:'/api/crm-chat/templates/82/attachment/',attachment_metadata:{name:'Informe.pdf',mime_type:'application/pdf'}}
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url());let body={},status=200
  if(url.pathname.endsWith('/user/perfil'))body={id:998,tipo_usuario:4,nombre_completo:'Administrador QA',estado:1}
  else if(url.pathname.endsWith('/attachment/')){status=503;body={error:'QA unavailable'}}
  else if(url.pathname.endsWith('/templates/') && route.request().method()==='GET')body=[template,pdf]
  else if(url.pathname.includes('/templates/') && route.request().method()==='POST'){
   savePayload=route.request().postData()||'';body=template
  } else if(url.pathname.endsWith('/messages/') && route.request().method()==='POST')sends++
  await route.fulfill({status,json:body})
 })
 await page.goto('http://crm.localhost/admin/chat/plantillas')
 await page.getByRole('button',{name:template.name,exact:true}).click()
 const preview=page.getByRole('region',{name:'Vista previa del mensaje para el cliente'})
 const body=preview.getByTestId('template-message-body')
 await preview.locator('[data-preview-channel=whatsapp_web]').waitFor()
 assert.equal(await body.locator('strong').innerText(),'María Pérez')
 assert.equal(await body.locator('em').innerText(),'Revisa tu pedido')
 assert.equal(await body.locator('s').innerText(),'anterior')
 assert.equal(await body.locator('code').innerText(),'PED-123')
 assert.equal(await body.locator('script,img').count(),0)
 assert.equal(await page.evaluate(()=>window.QA_INJECTED),undefined)
 for(const channel of ['Facebook Messenger','Instagram','WhatsApp Web']){
  await preview.getByLabel('Canal de la vista previa').click()
  await page.getByRole('option',{name:channel,exact:true}).click()
  if(channel!=='WhatsApp Web'){
   assert.equal(await body.locator('strong').count(),0)
   assert((await body.innerText()).includes('María Pérez'));assert(!(await body.innerText()).includes('*María Pérez*'))
  }
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:1000})
   assert(await page.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth),`dialog overflow ${channel} ${width}`)
   assert(await preview.evaluate(el=>el.scrollWidth<=el.clientWidth),`preview overflow ${channel} ${width}`)
  }
  await page.getByRole('listbox').waitFor({state:'hidden'})
  if(process.env.QA_OUTPUT)await preview.screenshot({path:`${process.env.QA_OUTPUT}/template-${channel.replaceAll(' ','-')}.png`,animations:'disabled'})
 }
 await page.getByRole('button',{name:'Editar',exact:true}).first().click()
 const content=page.getByLabel('Contenido', {exact:true})
 assert.equal(await content.inputValue(),template.text)
 const draft='Hola *{{nombre_cliente}}*\nGracias por escribirnos. '+ 'Producto '.repeat(12)
 await content.fill(draft)
 await preview.getByTestId('template-message-body').getByText('María Pérez',{exact:true}).waitFor()
 assert.equal(await content.inputValue(),draft)
 await page.locator('input[type=file]').setInputFiles({name:'foto-qa.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9WQAAAAASUVORK5CYII=','base64')})
 await preview.getByRole('img',{name:'Adjunto: foto-qa.png'}).waitFor()
 for(const width of [1280,768,390]){
  await page.setViewportSize({width,height:1000})
  assert(await page.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth),`editor overflow ${width}`)
 }
 await page.getByRole('button',{name:'Cancelar',exact:true}).click()
 await page.getByRole('button',{name:pdf.name,exact:true}).click()
 await preview.getByText('Informe.pdf',{exact:true}).waitFor()
 await preview.getByText('No se pudo mostrar el adjunto. El archivo sigue asociado a la plantilla.').waitFor()
 await preview.getByLabel('Canal de la vista previa').click()
 await page.getByRole('option',{name:'Instagram',exact:true}).click()
 await preview.getByText('Adjunto no compatible',{exact:true}).waitFor()
 await preview.getByText(/Instagram solo tiene habilitadas imágenes/).waitFor()
 await preview.getByLabel('Canal de la vista previa').click()
 await page.getByRole('option',{name:'Facebook Messenger',exact:true}).click()
 await preview.getByText(/Este canal requiere enviar el texto y este archivo por separado/).waitFor()
 await page.getByRole('combobox',{name:'Categoría',exact:true}).click()
 await page.getByRole('option',{name:'Sin categoría',exact:true}).click()
 assert.equal(await page.getByRole('button',{name:template.name,exact:true}).count(),0)
 assert.equal(await page.getByRole('button',{name:pdf.name,exact:true}).count(),1)
 await page.getByRole('combobox',{name:'Estado',exact:true}).click()
 await page.getByRole('option',{name:'Inactivas',exact:true}).click()
 await page.getByText('No hay plantillas para estos filtros.',{exact:true}).waitFor()
 assert.equal(sends,0);assert.equal(savePayload,'');assert.deepEqual(errors,[])
 console.log('PASS: three channel styles, WhatsApp formatting, literal Instagram/Facebook text, safe HTML, variables, live edit, local image, protected attachment error, responsive 1280/768/390, no sends or saves')
 await browser.close()
})().catch(error=>{console.error(error.stack);process.exit(1)})
