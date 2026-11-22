// Live local Django/PostgreSQL only; no provider traffic and no production data.
const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict'), fs=require('node:fs')
const auth=JSON.parse(fs.readFileSync('/evidence/readiness-auth.json','utf8'))
const base='http://crm.localhost'
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 try{
  const page=await browser.newPage();page.setDefaultTimeout(15000)
  const errors=[],escapes=[];page.on('pageerror',e=>errors.push(e.message))
  await page.addInitScript(token=>{if(location.origin!=='null')localStorage.setItem('token',token)},auth.token)
  await page.routeWebSocket('**/ws/**',s=>s.close())
  await page.route('**/*',r=>{if(new URL(r.request().url()).hostname!=='crm.localhost'){escapes.push(new URL(r.request().url()).hostname);return r.abort()}return r.continue()})
  let injectFailure=true, posts=0
  await page.route('**/api/categories',async route=>{
   if(route.request().method()==='POST'){
    posts++
    if(injectFailure){injectFailure=false;return route.fulfill({status:400,json:{name:['Conflicto de nombre simulado.']}})}
   }
   return route.continue()
  })
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000})
   await page.goto(base+'/admin/categorias',{waitUntil:'networkidle'})
   await page.getByRole('button',{name:'Agregar Categoria',exact:true}).click()
   let dialog=page.getByRole('dialog')
   await dialog.getByLabel('Nombre',{exact:true}).fill('Iconos QA '+width+' '+Date.now())
   const name=await dialog.getByLabel('Nombre',{exact:true}).inputValue()
   const search=dialog.getByRole('searchbox',{name:'Buscar iconos'})
   await search.fill('válvula')
   const valve=dialog.getByRole('radio',{name:'Válvula — valve',exact:true})
   await valve.click();assert.equal(await valve.getAttribute('aria-checked'),'true')
   await valve.press('Home');assert.equal(await valve.getAttribute('aria-checked'),'true')
   await page.screenshot({path:`/evidence/icon-picker-${width}.png`})
   assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth),'dialog overflow '+width)
   await dialog.getByRole('button',{name:'Crear categoria',exact:true}).click()
   if(width===1440){
    await dialog.getByText('Conflicto de nombre simulado.',{exact:true}).waitFor()
    assert.equal(await dialog.getByLabel('Nombre',{exact:true}).inputValue(),name)
    assert.equal(await valve.getAttribute('aria-checked'),'true')
    await dialog.getByRole('button',{name:'Crear categoria',exact:true}).dblclick()
   }
   await dialog.waitFor({state:'hidden'})
   let row=page.getByRole('row').filter({has:page.getByText(name,{exact:true})})
   await row.waitFor();assert.equal(await row.locator('svg.lucide-flow-valve').count(),1)
   await page.reload({waitUntil:'networkidle'})
   row=page.getByRole('row').filter({has:page.getByText(name,{exact:true})})
   await row.waitFor();assert.equal(await row.locator('svg.lucide-flow-valve').count(),1)
   await row.getByRole('button',{name:'Editar',exact:true}).click()
   dialog=page.getByRole('dialog')
   await dialog.getByRole('searchbox',{name:'Buscar iconos'}).fill('manometro')
   const gauge=dialog.getByRole('radio',{name:'Manómetro — gauge',exact:true})
   await gauge.focus();await gauge.press('Space')
   assert.equal(await gauge.getAttribute('aria-checked'),'true')
   await dialog.getByRole('button',{name:'Guardar cambios',exact:true}).click()
   await dialog.waitFor({state:'hidden'})
   await row.locator('svg.lucide-gauge').waitFor()
   const response=await page.request.get('http://nginx/api/categories?per_page=100',{headers:{Authorization:'Bearer '+auth.token}})
   const data=await response.json();const saved=data.data.filter(c=>c.name===name)
   assert.equal(saved.length,1);assert.equal(saved[0].icon_key,'gauge')
   const catalog=await (await page.request.get('http://nginx/api/products?per_page=1')).json()
   assert.equal(catalog.categories.find(c=>c.id===saved[0].id).icon_key,'gauge')
   await page.goto(base+'/',{waitUntil:'networkidle'})
   const card=page.locator('.home-category-card').filter({hasText:name})
   await card.waitFor();assert.equal(await card.locator('svg.lucide-gauge').count(),1)
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'home overflow '+width)
   console.log('PASS live create/edit/reload/keyboard/persisted catalog metadata',width)
  }
  assert.equal(posts,4,'failed attempt plus one actual create per viewport')
  assert.deepEqual(errors,[]);assert.deepEqual(escapes,[])
 }finally{await browser.close()}
})().catch(e=>{console.error(String(e.message).replace(/Bearer\\s+[A-Za-z0-9._-]+/g,'Bearer [redacted]').replace(/eyJ[A-Za-z0-9._-]+/g,'[token redacted]'));process.exitCode=1})
