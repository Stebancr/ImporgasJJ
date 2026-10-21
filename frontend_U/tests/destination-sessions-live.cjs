// Real isolated Django/PostgreSQL; carrier and payment remain synthetic.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const choose=require('./location-select.cjs')
const api=process.env.QA_API_URL,web=process.env.QA_WEB_URL||'http://crm.localhost'
;(async()=>{
 assert(api,'Requires isolated QA backend')
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(20000)
 const errors=[],estimates=[];let addressReads=0,addressWrites=0,failSave=true
 page.on('pageerror',e=>errors.push(e.message))
 try{
  let state
  for(let i=0;i<60;i++){try{const r=await page.request.get(api+'/__qa/state',{timeout:1000});if(r.ok()){state=await r.json();break}}catch{}await page.waitForTimeout(500)}
  assert(state?.database_isolated)
  const cities=await(await page.request.get(api+'/shipping/cities')).json()
  const bogota=cities.find(city=>city.code==='11001000')
  const product=web+'/producto/'+state.product_id
  await page.route('https://**',r=>r.abort());await page.routeWebSocket('**/ws/**',s=>s.close())
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url()),method=route.request().method()
   if(url.pathname.endsWith('/user/addresses')){
    if(method==='GET')addressReads++
    if(method==='POST'){addressWrites++;if(failSave){failSave=false;return route.fulfill({status:503,json:{error:'Fallo temporal sintético al guardar'}})}}
   }
   if(url.pathname.endsWith('/shipping/estimate')){
    const payload=route.request().postDataJSON();estimates.push(payload)
    assert(Object.keys(payload).every(k=>['items','tcc_city_code','address_id','force'].includes(k)))
   }
   try{const response=await route.fetch({url:api+url.pathname.replace(/^\/api/,'')+url.search});await route.fulfill({response})}catch{await route.abort().catch(()=>{})}
  })
  await page.goto(product)
  const delivery=page.getByRole('region',{name:'Información de envío'})
  await delivery.getByRole('button',{name:'Configurar ubicación de entrega'}).click()
  await choose(page,'Departamento de entrega','VALLE DEL CAUCA');await choose(page,'Ciudad o municipio de entrega','76001000')
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  assert.equal(addressReads,0);assert.equal(addressWrites,0)
  const temporary=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('tcc-checkout-destination:guest')))
  assert(Object.keys(temporary).every(key=>['tcc_city_code','city','department','manual_location'].includes(key)))
  assert.equal(estimates.at(-1).tcc_city_code,'76001000')
  await page.goto(web+'/productos');await page.goto(product)
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  await page.getByRole('button',{name:'Agregar al Carrito',exact:true}).click()
  await page.getByRole('alertdialog').getByRole('link',{name:'Iniciar sesión',exact:true}).click()
  await page.locator('#customer-email').fill('dest@qa.invalid');await page.locator('#customer-password').fill('TCC-synthetic-fixture-only')
  await page.getByRole('button',{name:'Iniciar Sesion',exact:true}).click();await page.waitForURL('**/carrito')
  const headers={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('authToken'))}
  const cart=await(await page.request.get(api+'/ecommerce/cart',{headers})).json()
  assert.equal(cart.items.length,1);assert.equal(cart.items[0].quantity,1)
  await page.goto(product)
  await delivery.getByText('Todavía no tienes una dirección de entrega',{exact:false}).waitFor()
  assert.equal(await delivery.getByRole('button',{name:'Configurar ubicación de entrega'}).count(),0)
  const estimateCount=estimates.length;await page.waitForTimeout(800);assert.equal(estimates.length,estimateCount)
  await delivery.getByRole('button',{name:'Agregar nueva dirección',exact:true}).click()
  let form=page.getByRole('form',{name:'Formulario de dirección de entrega'})
  await choose(page,'Departamento de entrega','VALLE DEL CAUCA');await choose(page,'Ciudad o municipio de entrega','76001000')
  await form.getByLabel('Dirección',{exact:true}).fill('Calle sintética primera QA')
  await form.getByRole('button',{name:'Guardar dirección'}).click()
  await form.getByText('Fallo temporal sintético al guardar',{exact:false}).waitFor()
  assert.equal(await form.getByLabel('Dirección',{exact:true}).inputValue(),'Calle sintética primera QA')
  await form.getByRole('button',{name:'Guardar dirección'}).dblclick();await form.waitFor({state:'hidden'})
  await delivery.getByLabel('Dirección de entrega seleccionada').getByText('Calle sintética primera QA',{exact:false}).waitFor()
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  let saved=(await(await page.request.get(api+'/ecommerce/user/addresses',{headers})).json()).data
  assert.equal(saved.length,1);assert(saved[0].is_default);assert.equal(addressWrites,2)
  const first=saved[0]
  assert.equal(estimates.at(-1).address_id,first.id)
  await page.reload();await delivery.getByLabel('Dirección de entrega seleccionada').getByText(first.address,{exact:false}).waitFor()
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  await delivery.getByRole('button',{name:'Agregar nueva dirección',exact:true}).click();form=page.getByRole('form',{name:'Formulario de dirección de entrega'})
  await form.getByLabel('Dirección',{exact:true}).fill('Calle sintética segunda QA')
  await choose(page,'Departamento de entrega',bogota.department);await choose(page,'Ciudad o municipio de entrega','11001000')
  assert(!(await form.getByRole('checkbox').isChecked()))
  await form.getByRole('button',{name:'Guardar dirección'}).click();await form.waitFor({state:'hidden'})
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  saved=(await(await page.request.get(api+'/ecommerce/user/addresses',{headers})).json()).data
  const second=saved.find(a=>a.address.includes('segunda'))
  assert.equal(saved.find(a=>a.is_default).id,first.id)
  assert.equal(estimates.at(-1).address_id,second.id)
  await page.reload();await delivery.getByLabel('Dirección de entrega seleccionada').getByText(second.address,{exact:false}).waitFor()
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  for(const width of [1280,768,390]){
    await page.setViewportSize({width,height:1000})
    await page.waitForFunction(()=>document.documentElement.scrollWidth<=window.innerWidth)
    if(process.env.QA_OUTPUT)await delivery.screenshot({path:process.env.QA_OUTPUT+'/destination-card-'+width+'.png'})
  }
  await page.setViewportSize({width:1280,height:1000})
  await delivery.getByRole('button',{name:'Cambiar dirección',exact:true}).click()
  await delivery.getByLabel('Dirección guardada para cotizar').selectOption(String(first.id))
  await delivery.getByText('Total estimado:',{exact:false}).waitFor();assert.equal(estimates.at(-1).address_id,first.id)
  await delivery.getByLabel('Dirección guardada para cotizar').selectOption(String(second.id))
  await delivery.getByText('Total estimado:',{exact:false}).waitFor();assert.equal(estimates.at(-1).address_id,second.id)
  await page.goto(web+'/checkout')
  const selected=page.getByRole('button',{name:new RegExp(second.address)})
  await selected.waitFor();assert.equal(await selected.getAttribute('aria-pressed'),'true')
  await page.getByText('Envío al cliente:',{exact:false}).waitFor()
  const unchanged=(await(await page.request.get(api+'/ecommerce/cart',{headers})).json()).items
  assert.equal(unchanged.length,1);assert.equal(unchanged[0].quantity,1)
  await page.goto(product)
  await delivery.getByText('Total estimado:',{exact:false}).waitFor()
  await page.locator('header button[aria-haspopup="true"]').click();await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click()
  const keys=await page.evaluate(()=>Object.keys(sessionStorage))
  assert(!keys.some(k=>k.startsWith('delivery-checkout:')||(k.startsWith('tcc-checkout-destination:')&&!k.endsWith(':guest'))))
  const readsAfterLogout=addressReads
  await page.goto(product);await delivery.getByRole('button',{name:/Configurar ubicación|Cambiar ubicación/}).waitFor()
  assert.equal(await delivery.getByLabel('Dirección de entrega seleccionada').count(),0)
  assert(!(await delivery.innerText()).includes(second.address));assert.equal(addressReads,readsAfterLogout)
  assert.deepEqual(errors,[])
  console.log('PASS three real destination journeys: guest estimate/session/login/cart; no-address user creates inline with retained failed draft; default and session-selected addresses, recotation, unchanged default, checkout selection and logout privacy. PostgreSQL isolated; carrier/payment synthetic.')
 }finally{await page.request.get(api+'/__qa/stop').catch(()=>{});await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)})
