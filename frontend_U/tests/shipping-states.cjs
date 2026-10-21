// Docker browser fixtures: each request family can fail independently.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
const chooseLocation=require('./location-select.cjs')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 try{
  for(const scenario of ['incomplete','disabled','config-error','catalog-error','catalog-empty','idle','quote-error','network-error','success']){
   const page=await browser.newPage();page.setDefaultTimeout(12000)
   const calls={config:0,cities:0,estimate:0};let retry=false
   const errors=[];page.on('pageerror',e=>errors.push(e.message))
   await page.route('https://**',r=>r.abort());await page.routeWebSocket('**/ws/**',s=>s.close())
   await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname;let status=200,body={data:[]}
    if(path.endsWith('/products/991'))body={data:{id:991,name:'Producto QA',slug:'qa',description:'QA',price:125000,category_id:1,brand_id:1,total_stock:20,is_available:true,rating:0,reviews_count:0,images:[],shipping_ready:scenario!=='incomplete',shipping_missing_fields:scenario==='incomplete'?['Peso','Alto']:[]}}
    else if(path.endsWith('/cart'))body={items:[]}
    else if(path.endsWith('/shipping/config')){calls.config++;if(scenario==='config-error'&&!retry){status=503;body={error:'Synthetic unavailable'}}else body={enabled:scenario!=='disabled'}}
    else if(path.endsWith('/shipping/cities')){calls.cities++;if(scenario==='catalog-error'&&!retry){status=503;body={error:'Synthetic unavailable'}}else body=scenario==='catalog-empty'?[]:[{code:'76001000',city:'CALI',department:'VALLE DEL CAUCA'},{code:'11001000',city:'BOGOTA',department:'BOGOTA D.C.'}]}
    else if(path.endsWith('/shipping/estimate')){calls.estimate++;if(scenario==='network-error'&&!retry)return route.abort('timedout');if(scenario==='quote-error'&&!retry){status=503;body={error:'Servicio temporalmente no disponible'}}else body={carrier:'TCC',total:'30000',subtotal:'125000',order_total:'155000',tcc_rate:'30000',surcharge:'0',destination:{city:'CALI'},expires_at:new Date(Date.now()+600000).toISOString()}}
    await route.fulfill({status,json:body})
   })
   await page.goto('http://crm.localhost/producto/991')
   const shipping=page.getByRole('region',{name:'Información de envío'})
   await shipping.getByText('Precio del producto:',{exact:false}).waitFor()
   if(scenario==='incomplete'){
    await shipping.getByText('Envío pendiente por configurar',{exact:true}).waitFor()
    assert.equal(await shipping.getByRole('alert').count(),0);assert.equal(await shipping.getByRole('button',{name:/Reintentar/}).count(),0)
    assert.equal(calls.estimate,0)
   }else if(scenario==='disabled'){
    await shipping.getByText('La cotización automática de envío no está disponible en este momento.').waitFor();assert.equal(calls.estimate,0)
   }else if(scenario==='config-error'){
    await shipping.getByText('No fue posible consultar la configuración de envíos.',{exact:true}).waitFor()
    assert.equal(await shipping.getByText(/No fue posible cargar los departamentos/).count(),0)
    const catalogCalls=calls.cities;retry=true
    await shipping.getByRole('button',{name:'Reintentar configuración'}).click()
    await shipping.getByText('Calcula el costo de entrega',{exact:true}).waitFor()
    assert.equal(calls.config,2);assert.equal(calls.cities,catalogCalls)
   }else if(scenario==='catalog-error'){
    await shipping.getByText('No fue posible cargar los departamentos y ciudades.',{exact:true}).waitFor()
    const configCalls=calls.config;retry=true
    await shipping.getByRole('button',{name:'Reintentar ubicaciones'}).click()
    await shipping.getByRole('button',{name:'Configurar ubicación de entrega'}).click()
    await chooseLocation(page,'Departamento de entrega','VALLE DEL CAUCA')
    assert.equal(calls.config,configCalls);assert.equal(calls.estimate,0)
   }else if(scenario==='catalog-empty'){
    await shipping.getByText('No hay departamentos y ciudades disponibles por el momento.').waitFor()
    assert.equal(await shipping.getByRole('alert').count(),0)
   }else{
    await shipping.getByRole('button',{name:'Configurar ubicación de entrega'}).click()
    if(scenario==='catalog-error'){
     await shipping.getByText('No fue posible cargar los departamentos y ciudades.',{exact:false}).waitFor()
     const configCalls=calls.config;retry=true
     await shipping.getByRole('button',{name:'Reintentar ubicaciones'}).click()
     await shipping.getByRole('combobox',{name:'Departamento de entrega',exact:true}).isEnabled()
     await chooseLocation(page,'Departamento de entrega','VALLE DEL CAUCA')
     assert.equal(calls.config,configCalls);assert.equal(calls.estimate,0)
    }else if(scenario==='catalog-empty'){
     await shipping.getByText('No hay departamentos y ciudades disponibles por el momento.').waitFor()
     assert.equal(await shipping.getByRole('alert').count(),0)
    }else if(scenario!=='idle'){
     await chooseLocation(page,'Departamento de entrega','VALLE DEL CAUCA');await chooseLocation(page,'Ciudad o municipio de entrega','CALI')
     if(scenario==='quote-error'||scenario==='network-error'){
      await shipping.getByText('No fue posible calcular el costo de envío.',{exact:true}).waitFor()
      assert.equal(await shipping.getByText('Total estimado:',{exact:false}).count(),0)
      const c={...calls};retry=true;await shipping.getByRole('button',{name:'Reintentar cotización'}).click()
      await shipping.getByText('Total estimado:',{exact:false}).waitFor()
      assert.equal(calls.config,c.config);assert.equal(calls.cities,c.cities);assert.equal(calls.estimate,c.estimate+1)
     }else await shipping.getByText('Total estimado:',{exact:false}).waitFor()
     const stable={...calls};await page.waitForTimeout(800);assert.deepEqual(calls,stable,'Requests must not loop')
    }
   }
   assert(!/Envío gratis|Envío: \$0/.test(await shipping.innerText()))
   assert.deepEqual(errors,[])
   await page.close()
  }
  console.log('PASS 9 shipping scenarios: incomplete, disabled, configuration, catalogue failure/empty, idle, provider failure, network timeout and success; independent retry, no loops or false free shipping')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)})
