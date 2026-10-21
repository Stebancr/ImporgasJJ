const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 await page.addInitScript(()=>localStorage.setItem('token',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`))
 await page.routeWebSocket('**/ws/**',ws=>ws.close())
 await page.route('https://**',route=>route.abort())
 let saves=0,fail=true,payload=''
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let status=200,body={}
  if(path.endsWith('/user/perfil'))body={id:998,tipo_usuario:4,nombre_completo:'Administrador QA',estado:1}
  else if(path.endsWith('/templates/')&&route.request().method()==='GET')body=[]
  else if(path.endsWith('/templates/')&&route.request().method()==='POST'){
   saves++;payload=route.request().postData()
   await new Promise(resolve=>setTimeout(resolve,350))
   if(fail){status=400;body={name:['Ya existe una plantilla con este nombre.']}}
   else body={id:993}
  }
  await route.fulfill({status,json:body})
 })
 try{
  await page.goto('http://crm.localhost/admin/chat/plantillas')
  await page.getByRole('button',{name:'Nueva plantilla',exact:true}).click()
  const name=page.getByRole('textbox',{name:/^Nombre/}),content=page.getByRole('textbox',{name:'Contenido',exact:true})
  await name.fill('Validación QA')
  await content.fill('Hola , gracias por escribir.')
  await content.evaluate(el=>{el.focus();el.setSelectionRange(5,5)})
  await page.getByRole('combobox',{name:'Insertar variable'}).click()
  await page.getByRole('option',{name:'nombre cliente',exact:true}).click()
  assert.equal(await content.inputValue(),'Hola {{nombre_cliente}}, gracias por escribir.')
  await page.getByTestId('template-message-body').getByText(/María Pérez/).waitFor()
  await page.getByRole('button',{name:'Guardar plantilla',exact:true}).dblclick()
  await page.getByText('Ya existe una plantilla con este nombre.',{exact:true}).waitFor()
  assert.equal(saves,1)
  assert.equal(await name.inputValue(),'Validación QA')
  assert.equal(await content.inputValue(),'Hola {{nombre_cliente}}, gracias por escribir.')
  assert(await name.getAttribute('aria-invalid')==='true')
  await content.fill('{{desconocida}}')
  assert(await page.getByRole('button',{name:'Guardar plantilla',exact:true}).isDisabled())
  await content.fill('x'.repeat(1001))
  assert(await page.getByRole('button',{name:'Guardar plantilla',exact:true}).isDisabled(),'Instagram limit')
  await content.fill('Hola **{{nombre_cliente}}**\nTu pedido está listo.')
  await name.fill('Validación QA corregida')
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:1100})
   assert(await page.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth),`overflow ${width}`)
   if(process.env.QA_OUTPUT)await page.screenshot({path:`${process.env.QA_OUTPUT}/template-editor-${width}.png`,animations:'disabled'})
  }
  await page.getByRole('combobox',{name:'Estado de la plantilla'}).click()
  await page.getByRole('option',{name:'Inactiva',exact:true}).click()
  fail=false
  await page.getByRole('button',{name:'Guardar plantilla',exact:true}).click()
  await page.getByRole('button',{name:'Nueva plantilla',exact:true}).waitFor()
  assert.equal(saves,2)
  assert(payload.includes('name="active"\r\n\r\nfalse'))
  console.log('PASS templates: variable inserted at cursor, live preview, duplicate-name field error, draft retained, double-click guarded, unknown variables blocked, channel length limit, active state saved, responsive 1280/768/390. No messages sent.')
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exit(1)})
