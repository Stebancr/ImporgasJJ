// Real isolated Django/PostgreSQL. TCC/Wompi transport are intercepted, never live.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict'),crypto=require('node:crypto')
const api=process.env.QA_API_URL,web=process.env.QA_WEB_URL||'http://crm.localhost'
;(async()=>{
 assert(api,'Requires isolated QA fixture')
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(20000)
 const errors=[];page.on('pageerror',error=>errors.push(error.message))
 try{
  let state
  for(let n=0;n<60;n++){try{const r=await page.request.get(api+'/__qa/state',{timeout:1000});if(r.ok()){state=await r.json();break}}catch{}await page.waitForTimeout(500)}
  assert(state?.database_isolated)
  const login=async usuario=>{
   const response=await page.request.post(api+'/auth/token/',{data:{usuario,password:'TCC-synthetic-fixture-only'}})
   assert.equal(response.status(),200);return response.json()
  }
  const tokens=await login('tcc-e2e-client'),admin=await login('tcc-e2e-admin')
  const headers={Authorization:'Bearer '+tokens.access},adminHeaders={Authorization:'Bearer '+admin.access}
  const profile=await(await page.request.get(api+'/user/perfil',{headers})).json()
  const cities=await(await page.request.get(api+'/shipping/cities')).json(),cali=cities.find(c=>c.code==='76001000')
  const saved=await page.request.post(api+'/ecommerce/user/addresses',{headers,data:{label:'QA subsidio',recipient_name:'QA',phone:'3000000000',address:'Dirección sintética QA',city:cali.city,department:cali.department,tcc_city_code:cali.code,is_default:true}})
  assert.equal(saved.status(),201)
  const address=(await saved.json()).data
  assert.equal((await page.request.post(api+'/ecommerce/cart',{headers,data:{product_id:state.product_id,quantity:1}})).status(),201)
  await page.addInitScript(({tokens,profile})=>{
   localStorage.setItem('authToken',tokens.access);localStorage.setItem('refreshToken',tokens.refresh)
   localStorage.setItem('user',JSON.stringify({id:String(profile.id),name:profile.nombre_completo,email:profile.correo,role:'client'}))
   window.WidgetCheckout=class{constructor(options){window.qaPayment=options}open(){}}
  },{tokens,profile})
  await page.route('https://**',route=>route.abort());await page.routeWebSocket('**/ws/**',socket=>socket.close())
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url())
   try{const response=await route.fetch({url:api+url.pathname.replace(/^\/api/,'')+url.search});await route.fulfill({response})}catch{await route.abort().catch(()=>{})}
  })
  const delivery=page.getByRole('region',{name:'Información de envío'})
  for(const [price,free] of [['1999999',false],['2000000',true],['2100000',true]]){
   const update=await page.request.patch(api+'/ecommerce/products/'+state.product_id,{headers:adminHeaders,data:{price}})
   assert.equal(update.status(),200,JSON.stringify(await update.json()))
   await page.goto(web+'/producto/'+state.product_id)
   await delivery.getByText('Total estimado:',{exact:false}).waitFor()
   assert.equal(await delivery.getByRole('button',{name:'Configurar ubicación de entrega'}).count(),0)
   if(free)await delivery.getByText('ImporGas JJ asume el costo de la entrega.').waitFor()
   else{assert(!(await delivery.innerText()).includes('ImporGas JJ asume'));await delivery.getByText(/Agrega \$\s*1 más/).waitFor()}
   await page.goto(web+'/carrito')
   await page.getByText(free?'Envío: Gratis':/Costo de envío:\s*\$\s*30\.000/,{exact:true}).waitFor()
   if(free)await page.getByText(/Ahorro en envío:\s*\$\s*30\.000/).first().waitFor()
  }
  // Set exact inclusive boundary for the actual simulated payment.
  assert.equal((await page.request.patch(api+'/ecommerce/products/'+state.product_id,{headers:adminHeaders,data:{price:'2000000'}})).status(),200)
  await page.goto(web+'/')
  await page.getByText(/Envío gratis en compras desde\s*\$\s*2\.000\.000/).waitFor()
  await page.goto(web+'/checkout')
  await page.getByText('Envío al cliente: Gratis',{exact:true}).waitFor()
  for(const width of [1280,768,390]){await page.setViewportSize({width,height:1000});await page.waitForFunction(()=>document.documentElement.scrollWidth<=window.innerWidth)}
  await page.getByRole('button',{name:'Continuar al Pago',exact:true}).click()
  await page.reload();await page.getByRole('heading',{name:'Método de Pago'}).waitFor()
  await page.getByText('Envío al cliente: Gratis',{exact:true}).waitFor()
  await page.getByRole('button',{name:'Pagar con Wompi',exact:true}).click()
  await page.waitForFunction(()=>window.qaPayment)
  const options=await page.evaluate(()=>window.qaPayment)
  assert.equal(options.amountInCents,200000000)
  state=await(await page.request.get(api+'/__qa/state')).json()
  assert.equal(state.orders,1);assert.equal(state.dispatch_calls,0)
  assert.deepEqual(state.shipping_accounting,[{carrier_shipping_cost:'30000.00',shipping_cost:'0.00',shipping_discount:'30000.00',free_shipping_applied:true,free_shipping_threshold:'2000000.00'}])
  const tx={id:'QA-SUBSIDY-TX',reference:options.reference,status:'APPROVED',amount_in_cents:options.amountInCents,currency:'COP'},timestamp=1700000000
  const checksum=crypto.createHash('sha256').update(`${tx.id}${tx.status}${tx.amount_in_cents}${timestamp}events-secret-for-tests`).digest('hex')
  const event={event:'transaction.updated',data:{transaction:tx},timestamp,signature:{properties:['transaction.id','transaction.status','transaction.amount_in_cents'],checksum}}
  for(let i=0;i<2;i++)assert.equal((await page.request.post(api+state.webhook_path,{data:event})).status(),200)
  state=await(await page.request.get(api+'/__qa/state')).json()
  assert.equal(state.orders,1);assert.equal(state.dispatch_calls,1);assert.equal(state.shipments,1)
  assert.equal(state.rows[0].paid_total,'2000000.00')
  const orders=(await(await page.request.get(api+'/ecommerce/admin/orders',{headers:adminHeaders})).json()).data
  assert.equal(orders[0].delivery_address,address.id)
  assert.equal(orders[0].shipment.tcc_rate,'30000.00');assert.equal(orders[0].shipment.shipping_discount,'30000.00')
  assert.deepEqual(errors,[])
  console.log('PASS subsidy E2E: 1999999/2000000/2100000; product/cart/home/checkout; responsive; persisted address; Wompi 2000000; carrier 30000/customer 0/subsidy 30000; duplicate webhook one order/guide; PostgreSQL isolated, provider/payment synthetic.')
 }finally{await page.request.get(api+'/__qa/stop').catch(()=>{});await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)})
