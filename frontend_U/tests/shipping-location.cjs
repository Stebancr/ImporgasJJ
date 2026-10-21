const chooseLocation=require('./location-select.cjs')
// Browser-only fixtures: no customer data, payment or carrier traffic.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage()
 const errors=[],requests=[]
  let fail=false,incomplete=false,noCoverage=false
 page.on('pageerror',e=>errors.push(e.message))
 await page.routeWebSocket('**/ws/**',ws=>ws.close())
 await page.route('https://**',route=>route.abort())
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body={data:[]},status=200
  if(path.endsWith('/products/991')||path.endsWith('/products/992'))body={data:{id:Number(path.split('/').at(-1)),name:'Producto QA',slug:'qa',description:'QA',price:125000,category_id:1,brand_id:1,total_stock:20,is_available:true,rating:0,reviews_count:0,images:[],specifications:[],stock_entries:[]}}
  else if(path.endsWith('/user/terms'))body={version:'qa'}
  else if(path.endsWith('/auth/token/'))body={access:'qa-synthetic',refresh:'qa-refresh',is_admin:0}
  else if(path.endsWith('/user/perfil'))body={id:998,nombre_completo:'Cliente QA',correo:'qa@example.invalid',telefono:'3000000000',estado:1,terms_version:'qa',current_terms_version:'qa',terms_accepted_at:new Date().toISOString()}
  else if(path.endsWith('/cart'))body={items:[]}
  else if(path.endsWith('/shipping/config'))body={enabled:true}
  else if(path.endsWith('/shipping/cities'))body=[{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'},{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'},{code:'76001000',city:'cali',department:'valle del cauca'}]
  else if(path.endsWith('/shipping/estimate')){
   const payload=route.request().postDataJSON();requests.push(payload)
   assert.deepEqual(Object.keys(payload).sort(),['force','items','tcc_city_code'])
   const subtotal=125000*payload.items[0].quantity
   if(noCoverage){status=503;body={error:'No hay cobertura para esta ruta.',code:'route_not_configured'}}
   else if(incomplete){status=400;body={error:'El envío de este producto aún no está disponible para calcular en línea.',code:'shipping_profile_incomplete'}}
   else if(fail){status=503;body={error:'No fue posible calcular el envío en este momento.'}}
   else body={carrier:'TCC',total:'30000',subtotal:String(subtotal),order_total:String(subtotal+30000),tcc_rate:'30000',surcharge:'0',approximate:true,expires_at:new Date(Date.now()+600000).toISOString()}
  }
  await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
 })
 try{
  await page.goto('http://crm.localhost/producto/991')
  await page.getByRole('button',{name:'Configurar ubicación de entrega'}).waitFor()
  assert.equal(requests.length,0)
  await page.getByText('Calcula el costo de entrega',{exact:true}).waitFor()
  await page.getByText('Precio del producto:',{exact:false}).waitFor()
  assert.equal(await page.getByLabel('Ciudad o municipio de entrega',{exact:true}).count(),0)
  await page.getByRole('button',{name:'Configurar ubicación de entrega'}).click()
  assert(await page.getByLabel('Ciudad o municipio de entrega',{exact:true}).isDisabled())
  assert.equal(await page.getByRole('region',{name:'Información de envío'}).getByRole('searchbox').count(),0)
  await page.getByRole('combobox',{name:'Departamento de entrega',exact:true}).click()
  const departmentNames=await page.getByRole('option').allTextContents()
  assert.equal(departmentNames.length,2)
  assert.deepEqual(departmentNames,[...departmentNames].sort((a,b)=>a.localeCompare(b,'es')))
  await page.getByRole('combobox',{name:'Departamento de entrega',exact:true}).fill('valle')
  assert.equal(await page.getByRole('option').count(),1)
  await page.keyboard.press('Escape')
  await chooseLocation(page,'Departamento de entrega','VALLE DEL CAUCA')
  await page.getByRole('combobox',{name:'Ciudad o municipio de entrega',exact:true}).fill('ca')
  assert.equal(await page.getByRole('option').count(),1)
  await page.keyboard.press('Escape')
  await page.getByRole('combobox',{name:'Ciudad o municipio de entrega',exact:true}).fill('ca')
  await page.getByRole('combobox',{name:'Ciudad o municipio de entrega',exact:true}).click()
  await page.getByRole('combobox',{name:'Ciudad o municipio de entrega',exact:true}).press('ArrowDown')
  await page.getByRole('combobox',{name:'Ciudad o municipio de entrega',exact:true}).press('Enter')
  await page.getByText('Total estimado:',{exact:false}).waitFor().catch(e=>{console.log('location_requests',requests.length,requests.at(-1)?.tcc_city_code);throw e})
  await page.goto('http://crm.localhost/producto/992')
  await page.getByText('Envío estimado:',{exact:false}).waitFor()
  assert.equal(requests.at(-1).items[0].product_id,992)
  await page.reload()
  await page.getByText('Envío estimado:',{exact:false}).waitFor()
  assert.equal(requests.at(-1).tcc_city_code,'76001000')
  assert.equal(await page.getByLabel('Ciudad o municipio de entrega',{exact:true}).count(),0)
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:1000})
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`)
  }
  await page.getByRole('button',{name:/Cambiar ubicación/}).click()
  fail=true
  await chooseLocation(page,'Departamento de entrega','BOGOTA D.C.')
  assert.equal(await page.getByLabel('Ciudad o municipio de entrega',{exact:true}).inputValue(),'')
  assert.equal(await page.getByText('Total estimado:',{exact:false}).count(),0)
  await chooseLocation(page,'Ciudad o municipio de entrega','11001000')
  await page.getByRole('alert').filter({hasText:'No fue posible calcular'}).waitFor()
  assert.equal(await page.getByText('Total estimado:',{exact:false}).count(),0)
  assert.equal(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('tcc-checkout-destination:guest')).tcc_city_code),'11001000')
  fail=false
  await page.getByRole('button',{name:'Reintentar cotización'}).click()
  await page.getByText('Total estimado:',{exact:false}).waitFor().catch(e=>{console.log('location_requests',requests.length,requests.at(-1)?.tcc_city_code);throw e})
  assert.equal(requests.at(-1).force,true)
  incomplete=true
  await page.getByRole('button',{name:'Calcular envío',exact:true}).click()
  await page.getByRole('link',{name:'Contactar a un asesor',exact:true}).waitFor()
  assert.equal(await page.getByRole('button',{name:'Reintentar cotización'}).count(),0)
  assert.equal(await page.getByText('Total estimado:',{exact:false}).count(),0)
  incomplete=false;noCoverage=true
  await page.getByRole('button',{name:'Calcular envío',exact:true}).click()
  await page.getByText('No hay cobertura para esta ruta.',{exact:true}).waitFor()
  assert.equal(await page.getByText('Total estimado:',{exact:false}).count(),0)
  noCoverage=false
  await page.goto('http://crm.localhost/login?mode=register&redirect=/producto/991')
  await page.locator('#customer-name').fill('Cliente QA')
  await page.locator('#customer-id').fill('9999999999')
  await page.locator('#customer-email').fill('qa@example.invalid')
  await page.locator('#customer-password').fill('Synthetic-QA-only-123')
  await page.locator('#customer-password-confirmation').fill('Synthetic-QA-only-123')
  await page.getByRole('checkbox').check()
  await page.getByRole('button',{name:'Crear Cuenta',exact:true}).click()
  await page.getByRole('link',{name:'Agregar dirección de entrega'}).waitFor()
  await page.getByRole('button',{name:'Ahora no, seguir navegando'}).click()
  assert.equal(await page.getByRole('link',{name:'Agregar dirección de entrega'}).count(),0)
  await page.reload()
  await page.getByRole('button',{name:'Agregar nueva dirección',exact:true}).waitFor()
  assert.equal(await page.getByRole('link',{name:'Agregar dirección de entrega'}).count(),0)
  assert.deepEqual(errors,[])
  console.log('PASS guest: unobtrusive location, auto quote, session persistence, manual destination, failure clears old price, controlled retry, responsive 1280/768/390; registration offers optional address, skip persists without blocking browsing. APIs mocked, no external requests.')
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)})
