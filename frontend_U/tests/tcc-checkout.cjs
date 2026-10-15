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
  let failQuote=false,quoteCount=0,profileSaves=0,retries=0
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
    else if(path.endsWith('/user/addresses'))body={data:[address]}
    else if(path.endsWith('/shipping/config'))body={enabled:true,tracking_api_available:false}
    else if(path.endsWith('/shipping/cities'))body=[{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'},{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'}]
    else if(path.endsWith('/shipping/quote')){
      const payload=route.request().postDataJSON();quotes.push(payload)
      assert(!('token' in payload));assert.equal(payload.items[0].product_id,991)
      quoteCount++
      if(failQuote){status=503;body={error:'No hay tarifa de prueba para esta ruta'}}
      else body={id:`00000000-0000-4000-8000-${String(quoteCount).padStart(12,'0')}`,carrier:'TCC',tcc_rate:'30000.00',surcharge:'2000.00',total:'32000.00',subtotal:'125000.00',order_total:'157000.00',package_count:1,real_kg:'2',volumetric_kg:'0.4',billable_kg:'2',expires_at:new Date(Date.now()+600000).toISOString()}
    }else if(path.endsWith('/orders')&&route.request().method()==='POST'){
      const payload=route.request().postDataJSON();orders.push(payload)
      assert(payload.shipping_quote_id);assert(!('shipping_cost' in payload))
      body={data:{wompi_public_key:'pub_test_synthetic',tracking_code:'qa',wompi_reference:payload.wompi_reference,wompi_signature:'a'.repeat(64),total:'157000.00',payment_status:'PENDING'}}
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
    await page.getByText('Tarifa TCC:',{exact:false}).waitFor().catch(async e=>{console.log('URL',page.url(),'BODY',(await page.locator('body').innerText()).slice(0,2200),'QUOTES',quotes);throw e})
    assert.equal(quotes.at(-1).address_id,77)
    assert.equal(quotes.at(-1).tcc_city_code,'11001000')
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`checkout overflow ${width}`)
  }
  await page.getByLabel('Ciudad de entrega TCC').selectOption('76001000')
  await page.getByText('Tarifa TCC:',{exact:false}).waitFor()
  assert.equal(quotes.at(-1).tcc_city_code,'76001000')
  assert.equal(quotes.at(-1).address_id,null)
  failQuote=true
  await page.getByRole('button',{name:'Volver a cotizar'}).click()
  await page.getByRole('alert').filter({hasText:'No hay tarifa de prueba'}).waitFor()
  assert(await page.getByRole('button',{name:'Continuar al Pago'}).isDisabled())
  failQuote=false
  await page.getByRole('button',{name:'Volver a cotizar'}).click()
  await page.getByText('Tarifa TCC:',{exact:false}).waitFor()
  assert.equal(quotes.at(-1).force,true)
  await page.getByRole('button',{name:'Continuar al Pago'}).click()
  await page.getByRole('button',{name:'Pagar con Wompi',exact:true}).click()
  await page.waitForFunction(()=>window.qaPayment)
  assert.equal((await page.evaluate(()=>window.qaPayment)).amountInCents,15700000)
  assert.equal(orders.length,1)
  assert.equal(orders[0].city,'CALI')
  assert.equal(orders[0].department,'VALLE DEL CAUCA')
  assert.equal(orders[0].complement,'Apto QA')
  assert.equal(alerts.length,0)
  await page.goto('http://crm.localhost/pedido/qa')
  await page.getByText('Despacho creado',{exact:true}).waitFor()
  assert.equal(await page.getByRole('link',{name:'Rastrear en TCC'}).getAttribute('href'),shipment.tracking_url)
  await page.getByText('TCC confirmó la creación del despacho.',{exact:false}).waitFor()
  assert.equal(await page.getByText('Cuenta:',{exact:false}).count(),0)
  for(const width of [1280,768,390]){
    await page.setViewportSize({width,height:1000})
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`order overflow ${width}`)
  }
  await page.setViewportSize({width:1280,height:1000})
  await page.goto('http://crm.localhost/admin/productos')
  await page.getByRole('button',{name:'Editar',exact:true}).click()
  await page.getByLabel('Peso por paquete (kg)',{exact:true}).fill('3.200')
  await page.getByRole('button',{name:'Guardar cambios',exact:true}).click()
  await page.waitForFunction(()=>!document.querySelector('[role="dialog"]'))
  assert.equal(profileSaves,1)
  await page.reload()
  await page.getByRole('button',{name:'Editar',exact:true}).click()
  assert.equal(await page.getByLabel('Peso por paquete (kg)',{exact:true}).inputValue(),'3.200')
  for(const width of [1280,768,390]){
    await page.setViewportSize({width,height:1000})
    // Radix reserves scrollbar space on the locked background. Check the
    // visible dialog/fields, independently of the background table scroll area.
    assert(await page.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth && el.getBoundingClientRect().right<=innerWidth),`product shipping dialog overflow ${width}`)
  }
  Object.assign(shipment,{state:'error',state_label:'Error de creación',account_type:'MSJ',account:'5625200',environment:'development',
    real_kg:'2',volumetric_kg:'0.4',billable_kg:'2',tcc_rate:'30000',surcharge:'2000',charged:'32000',retry_allowed:true,last_error:'Error de prueba controlado',documents:{label:'https://testsomos.tcc.com.co/qa.pdf'}})
  await page.goto('http://crm.localhost/admin/ordenes')
  await page.getByRole('button',{name:'Ver detalle',exact:true}).click()
  await page.getByText('Error de prueba controlado',{exact:true}).waitFor()
  await page.getByRole('button',{name:'Reintentar creación en TCC'}).click()
  await page.getByText('Despacho creado',{exact:true}).waitFor()
  assert.equal(retries,1)
  assert.equal(await page.getByRole('link',{name:'Etiqueta TCC'}).getAttribute('href'),'https://testsomos.tcc.com.co/qa.pdf')
  assert.deepEqual(errors,[])
  console.log('PASS TCC browser: saved address, changed city, canonical department, error blocks payment, forced refresh, quote ID, server Wompi total, customer shipment/history/link, admin product profile save/reload, admin shipment retry/document, responsive 1280/768/390. All APIs mocked.')
  await browser.close()
})().catch(e=>{console.error(e);process.exit(1)})
