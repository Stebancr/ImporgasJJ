const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const choose=require('./location-select.cjs')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 let failAddresses=true;const calls={addresses:0,config:0,cities:0,estimate:0}
 await page.addInitScript(()=>{
  localStorage.setItem('authToken',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`)
  localStorage.setItem('user',JSON.stringify({id:'stale-browser-id',name:'QA',email:'qa@example.invalid',role:'client'}))
 })
 await page.routeWebSocket('**/ws/**',s=>s.close());await page.route('https://**',r=>r.abort())
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;let status=200,body={data:[]}
  if(path.endsWith('/user/perfil'))body={id:998,nombre_completo:'QA',correo:'qa@example.invalid',estado:1}
  else if(path.endsWith('/products/991'))body={data:{id:991,name:'QA',slug:'qa',description:'QA',price:125000,category_id:1,brand_id:1,total_stock:20,is_available:true,rating:0,reviews_count:0,images:[],shipping_ready:true}}
  else if(path.endsWith('/cart'))body={items:[]}
  else if(path.endsWith('/shipping/config')){calls.config++;body={enabled:true}}
  else if(path.endsWith('/shipping/cities')){calls.cities++;body=[{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'}]}
  else if(path.endsWith('/user/addresses')){calls.addresses++;if(failAddresses){status=503;body={error:'Synthetic unavailable'}}}
  else if(path.endsWith('/shipping/estimate')){calls.estimate++;body={total:'30000',subtotal:'125000',order_total:'155000',approximate:true,tcc_rate:'30000',surcharge:'0',expires_at:new Date(Date.now()+600000).toISOString()}}
  await route.fulfill({status,json:body})
 })
 try{
  await page.goto('http://crm.localhost/producto/991')
  const block=page.getByRole('region',{name:'Información de envío'})
  await block.getByText('No fue posible cargar tus direcciones.',{exact:false}).waitFor()
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('user')).id),'998')
  assert.equal(await block.getByText('Todavía no tienes una dirección de entrega',{exact:false}).count(),0)
  const before={...calls};failAddresses=false
  await block.getByRole('button',{name:'Reintentar direcciones'}).click()
  await block.getByText('Todavía no tienes una dirección de entrega',{exact:false}).waitFor()
  assert.equal(calls.addresses,before.addresses+1);assert.equal(calls.config,before.config);assert.equal(calls.cities,before.cities)
  assert.equal(calls.estimate,0)
  assert.equal(await block.getByRole('button',{name:'Configurar ubicación de entrega'}).count(),0)
  await block.getByRole('button',{name:'Agregar nueva dirección'}).click()
  await page.getByRole('form',{name:'Formulario de dirección de entrega'}).waitFor()
  await page.getByRole('button',{name:'Cancelar',exact:true}).click()
  assert.equal(calls.estimate,0)
  const stable={...calls};await page.waitForTimeout(800);assert.deepEqual(calls,stable)
  console.log('PASS address load failure is separate from empty addresses and TCC; retry only addresses; authenticated user must save an address; no request loop')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)})
