const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 const browser=await chromium.launch({args:['--host-resolver-rules=MAP crm.localhost nginx']})
 const page=await browser.newPage();page.setDefaultTimeout(15000)
 let failedList=true,failedSave=true,saves=0
 let templates=[{id:81,name:'Saludo QA',text:'Hola {{nombre_cliente}}',channels:['whatsapp_web'],category:'Ventas',active:true,variables:['nombre_cliente'],favorite:false,last_used_at:null,updated_at:new Date().toISOString(),author_name:'QA',attachment_url:'',attachment_metadata:{}}]
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.addInitScript(()=>localStorage.setItem('token',`test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`))
 await page.routeWebSocket('**/ws/**',s=>s.close());await page.route('https://**',r=>r.abort())
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url()),path=url.pathname,method=route.request().method();let body={},status=200
  if(path.endsWith('/user/perfil'))body={id:998,tipo_usuario:4,nombre_completo:'QA',estado:1}
  else if(path.endsWith('/templates/')&&method==='GET'){if(failedList){status=503;body={error:'Synthetic failure'}}else body=templates.filter(t=>!url.searchParams.get('search')||t.name.includes(url.searchParams.get('search')))}
  else if(path.endsWith('/duplicate/')){const copy={...templates[0],id:83,name:templates[0].name+' (copia)'};templates.push(copy);body=copy}
  else if(path.includes('/templates/')&&method==='POST'){
   saves++;if(failedSave){status=400;body={name:['Nombre ya utilizado.']}}else{
    const text=route.request().postData()||'',field=name=>text.match(new RegExp('name="'+name+'"\\r\\n\\r\\n([^\\r]*)'))?.[1]||''
    const id=Number(path.match(/templates\/(\d+)/)?.[1])||82
    const item={...templates[0],id,name:field('name'),text:field('text'),category:field('category'),channels:JSON.parse(field('channels')||'[]'),active:field('active')==='true'}
    templates=templates.filter(t=>t.id!==id).concat(item);body=item
   }
  }else if(method==='PATCH'){const id=Number(path.match(/templates\/(\d+)/)?.[1]);templates=templates.map(t=>t.id===id?{...t,...route.request().postDataJSON()}:t)}
  else if(method==='DELETE'){const id=Number(path.match(/templates\/(\d+)/)?.[1]);templates=templates.filter(t=>t.id!==id);status=204}
  await route.fulfill({status,...(status===204?{}:{json:body})})
 })
 try{
  await page.goto('http://crm.localhost/chat/plantillas')
  await page.getByRole('heading',{name:'Plantillas',exact:true}).waitFor()
  assert.equal(await page.getByRole('dialog').count(),0);assert.equal(new URL(page.url()).pathname,'/chat/plantillas')
  await page.getByText('No fue posible cargar las plantillas.',{exact:false}).waitFor()
  assert.equal(await page.getByText('No hay plantillas para estos filtros.',{exact:true}).count(),0)
  failedList=false;await page.getByRole('button',{name:'Reintentar listado'}).click()
  await page.getByRole('button',{name:'Saludo QA',exact:true}).waitFor()
  await page.getByRole('combobox',{name:'Canal',exact:true}).click();await page.getByRole('option',{name:'Facebook',exact:true}).click();await page.getByText('No hay plantillas para estos filtros.').waitFor()
  await page.getByRole('combobox',{name:'Canal',exact:true}).click();await page.getByRole('option',{name:'Todos',exact:true}).click()
  await page.getByRole('combobox',{name:'Estado',exact:true}).click();await page.getByRole('option',{name:'Inactivas',exact:true}).click();await page.getByText('No hay plantillas para estos filtros.').waitFor()
  await page.getByRole('combobox',{name:'Estado',exact:true}).click();await page.getByRole('option',{name:'Todos',exact:true}).click()
  await page.getByRole('combobox',{name:'Categoría',exact:true}).click();await page.getByRole('option',{name:'Ventas',exact:true}).click();await page.getByRole('button',{name:'Saludo QA',exact:true}).waitFor()
  await page.reload();await page.getByRole('button',{name:'Nueva plantilla',exact:true}).waitFor();assert.equal(await page.getByRole('dialog').count(),0)
  await page.getByRole('button',{name:'Nueva plantilla',exact:true}).click()
  let dialog=page.getByRole('dialog');await dialog.waitFor()
  const name=dialog.getByRole('textbox',{name:/^Nombre/})
  await name.waitFor();await page.waitForFunction(id=>document.activeElement?.id===id,await name.getAttribute('id'))
  await name.fill('Nueva QA');await dialog.getByRole('textbox',{name:'Contenido',exact:true}).fill('Hola {{nombre_cliente}}')
  await dialog.getByRole('button',{name:'Guardar plantilla'}).dblclick()
  await dialog.getByText('Nombre ya utilizado.',{exact:true}).waitFor();assert.equal(saves,1);assert.equal(await name.inputValue(),'Nueva QA')
  failedSave=false;await dialog.getByRole('button',{name:'Guardar plantilla'}).click();await dialog.waitFor({state:'hidden'})
  await page.getByRole('button',{name:'Nueva QA',exact:true}).waitFor()
  await page.getByRole('button',{name:'Editar',exact:true}).first().click();dialog=page.getByRole('dialog')
  await dialog.getByRole('textbox',{name:/^Nombre/}).fill('Edición sin guardar')
  await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();await dialog.getByText(/Hay cambios sin guardar/).waitFor()
  await dialog.getByRole('button',{name:'Seguir editando'}).click();assert.equal(await dialog.getByRole('textbox',{name:/^Nombre/}).inputValue(),'Edición sin guardar')
  await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();await dialog.getByRole('button',{name:'Descartar cambios'}).click();await dialog.waitFor({state:'hidden'})
  assert.equal(await page.locator('.MuiBackdrop-root:visible').count(),0)
  await page.getByRole('button',{name:'Editar',exact:true}).first().click();dialog=page.getByRole('dialog');await dialog.getByRole('textbox',{name:'Contenido',exact:true}).fill('Contenido actualizado')
  await dialog.getByRole('button',{name:'Guardar plantilla',exact:true}).click();await dialog.waitFor({state:'hidden'})
  assert(templates.some(t=>t.text==='Contenido actualizado'))
  await page.getByRole('button',{name:'Duplicar',exact:true}).first().click();dialog=page.getByRole('dialog');await dialog.getByRole('textbox',{name:/^Nombre/}).waitFor()
  assert((await dialog.getByRole('textbox',{name:/^Nombre/}).inputValue()).includes('(copia)'))
  await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();await dialog.waitFor({state:'hidden'})
  await page.getByRole('button',{name:'Desactivar',exact:true}).first().click();await page.getByRole('button',{name:'Activar',exact:true}).first().waitFor()
  await page.getByRole('button',{name:'Activar',exact:true}).first().click()
  await page.getByRole('button',{name:'Eliminar',exact:true}).last().click();dialog=page.getByRole('dialog',{name:'Eliminar plantilla'})
  await dialog.getByRole('button',{name:'Eliminar plantilla',exact:true}).click();await dialog.waitFor({state:'hidden'})
  await page.getByRole('textbox',{name:'Buscar por nombre o texto'}).fill('Sin coincidencias');await page.getByText('No hay plantillas para estos filtros.').waitFor()
  await page.getByRole('textbox',{name:'Buscar por nombre o texto'}).fill('')
  for(const width of [1280,768,390]){await page.setViewportSize({width,height:900});await page.waitForFunction(()=>{const e=document.querySelector("main");return e&&e.scrollWidth<=e.clientWidth});assert(await page.locator("main").evaluate(e=>e.scrollWidth<=e.clientWidth));if(process.env.QA_OUTPUT)await page.screenshot({path:process.env.QA_OUTPUT+"/templates-page-"+width+".png",fullPage:true})}
  await page.goto('http://crm.localhost/admin/chat/plantillas');await page.getByRole('heading',{name:'Plantillas',exact:true}).waitFor();assert.equal(await page.getByRole('dialog').count(),0)
  await page.goBack();await page.getByRole('heading',{name:'Plantillas',exact:true}).waitFor();await page.goForward();assert.equal(await page.getByRole('dialog').count(),0)
  await page.getByRole('button',{name:'Abrir navegación',exact:true}).click();await page.getByRole('link',{name:'Plantillas CRM',exact:true}).click();await page.getByRole('heading',{name:'Plantillas',exact:true}).waitFor();assert.equal(await page.getByRole('dialog').count(),0)
  const newButton=page.getByRole('button',{name:'Nueva plantilla',exact:true});await newButton.click();dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'Cancelar',exact:true}).click();await dialog.waitFor({state:'hidden'})
  assert(await newButton.evaluate(el=>el===document.activeElement));assert.equal(await page.locator('.MuiBackdrop-root:visible').count(),0)
  assert.deepEqual(errors,[])
  console.log('PASS templates normal page and route alias, no auto modal, reload/history, create/save/error retention, dirty cancel, duplicate, activation/delete, search, overlays and responsive')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)})
