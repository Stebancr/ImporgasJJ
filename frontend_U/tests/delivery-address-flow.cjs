const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const choose=require('./location-select.cjs')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(12000)
 let addresses=[],saves=0,quotes=0
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(()=>{localStorage.setItem('authToken',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`);localStorage.setItem('user',JSON.stringify({id:'55',name:'QA',email:'qa@example.invalid',role:'client'}))})
 await page.routeWebSocket('**/ws/**',ws=>ws.close());await page.route('https://**',r=>r.abort())
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;let status=200,body={data:[]}
  if(path.endsWith('/user/perfil'))body={id:55,nombre_completo:'QA',correo:'qa@example.invalid',telefono:'3000000000',estado:1,terms_version:'qa',current_terms_version:'qa',terms_accepted_at:new Date().toISOString()}
  else if(path.endsWith('/cart'))body={items:[{product_id:991,quantity:1}]}
  else if(path.endsWith('/products/991'))body={data:{id:991,name:'QA',price:125000,total_stock:20,is_available:true,images:[]}}
  else if(path.endsWith('/shipping/config'))body={enabled:true}
  else if(path.endsWith('/shipping/cities'))body=[{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'}]
  else if(path.endsWith('/shipping/quote')){quotes++;body={id:'00000000-0000-4000-8000-000000000001',total:'8000',subtotal:'125000',order_total:'133000',tcc_rate:'8000',surcharge:'0',taxes:'0',discounts:'0',expires_at:new Date(Date.now()+600000).toISOString()}}
  else if(path.endsWith('/user/addresses')){
   if(route.request().method()==='POST'){
    saves++;if(saves===1){status=400;body={phone:['Revisa este número de teléfono.']}}
    else {const a={...route.request().postDataJSON(),id:99};addresses=[a];status=201;body={data:a}}
   }else body={data:addresses}
  }
  await route.fulfill({status,json:body})
 })
 try{
  await page.goto('http://crm.localhost/checkout')
  await page.getByRole('button',{name:'Agregar nueva dirección',exact:true}).click()
  const form=page.getByRole('form',{name:'Formulario de dirección de entrega'})
  assert.equal(await form.getByRole('combobox').count(),2)
  await form.getByRole('button',{name:'Guardar dirección',exact:true}).click()
  await form.getByText('Escribe la dirección.',{exact:true}).waitFor();assert.equal(saves,0)
  await form.getByLabel('Nombre de quien recibe',{exact:true}).fill('Persona QA')
  await form.getByLabel('Número de teléfono',{exact:true}).fill('3000000000')
  await choose(page,'Departamento de entrega','VALLE DEL CAUCA');await choose(page,'Ciudad o municipio de entrega','76001000')
  await form.getByLabel('Dirección',{exact:true}).fill('Calle sintética QA')
  await form.getByRole('button',{name:'Guardar dirección',exact:true}).click()
  await form.getByText('Revisa este número de teléfono.',{exact:true}).waitFor()
  assert.equal(await form.getByLabel('Dirección',{exact:true}).inputValue(),'Calle sintética QA')
  await form.getByLabel('Número de teléfono',{exact:true}).fill('3000000001')
  await form.getByRole('button',{name:'Guardar dirección',exact:true}).dblclick()
  await page.getByRole('button',{name:/Casa.*Persona QA/}).waitFor()
  assert.equal(saves,2);assert.equal(addresses.length,1)
  assert.equal(await page.getByRole('button',{name:/Casa.*Persona QA/}).getAttribute('aria-pressed'),'true')
  await page.getByText('Costo de envío:',{exact:false}).waitFor()
  assert(quotes>0)
  await page.getByRole('button',{name:'Agregar nueva dirección',exact:true}).click()
  await page.getByRole('form',{name:'Formulario de dirección de entrega'}).getByRole('button',{name:'Cancelar',exact:true}).click()
  assert.equal(await page.getByLabel('Dirección',{exact:true}).inputValue(),'Calle sintética QA')
  await page.getByRole('button',{name:'Continuar al Pago',exact:true}).click();await page.reload()
  await page.getByRole('heading',{name:'Método de Pago',exact:true}).waitFor()
  const draft=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('delivery-checkout:55')))
  assert.equal(draft.address_id,99);assert.equal(draft.step,'payment');assert(draft.cartKey.includes('991'))
  for(const width of [1280,768,390]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))}
  assert.deepEqual(errors,[])
  console.log('PASS no saved addresses: inline validation, searchable unique fields, field-level server error retains draft, double click creates once, new address selected, quote and total updated, cancel/refresh preserve cart and payment step, responsive')
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)})