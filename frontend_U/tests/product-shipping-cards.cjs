// Browser fixtures only: no carrier, payment, customer or location-service requests.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const chooseLocation=require('./location-select.cjs')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(20000)
 const requests=[],errors=[];let configCalls=0,cityCalls=0,fail=false,defaultAddress=true,historyCode='11001000'
 page.on('pageerror',e=>errors.push(e.message))
 await page.routeWebSocket('**/ws/**',ws=>ws.close())
 await page.route('https://**',route=>route.abort())
 const products=[991,992].map(id=>({id,name:`Producto QA ${id}`,slug:`qa-${id}`,description:'QA',price:125000,category_id:1,brand_id:1,total_stock:20,is_available:true,rating:0,reviews_count:0,images:[],specifications:[],stock_entries:[]}))
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body={data:[]},status=200
  if(/\/products$/.test(path))body={data:products,total:2}
  else if(path.endsWith('/user/perfil'))body={id:998,nombre_completo:'Cliente QA',correo:'qa@example.invalid',telefono:'3000000000',estado:1,tipo_usuario:0}
  else if(path.endsWith('/user/addresses'))body={data:defaultAddress?[{id:77,label:'QA',is_default:true,tcc_city_code:'76001000',city:'CALI',department:'VALLE DEL CAUCA',recipient_name:'QA',phone:'3000000000',address:'Dirección sintética'}]:[]}
  else if(path.endsWith('/shipping/destination'))body={destination:historyCode?{code:historyCode}:null}
  else if(/\/products\/99[12]$/.test(path))body={data:products.find(p=>path.endsWith(String(p.id)))}
  else if(path.endsWith('/shipping/config')){configCalls++;body={enabled:true}}
  else if(path.endsWith('/shipping/cities')){cityCalls++;body=[{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'},{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'}]}
  else if(path.endsWith('/shipping/estimate')){
   const payload=route.request().postDataJSON();requests.push(payload)
   assert.deepEqual(Object.keys(payload).sort(),['force','items','tcc_city_code'])
   const rate=payload.tcc_city_code==='76001000'?30000:45000
   if(fail){status=503;body={error:'No fue posible calcular el envío en este momento.'}}
   else body={carrier:'TCC',total:String(rate),subtotal:'125000',order_total:String(125000+rate),tcc_rate:String(rate),surcharge:'0',approximate:true,expires_at:new Date(Date.now()+600000).toISOString()}
  }
  await route.fulfill({status,json:body})
 })
 try{
  await page.goto('http://crm.localhost/productos')
  const cards=page.getByLabel('Envío de este producto',{exact:true})
  await cards.first().waitFor()
  assert.equal(requests.length,0)
  await cards.first().getByRole('button',{name:'Configurar ubicación de entrega'}).click()
  await chooseLocation(page,'Departamento de entrega','VALLE DEL CAUCA')
  await chooseLocation(page,'Ciudad o municipio de entrega','76001000')
  await page.getByRole('button',{name:'Continuar viendo productos'}).click()
  await cards.first().getByText('Envío a CALI:',{exact:false}).waitFor()
  await cards.nth(1).scrollIntoViewIfNeeded()
  await cards.nth(1).getByText('Envío a CALI:',{exact:false}).waitFor()
  assert.equal(configCalls,1,'shared config request')
  assert.equal(await cards.getByText(/Total estimado:/).count(),2)
  assert(requests.every(p=>p.tcc_city_code==='76001000'))
  const before=requests.length
  await page.getByRole('link',{name:'Ver Producto QA 991',exact:true}).click()
  await page.getByText('Envío estimado:',{exact:false}).waitFor()
  await page.goBack()
  await cards.first().getByText('Envío a CALI:',{exact:false}).waitFor()
  assert.equal(requests.length,before+1,'listing cache reused; only detail requested')
  for(const width of [1280,768,390]){
   await page.setViewportSize({width,height:1200})
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`)
   if(process.env.QA_OUTPUT)await page.screenshot({path:`${process.env.QA_OUTPUT}/product-shipping-${width}.png`,animations:'disabled'})
  }
  await cards.first().getByRole('button',{name:/Cambiar ubicación/}).click()
  await chooseLocation(page,'Departamento de entrega','BOGOTA D.C.')
  await chooseLocation(page,'Ciudad o municipio de entrega','11001000')
  await page.getByRole('button',{name:'Continuar viendo productos'}).click()
  await cards.first().getByText('Envío a BOGOTA:',{exact:false}).waitFor()
  assert.equal(requests.at(-1).tcc_city_code,'11001000')
  assert(!(await cards.first().innerText()).includes('CALI:'))
  fail=true
  await page.reload()
  await cards.first().getByText('No fue posible calcular el envío en este momento.').waitFor()
  assert.equal(await cards.first().getByText(/Total estimado:/).count(),0)
  fail=false
  await cards.first().getByRole('button',{name:'Reintentar envío'}).click()
  await cards.first().getByText('Envío a BOGOTA:',{exact:false}).waitFor()
  // Automatic location priority is default address, validated history, session.
  await page.evaluate(()=>{
   localStorage.setItem('authToken',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`)
   localStorage.setItem('user',JSON.stringify({id:'998',name:'Cliente QA',email:'qa@example.invalid',role:'client'}))
   sessionStorage.setItem('tcc-checkout-destination:998',JSON.stringify({tcc_city_code:'11001000'}))
  })
  await page.reload()
  await cards.first().getByText('Envío a CALI:',{exact:false}).waitFor()
  defaultAddress=false
  await page.evaluate(()=>sessionStorage.setItem('tcc-checkout-destination:998',JSON.stringify({tcc_city_code:'76001000'})))
  await page.reload()
  await cards.first().getByText('Envío a BOGOTA:',{exact:false}).waitFor()
  historyCode=null
  await page.reload()
  await cards.first().getByText('Envío a CALI:',{exact:false}).waitFor()
  assert.deepEqual(errors,[])
  console.log('PASS product cards: default address > validated history > session, guest/manual persistence, shared config/location, lazy per-product quote, cross-card update, cache reuse, city invalidation, provider error/retry, no fake free rate, responsive 1280/768/390. Catalogue reads:',cityCalls)
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exit(1)})
