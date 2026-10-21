const chooseLocation=require('./location-select.cjs')
// Browser fixtures only. All API/payment requests are intercepted; no real sends.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
const now = new Date().toISOString()
const product = {id:991,name:'Producto transporte QA',slug:'qa',description:'QA',price:125000,
  category_id:1,category_name:'QA',brand_id:1,brand_name:'QA',total_stock:20,is_available:true,
  rating:0,reviews_count:0,images:[],specifications:[],stock_entries:[],
  shipping_profile:{requires_shipping:true,weight_kg:'2.000',height_cm:'10.00',width_cm:'10.00',length_cm:'10.00',packages_per_unit:1,declared_value:'125000.00',packaging_code:'CLEM_CAJA',fragile:false}}
const address = {id:77,label:'Dirección QA',recipient_name:'Cliente QA',phone:'3000000000',
  address:'Dirección sintética QA',city:'BOGOTA',department:'BOGOTA D.C.',postal_code:'',is_default:true,
  tcc_city_code:'11001000',complement:'Apto QA',neighborhood:'QA',delivery_instructions:'QA'}
;(async()=>{
  const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
  const page=await browser.newPage()
  page.setDefaultTimeout(15000)
  const errors=[],quotes=[],orders=[],alerts=[]
  let failPayment=false,failQuote=false,changedRate=false,quoteCount=0,profileSaves=0,retries=0
  const shipment={id:1,carrier:'TCC',state:'created',state_label:'Despacho creado',waybill:'123456789',last_update:now,last_sync_at:now,
    tracking_url:'https://www.tcc.com.co/rastreo?tipo=RE&documento=123456789',tracking_api_available:false,
    history:[{state:'created',description:'TCC confirmó la creación del despacho.',created_at:now}]}
  const order={id:11,order_number:'QA-11',customer_name:'Cliente QA',customer_email:'qa@example.invalid',customer_phone:'3000000000',
    shipping_address:address.address,city:address.city,department:address.department,postal_code:'',subtotal:'125000',shipping_cost:'32000',
    total:'157000',status:'paid',payment_method:'wompi',wompi_status:'APPROVED',tracking_code:'qa',items:[],tracking_history:[],created_at:now,updated_at:now,shipment}
  page.on('pageerror',e=>errors.push(e.message))
  page.on('dialog',async d=>{alerts.push(d.message());await d.dismiss()})
  await page.addInitScript(()=>{
    localStorage.setItem('authToken',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`)
    localStorage.setItem('user',JSON.stringify({id:'998',name:'Cliente QA',email:'qa@example.invalid',role:'client'}))
    localStorage.setItem('token',localStorage.getItem('authToken'))
    window.WidgetCheckout=class {constructor(options){window.qaPayment=options}open(){}}
  })
  await page.routeWebSocket('**/ws/**',ws=>ws.close())
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname
    let body={data:[]},status=200
    if(path.endsWith('/user/perfil'))body={id:998,tipo_usuario:4,nombre_completo:'Cliente QA',correo:'qa@example.invalid',telefono:'3000000000',estado:1,terms_version:'qa',current_terms_version:'qa',terms_accepted_at:now}
    else if(path.endsWith('/cart'))body={items:[{product_id:991,quantity:1}]}
    else if(path.endsWith('/products/991/editor')){
      const multipart=route.request().postData()
      const payload=JSON.parse(multipart.split('\r\n\r\n')[1].split('\r\n--')[0])
      product.shipping_profile=payload.product.shipping_profile
      assert.equal(product.shipping_profile.weight_kg,'3.200');profileSaves++
      body={data:product}
    }
    else if(path.endsWith('/products/991')){
      if(['PATCH','PUT'].includes(route.request().method())){
        product.shipping_profile=route.request().postDataJSON().shipping_profile
        assert.equal(product.shipping_profile.weight_kg,'3.200');profileSaves++
      }
      body={data:product}
    }
    else if(path.endsWith('/products'))body={data:[product],total:1,total_pages:1}
    else if(path.endsWith('/categories'))body={data:[{id:1,name:'QA',slug:'qa'}]}
    else if(path.endsWith('/brands'))body={data:[{id:1,name:'QA',slug:'qa'}]}
    else if(path.endsWith('/user/addresses'))body={data:[address,{...address,id:78,label:'Otra dirección QA',address:'Segunda dirección sintética',city:'CALI',department:'VALLE DEL CAUCA',tcc_city_code:'76001000',is_default:false}]}
    else if(path.endsWith('/shipping/config'))body={enabled:true,tracking_api_available:false}
    else if(path.endsWith('/shipping/cities'))body=[{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'},{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'}]
    else if(path.endsWith('/shipping/quote')){
      const payload=route.request().postDataJSON();quotes.push(payload)
      assert(!('token' in payload));assert.equal(payload.items[0].product_id,991)
      quoteCount++
      if(failQuote){status=503;body={error:'No hay tarifa de prueba para esta ruta'}}
      else body={id:`00000000-0000-4000-8000-${String(quoteCount).padStart(12,'0')}`,carrier:'TCC',tcc_rate:changedRate?'32000.00':'30000.00',surcharge:'2000.00',total:changedRate?'34000.00':'32000.00',subtotal:'125000.00',order_total:changedRate?'159000.00':'157000.00',package_count:1,real_kg:'2',volumetric_kg:'0.4',billable_kg:'2',expires_at:new Date(Date.now()+600000).toISOString()}
    }else if(path.endsWith('/orders')&&route.request().method()==='POST'){
      const payload=route.request().postDataJSON();orders.push(payload)
      assert(payload.shipping_quote_id);assert(!('shipping_cost' in payload))
      if(failPayment){failPayment=false;return route.fulfill({status:503,json:{error:'Fallo temporal de pago QA'}})}
      body={data:{wompi_public_key:'pub_test_synthetic',tracking_code:'qa',wompi_reference:payload.wompi_reference,wompi_signature:'a'.repeat(64),total:changedRate?'159000.00':'157000.00',payment_status:'PENDING'}}
    }else if(path.endsWith('/orders/tracking/qa'))body={data:order}
    else if(path.endsWith('/ecommerce/admin/orders'))body={data:[order],total:1,total_pages:1}
    else if(path.endsWith('/ecommerce/admin/orders/11'))body={data:order}
    else if(path.endsWith('/shipping/orders/11/retry')){
      retries++;shipment.state='created';shipment.state_label='Despacho creado';shipment.retry_allowed=false
      status=202;body={state:'pending'}
    }
    await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
  })
  for(const width of [1280,768,390]){
    await page.setViewportSize({width,height:1000})
    await page.goto('http://crm.localhost/checkout')
    await page.getByText(/157[.,]000/).first().waitFor()
    assert.equal(quotes.at(-1).address_id,77)
    assert.equal(await page.getByLabel('Departamento de entrega',{exact:true}).count(),0,'Authenticated checkout must use persisted addresses')
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`checkout overflow ${width}`)
  }
  await page.getByRole('button').filter({hasText:'Segunda dirección sintética'}).click()
  await page.getByText(/157[.,]000/).first().waitFor()
  await page.waitForTimeout(100)
  assert.equal(quotes.at(-1).address_id,78)
  assert.equal(quotes.at(-1).tcc_city_code,'76001000')
  failQuote=true
  await page.getByRole('button',{name:'Volver a cotizar'}).click()
  await page.getByRole('alert').filter({hasText:'El servicio no está disponible temporalmente.'}).waitFor()
  assert(await page.getByRole('button',{name:'Continuar al Pago'}).isDisabled())
  failQuote=false;changedRate=true
  await page.getByRole('button',{name:'Volver a cotizar'}).click()
  await page.getByText(/159[.,]000/).first().waitFor()
  assert.equal(quotes.at(-1).address_id,78)
  await page.getByRole('button',{name:'Continuar al Pago'}).click()
  failPayment=true
  await page.getByRole('button',{name:'Pagar con Wompi'}).click()
  await page.getByRole('alert').filter({hasText:'El servicio no está disponible temporalmente.'}).waitFor()
  const reference=orders.at(-1).wompi_reference
  await page.getByRole('button',{name:'Pagar con Wompi'}).click()
  await page.waitForFunction(()=>!!window.qaPayment)
  assert.equal(orders.at(-1).wompi_reference,reference,'Payment retry retains idempotency reference')
  assert.equal(orders.at(-1).address_id,78)
  assert(!('shipping_cost' in orders.at(-1)))
  assert.deepEqual(errors,[])
  console.log('PASS TCC checkout: persisted/default/alternative address, independent re-quotation, changed rate, provider failure blocks payment, payment retry/idempotency, no client shipping charge, responsive. Full subsidy and webhook persistence are covered by shipping-subsidy-live.cjs.')
  await browser.close()
})().catch(e=>{console.error(e);process.exit(1)})
