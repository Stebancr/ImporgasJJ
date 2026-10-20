// API transport is mocked; PostgreSQL migration/rollback and persistence have separate Docker rehearsals.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP tcc.localhost tcc-rollout-frontend-qa']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(()=>localStorage.setItem('token',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`))
 let saved=0,stockWrites=0
 const product={id:991,name:'Histórico sin logística',slug:'historico',description:'Conservar',price:2900000,
  category_id:1,brand_id:1,total_stock:7,is_available:true,is_featured:false,shipping_profile:null,shipping_ready:false,
  shipping_status:'incomplete',images:[],specifications:[],stock_entries:[]}
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname;let json={data:[]}
  if(path.endsWith('/user/perfil'))json={id:998,tipo_usuario:4,nombre_completo:'QA',estado:1}
  else if(path.endsWith('/products/991')&&request.method()==='PUT'){
   const payload=request.postDataJSON();assert(!('shipping_profile' in payload),'Untouched logistics must be omitted')
   assert.equal(payload.description,'Editar sin inventar peso');assert(!('price' in payload),'An unchanged price must not be overwritten')
   Object.assign(product,payload);saved++;json={data:product}
  }else if(path.endsWith('/products/991/stock')){
   if(request.method()==='POST')stockWrites++
   json={data:[{product_id:991,location_id:1,quantity:7}]}
  }else if(path.endsWith('/products/991'))json={data:product}
  else if(path.endsWith('/products'))json={data:[product],total:1,page:1,per_page:20,total_pages:1}
  else if(path.endsWith('/brands'))json={data:[{id:1,name:'Marca QA',is_active:true}]}
  else if(path.endsWith('/locations'))json={data:[{id:1,name:'Sede QA',city:'Cali',is_active:true}]}
  else if(path.endsWith('/categories'))json={data:[{id:1,name:'Categoría QA',is_active:true}]}
  else if(path.endsWith('/shipping/config'))json={enabled:false,requires_shipping_confirmation:true}
  await route.fulfill({json})
 })
 await page.goto('http://tcc.localhost:3000/admin/productos')
 await page.getByRole('button',{name:'Editar',exact:true}).click()
 const dialog=page.getByRole('dialog')
 await dialog.getByText(/Información de envío incompleta/).waitFor()
 await dialog.getByLabel('Descripción',{exact:true}).fill('Editar sin inventar peso')
 for(const width of [1280,768,390]){
  await page.setViewportSize({width,height:1000});assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth))
 }
 await dialog.getByRole('button',{name:'Guardar cambios',exact:true}).click()
  await dialog.waitFor({state:'hidden'});assert.equal(saved,1);assert.equal(stockWrites,0)
 await page.goto('http://tcc.localhost:3000/producto/991')
 await page.getByText(/Envío: pendiente por calcular/).waitFor()
 await page.route('**/api/shipping/config',route=>route.fulfill({status:503,json:{error:'Synthetic unavailable'}}))
 await page.reload()
 await page.getByText(/Envío: pendiente por calcular/).waitFor()
 await page.getByRole('alert').filter({hasText:/No fue posible consultar/}).waitFor()
 assert.deepEqual(errors,[])
 console.log('PASS: legacy admin edit omits logistics, preserves price, responsive modal, pending shipping message with TCC disabled')
 await browser.close()
})().catch(error=>{console.error(error.stack);process.exit(1)})
