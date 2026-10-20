// Docker-only, disposable Django/PostgreSQL database. No real carrier calls.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const api='http://tcc-e2e-backend:8099'
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(20000)
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 page.on('response',async response=>{if(response.url().endsWith('/editor')) console.log('EDITOR',response.status(),response.status()>=400?await response.text():'saved')})
 let fail=false
 try{
  assert((await (await page.request.get(api+'/__qa/state')).json()).database_isolated)
  const login=await page.request.post(api+'/auth/token/',{data:{usuario:'tcc-e2e-admin',password:'TCC-synthetic-fixture-only'}})
  assert.equal(login.status(),200)
  const tokens=await login.json(),headers={Authorization:'Bearer '+tokens.access}
  await page.addInitScript(tokens=>localStorage.setItem('token',tokens.access),tokens)
  await page.routeWebSocket('**/ws/**',ws=>ws.close())
  await page.route('https://**',route=>route.abort())
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url())
   if(fail && url.pathname.endsWith('/editor')){fail=false;return route.fulfill({status:503,json:{detail:'QA unavailable'}})}
   try{await route.fulfill({response:await route.fetch({url:api+url.pathname.replace(/^\/api/,'')+url.search})})}catch{await route.abort().catch(()=>{})}
  })
  await page.goto('http://crm.localhost/admin/productos')
  await page.getByRole('button',{name:'Agregar Producto',exact:true}).click()
  const dialog=page.getByRole('dialog')
  await dialog.getByRole('button',{name:'Crear producto',exact:true}).click()
  await dialog.getByText('Escribe el nombre del producto.',{exact:true}).first().waitFor()
  await dialog.getByLabel('Nombre del producto *',{exact:true}).fill('Editor completo QA')
  await dialog.getByLabel('Precio *',{exact:true}).fill('123000')
  const selects=dialog.getByRole('combobox')
  await selects.nth(0).click();await page.getByRole('option',{name:'QA',exact:true}).click()
  await selects.nth(1).click();await page.getByRole('option',{name:'QA',exact:true}).click()
  for(const label of ['Peso por paquete (kg)','Alto por paquete (cm)','Ancho por paquete (cm)','Largo por paquete (cm)']) await dialog.getByLabel(label,{exact:true}).fill('10')
  assert(await dialog.getByLabel('Usar el precio de venta como valor declarado').isChecked())
  const png=await page.screenshot({clip:{x:0,y:0,width:4,height:4}})
  await dialog.locator('input[type=file]').setInputFiles([{name:'first.png',mimeType:'image/png',buffer:png},{name:'second.png',mimeType:'image/png',buffer:png}])
  await dialog.getByLabel('Usar imagen 2 como principal',{exact:true}).click()
  await dialog.getByLabel('Descripción de imagen 2',{exact:true}).fill('Principal QA')
  fail=true
  await dialog.getByRole('button',{name:'Crear producto',exact:true}).click()
  await dialog.getByText(/No se pudo confirmar el guardado/).waitFor()
  assert.equal(await dialog.getByLabel('Nombre del producto *',{exact:true}).inputValue(),'Editor completo QA')
  await dialog.getByRole('button',{name:'Crear producto',exact:true}).click()
  await dialog.waitFor({state:'hidden'})
  const list=await (await page.request.get(api+'/products?search=Editor%20completo%20QA',{headers})).json()
  assert.equal(list.data.length,1)
  const id=list.data[0].id
  let stored=(await (await page.request.get(api+'/products/'+id,{headers})).json()).data
  assert.equal(stored.images.length,2);assert.equal(stored.images.filter(image=>image.is_primary).length,1)
  assert.equal(stored.images.find(image=>image.is_primary).alt_text,'Principal QA')
  await page.getByRole('row').filter({hasText:'Editor completo QA'}).getByRole('button',{name:'Editar',exact:true}).click()
  await dialog.getByLabel('Usar imagen 2 como principal',{exact:true}).waitFor()
  assert.equal(await dialog.getByLabel('Usar imagen 2 como principal',{exact:true}).getAttribute('aria-pressed'),'true')
  await dialog.getByLabel('Eliminar imagen 2',{exact:true}).click()
  await dialog.getByLabel('Precio *',{exact:true}).fill('124000')
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:900})
   assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth&&el.getBoundingClientRect().right<=innerWidth),`overflow ${width}`)
   if(process.env.QA_OUTPUT) await page.screenshot({path:`${process.env.QA_OUTPUT}/product-editor-${width}.png`})
  }
  await dialog.getByRole('button',{name:'Guardar cambios',exact:true}).click()
  await dialog.waitFor({state:'hidden'})
  stored=(await (await page.request.get(api+'/products/'+id,{headers})).json()).data
  assert.equal(stored.price,'124000.00');assert.equal(stored.images.length,1);assert(stored.images[0].is_primary)
  assert(stored.shipping_profile.declared_value_from_price)
  await page.getByRole('row').filter({hasText:'Editor completo QA'}).getByRole('button',{name:'Editar',exact:true}).click()
  assert.equal(await dialog.getByLabel('Precio *',{exact:true}).inputValue(),'124000.00')
  await dialog.getByRole('button',{name:'Cancelar',exact:true}).click()
  await dialog.getByRole('button',{name:'Seguir editando',exact:true}).click()
  assert.equal(await dialog.count(),1)
  assert.deepEqual(errors,[])
  console.log('PASS real PostgreSQL: create, validation, images, primary, retained failure/retry, reopen, edit/delete primary, responsive, cancel protection')
 }finally{await page.request.get(api+'/__qa/stop').catch(()=>{});await browser.close()}
})().catch(error=>{console.error(error.message);process.exit(1)})
