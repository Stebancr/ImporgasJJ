// Real Django/PostgreSQL persistence in a disposable test database.
// Only the carrier, Wompi widget and signed payment events are synthetic.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
const {createHash}=require('node:crypto')
const api='http://tcc-e2e-backend:8099'
;(async()=>{
  const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
  const page=await browser.newPage()
  page.setDefaultTimeout(20000)
  const errors=[]
  page.on('pageerror',e=>errors.push(e.message))
  try{
    const initial=await (await page.request.get(api+'/__qa/state')).json()
    assert(initial.database_isolated)
    const login=await page.request.post(api+'/auth/token/',{data:{usuario:'tcc-e2e-client',password:'TCC-synthetic-fixture-only'}})
    assert.equal(login.status(),200)
    const tokens=await login.json(),headers={Authorization:'Bearer '+tokens.access}
    const profile=await (await page.request.get(api+'/user/perfil',{headers})).json()
    const cities=await (await page.request.get(api+'/shipping/cities')).json()
    const cali=cities.find(city=>city.code==='76001000')
    const address=await page.request.post(api+'/ecommerce/user/addresses',{headers,data:{label:'QA Cali',recipient_name:'Cliente QA',phone:'3000000000',
      address:'Dirección sintética Cali',city:cali.city,department:cali.department,tcc_city_code:cali.code,is_default:true}})
    assert.equal(address.status(),201,JSON.stringify(await address.json()))
    await page.addInitScript(({tokens,profile})=>{
      localStorage.setItem('authToken',tokens.access)
      localStorage.setItem('refreshToken',tokens.refresh)
      localStorage.setItem('user',JSON.stringify({id:String(profile.id),name:profile.nombre_completo,email:profile.correo,role:'client'}))
      window.WidgetCheckout=class{constructor(options){window.qaPayment=options}open(){}}
    },{tokens,profile})
    await page.routeWebSocket('**/ws/**',ws=>ws.close())
    await page.route('https://**',route=>route.abort())
    await page.route('**/api/**',async route=>{
      const url=new URL(route.request().url())
      const response=await route.fetch({url:api+url.pathname.replace(/^\/api/,'')+url.search})
      await route.fulfill({response})
    })
    await page.goto(`http://crm.localhost/producto/${initial.product_id}`)
    await page.getByLabel('Ciudad de entrega TCC').selectOption('11001000')
    await page.getByRole('button',{name:'Calcular envío',exact:true}).click()
    await page.getByText('Envío estimado:',{exact:false}).waitFor()
    await page.getByRole('button',{name:'Agregar al Carrito',exact:true}).click()
    await page.goto('http://crm.localhost/carrito')
    await page.getByText('Envío cotizado:',{exact:false}).waitFor()
    await page.getByRole('button',{name:'Aumentar cantidad'}).click()
    await page.getByText('Envío cotizado:',{exact:false}).waitFor()
    await page.getByLabel('Ciudad de entrega TCC').selectOption('11001000')
    await page.getByLabel('Dirección de entrega',{exact:true}).fill('Dirección sintética Bogotá')
    await page.getByText('Envío cotizado:',{exact:false}).waitFor()
    for(const width of [1280,390]){
      await page.setViewportSize({width,height:1000})
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`cart overflow ${width}`)
    }
    await page.getByRole('link',{name:'Proceder al Pago'}).click()
    await page.getByText('Tarifa TCC:',{exact:false}).waitFor()
    assert.equal(await page.getByLabel('Dirección',{exact:true}).inputValue(),'Dirección sintética Bogotá')
    await page.getByRole('button',{name:'Continuar al Pago'}).click()
    await page.getByRole('button',{name:'Pagar con Wompi',exact:true}).click()
    await page.waitForFunction(()=>window.qaPayment)
    const options=await page.evaluate(()=>window.qaPayment)
    assert.equal(options.amountInCents,28000000)
    const waiting=await (await page.request.get(api+'/__qa/state')).json()
    assert.equal(waiting.orders,1);assert.equal(waiting.dispatch_calls,0)
    const timestamp=1700000000
    const transaction={id:'TCC-E2E-SYNTHETIC',reference:options.reference,status:'APPROVED',amount_in_cents:options.amountInCents,currency:'COP'}
    const checksum=createHash('sha256').update(`${transaction.id}${transaction.status}${transaction.amount_in_cents}${timestamp}events-secret-for-tests`).digest('hex')
    const event={event:'transaction.updated',data:{transaction},timestamp,signature:{properties:['transaction.id','transaction.status','transaction.amount_in_cents'],checksum}}
    for(let i=0;i<2;i++)assert.equal((await page.request.post(api+initial.webhook_path,{data:event})).status(),200)
    const finished=await (await page.request.get(api+'/__qa/state')).json()
    assert.equal(finished.orders,1);assert.equal(finished.shipments,1);assert.equal(finished.dispatch_calls,1)
    assert.deepEqual(finished.waybills,['999000001'])
    assert.deepEqual(finished.rows.map(({id,...row})=>row),[{subtotal:'250000.00',shipping_cost:'30000.00',discounts:'0.00',taxes:'0.00',total:'280000.00',paid_total:'280000.00'}])
    const orders=await (await page.request.get(api+'/orders',{headers})).json()
    await page.goto('http://crm.localhost/pedido/'+orders.data[0].tracking_code)
    await page.getByText('Despacho creado',{exact:true}).waitFor()
    await page.getByRole('link',{name:'Rastrear en TCC'}).waitFor()
    assert.deepEqual(errors,[])
    console.log('PASS full Docker flow: real login/address/cart/quote/order PostgreSQL persistence; product estimate; quantity/city invalidation; checkout destination; Wompi 280000 COP; verified duplicate event; one order/guide/dispatch; visible customer tracking link; responsive. Carrier/payment simulated; no production data or real charges.')
  }finally{
    await page.request.get(api+'/__qa/stop').catch(()=>{})
    await browser.close()
  }
})().catch(e=>{console.error(e);process.exit(1)})
