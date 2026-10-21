const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 const now=new Date().toISOString();let failConfig=true
 const product={id:991,name:'QA',price:125000,is_available:true,total_stock:20,images:[],brand_name:'QA',category_name:'QA'}
 const address={id:77,label:'QA',recipient_name:'QA',phone:'3000000000',address:'QA street',city:'BOGOTA',department:'BOGOTA D.C.',tcc_city_code:'11001000',is_default:true}
 await page.addInitScript(()=>{localStorage.setItem('authToken',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`);localStorage.setItem('user',JSON.stringify({id:'998',name:'QA',email:'qa@example.invalid',role:'client'}))})
 await page.routeWebSocket('**/ws/**',ws=>ws.close())
 await page.route('https://**',route=>route.abort())
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body={data:[]},status=200
  if(path.endsWith('/user/perfil'))body={id:998,nombre_completo:'QA',correo:'qa@example.invalid',telefono:'3000000000',estado:1,terms_version:'qa',current_terms_version:'qa',terms_accepted_at:now}
  else if(path.endsWith('/cart'))body={items:[{product_id:991,quantity:1}]}
  else if(path.endsWith('/products/991'))body={data:product}
  else if(path.endsWith('/user/addresses'))body={data:[address]}
  else if(path.endsWith('/shipping/config')){body=failConfig?{error:'Configuración temporalmente no disponible'}:{enabled:true};status=failConfig?503:200}
  else if(path.endsWith('/shipping/cities'))body=[{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'}]
  else if(path.endsWith('/shipping/destination'))body={destination:null}
  else if(path.endsWith('/shipping/quote')||path.endsWith('/shipping/estimate'))body={id:'00000000-0000-4000-8000-000000000001',total:'32000',subtotal:'125000',order_total:'157014',discounts:'5',taxes:'19',tcc_rate:'32000',surcharge:'0',package_count:1,real_kg:'2',volumetric_kg:'0.4',billable_kg:'2',expires_at:new Date(Date.now()+600000).toISOString()}
  await route.fulfill({status,json:body})
 })
 try{
  await page.goto('http://crm.localhost/carrito')
  await page.getByRole('alert').filter({hasText:/configuración|configuracion|transporte/i}).waitFor()
  await page.getByText('Pendiente de cotización',{exact:true}).waitFor()
  failConfig=false
  await page.goto('http://crm.localhost/checkout')
  await page.getByText('Costo de envío',{exact:true}).waitFor()
  for(const [label,value] of [['Descuentos adicionales','5'],['Impuestos adicionales','19']]){
   const row=page.getByText(label,{exact:true}).locator('..')
   await row.getByText(new RegExp(value)).waitFor()
  }
  await page.goto('http://crm.localhost/carrito')
  await page.getByText('Descuentos adicionales',{exact:true}).waitFor()
  await page.getByText('Impuestos adicionales',{exact:true}).waitFor()
  assert(!/env[ií]o gratis|envio gratis|500\.000/.test((await page.locator('body').innerText()).toLowerCase()))
  assert.deepEqual(errors,[])
  console.log('PASS restored cart configuration error and pending total; quoted checkout taxes/discounts; cart breakdown; no free-shipping promotion; requests intercepted')
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)})