const { chromium } = require('/tools/node_modules/playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const base = process.env.ICON_QA_URL || 'http://localhost:4173'
const categories = JSON.parse(fs.readFileSync('/audit/tests/fixtures/category-icons.json','utf8').replace(/^\uFEFF/,''))
 .map((c,i)=>({...c,id:i+1,description:'',order:i+1,is_active:true,product_count:1}))
const unknown={id:100,name:'Nueva categoría QA',slug:'nueva-qa',icon:'invalid-icon',order:16,is_active:true,product_count:0}
const output=process.env.ICON_EVIDENCE || '/evidence'
;(async()=>{
 const browser=await chromium.launch()
 try {
  const page=await browser.newPage()
  const errors=[]
  page.on('pageerror',e=>errors.push(e.message))
  await page.addInitScript(()=>{if(location.origin!=='null')localStorage.setItem('token',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`)})
  await page.routeWebSocket('**/ws/**',s=>s.close())
  await page.route('https://**/*',r=>r.abort())
  let lastCategory
  await page.route('**/api/**',route=>{
   const url=new URL(route.request().url()); let json={}
   assert.equal(route.request().method(),'GET','no writes in UI validation')
   if(url.pathname.endsWith('/user/perfil'))json={id:99,estado:1,tipo_usuario:4,nombre_completo:'Admin QA'}
   else if(url.pathname.endsWith('/categories'))json={data:[...categories,unknown],total:16,total_pages:1}
   else if(url.pathname.endsWith('/products')){
    lastCategory=url.searchParams.get('category_id')
    json={data:[],total:0,total_pages:1,categories:[...categories,unknown],brands:[]}
   }else if(url.pathname.endsWith('/locations'))json={data:[]}
   return route.fulfill({json})
  })
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000})
   await page.goto(base+'/',{waitUntil:'networkidle'})
   await page.locator('.home-category-card').filter({hasText:'Nueva categoría QA'}).waitFor()
   const geometry=[]
   for(const c of categories){
    const selector=['calentadores','reguladores'].includes(c.slug)?`a[href="/productos?category=${c.slug}"]`:`a[href="/productos?category_id=${c.id}"]`
    const icon=page.locator('.home-category-card'+selector.slice(1)).locator('h3').locator('..').locator('svg')
    assert.equal(await icon.count(),1,c.slug)
    assert.equal(await icon.getAttribute('aria-hidden'),'true')
    geometry.push(await icon.innerHTML())
   }
   assert.equal(new Set(geometry).size,15)
   assert(await page.locator('.home-category-card').filter({hasText:'Nueva categoría QA'}).locator('svg.lucide-folder-tree').count())
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'home overflow '+width)
   if(width===1440)await page.locator('.home-categories__grid').screenshot({path:output+'/home-after.png'})
   await page.goto(base+'/productos',{waitUntil:'networkidle'})
   if(width<1024)await page.getByRole('button',{name:/Filtros/}).first().click()
   const region=width<1024?page.getByRole('dialog',{name:'Filtros de productos'}):page.locator('aside')
   for(let i=0;i<categories.length;i++){
    const label=region.locator('label').filter({hasText:categories[i].name}).first()
    assert.equal(await label.locator('svg').innerHTML(),geometry[i],categories[i].slug+' consistent filter')
   }
   await Promise.all([
    page.waitForResponse(r=>new URL(r.url()).searchParams.get('category_id')==='11' && r.status()===200),
    region.locator('label').filter({hasText:'Manómetro'}).click(),
   ])
   await page.waitForURL(url=>url.searchParams.get('category_id')==='11')
   assert.equal(new URL(page.url()).searchParams.get('category_id'),'11')
   assert.equal(lastCategory,'11')
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'catalog overflow '+width)
   await page.goto(base+'/admin/categorias',{waitUntil:'networkidle'})
   await page.getByRole('heading',{name:'Categorias',exact:true}).waitFor()
   for(let i=0;i<categories.length;i++){
    const row=page.getByRole('row').filter({has:page.getByText(categories[i].name,{exact:true})})
    assert.equal(await row.locator('svg[aria-hidden=true]').first().innerHTML(),geometry[i],categories[i].slug+' consistent admin')
   }
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'admin overflow '+width)
   await page.getByRole('row').filter({has:page.getByText('Manómetro',{exact:true})}).getByRole('button',{name:'Editar',exact:true}).click()
   const dialog=page.getByRole('dialog')
   assert.equal(await dialog.getByLabel('Icono',{exact:true}).inputValue(),'gauge')
   assert(await dialog.getByLabel('Icono',{exact:true}).isDisabled())
   await dialog.getByRole('button',{name:'Cancelar',exact:true}).click()
   await page.screenshot({path:output+`/admin-${width}.png`,fullPage:true})
   console.log('PASS home/admin/catalog/filter/unknown/preview/no-overflow',width)
  }
  for(const theme of ['light','dark']){
   await page.emulateMedia({colorScheme:theme})
   await page.setViewportSize({width:1280,height:900})
   for(const version of ['before','after']){
    await page.goto(`file:///evidence/icons-${version}.html`)
    await page.screenshot({path:output+`/icons-${version}-${theme}.png`,fullPage:true})
   }
  }
  assert.deepEqual(errors,[])
  console.log('PASS light/dark comparison and zero runtime errors')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
