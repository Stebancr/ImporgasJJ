// Docker-only browser and real isolated Django/PostgreSQL. All external calls blocked.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const api='http://general-e2e-backend:8099'
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 const errors=[],carrierRequests=[]
 page.on('pageerror',error=>errors.push(error.message))
 page.on('request',request=>{if(/tcc|\/shipping\//i.test(request.url()))carrierRequests.push(request.url())})
 try{
  let state
  for(let attempt=0;attempt<60;attempt++){
   try{state=await(await page.request.get(api+'/__qa/state')).json();break}catch{await new Promise(resolve=>setTimeout(resolve,500))}
  }
  assert(state?.database_isolated)
  const login=await page.request.post(api+'/auth/token/',{data:{usuario:'general-e2e-client',password:'General-synthetic-fixture-only'}})
  assert.equal(login.status(),200)
  const token=await login.json(),headers={Authorization:'Bearer '+token.access}
  const profile=await(await page.request.get(api+'/user/perfil',{headers})).json()
  const user={id:String(profile.id),email:profile.correo,name:profile.nombre_completo,phone:profile.telefono,role:'client',is_active:true}
  assert.equal((await page.request.post(api+'/cart',{headers,data:{product_id:state.product_id,quantity:1}})).status(),201)
  await page.addInitScript(({token,user})=>{
   localStorage.setItem('authToken',token.access);localStorage.setItem('user',JSON.stringify(user))
   window.WidgetCheckout=class{constructor(options){window.__qaPayment=options}open(){}}
  },{token,user})
  await page.routeWebSocket('**/ws/**',ws=>ws.close())
  await page.route('https://**',route=>route.abort())
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url())
   await route.fulfill({response:await route.fetch({url:api+url.pathname.replace(/^\/api/,'')+url.search})})
  })
  await page.goto('http://crm.localhost/direcciones?nueva=1')
  const form=page.getByRole('form',{name:'Formulario de dirección de entrega'})
  await form.getByLabel('Departamento',{exact:true}).selectOption({label:'VALLE DEL CAUCA'})
  await form.getByLabel('Ciudad',{exact:true}).selectOption({label:'SANTIAGO DE CALI'})
  await form.getByLabel('Dirección',{exact:true}).fill('Calle sintética 123')
  await form.getByRole('button',{name:'Guardar dirección',exact:true}).click()
  await form.waitFor({state:'hidden'})
  const addresses=(await(await page.request.get(api+'/ecommerce/user/addresses',{headers})).json()).data
  assert.equal(addresses.length,1);assert.equal(addresses[0].city,'SANTIAGO DE CALI')
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:900})
   await page.goto('http://crm.localhost/carrito')
   await page.getByText('Producto general QA',{exact:true}).first().waitFor()
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`cart overflow ${width}`)
  }
  await page.goto('http://crm.localhost/checkout')
  await page.getByRole('button',{name:'Continuar al Pago',exact:true}).click()
  const intentPromise=page.waitForResponse(response=>response.url().endsWith('/orders')&&response.request().method()==='POST')
  await page.getByRole('button',{name:'Pagar con Wompi',exact:true}).click()
  const response=await intentPromise
  assert.equal(response.status(),201)
  const intent=(await response.json()).data
  assert.equal(Number(intent.subtotal),125000);assert.equal(Number(intent.shipping_cost),25000);assert.equal(Number(intent.total),150000)
  await page.waitForFunction(()=>window.__qaPayment?.amountInCents===15000000)
  assert.deepEqual(carrierRequests,[]);assert.deepEqual(errors,[])
  console.log('PASS dev: address persistence, cart desktop/tablet/mobile, checkout server tariff 25000, Wompi amount 15000000 cents, no carrier requests')
 }finally{await page.request.get(api+'/__qa/stop').catch(()=>{});await browser.close()}
})().catch(error=>{console.error(error.message);process.exit(1)})
