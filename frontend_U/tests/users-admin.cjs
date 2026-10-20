const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({args:['--host-resolver-rules=MAP users.localhost nginx']})
  const page = await browser.newPage()
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('token', `test.${btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))}.synthetic`))
  const user = { id: 77, cedula:'QA-77', nombre_completo:'Trabajador QA', correo:'qa@example.invalid', telefono:'3000000000', cargo:null, usuario:'qa.worker', tipo_usuario:3, estado:1, location_id:null }
  let attempts = 0, state = 'todos', saved = false, passwordCalls = 0
  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url())
    let json = {}, status = 200
    if (url.pathname.endsWith('/user/perfil')) json = { id:99, estado:1, tipo_usuario:4, nombre_completo:'Admin QA' }
    else if (url.pathname.endsWith('/lista-usuarios')) {
      state = url.searchParams.get('estado')
      json = { count:1, page:1, page_size:10, results:[{...user, estado:state==='0'?0:1}] }
    } else if (url.pathname.endsWith('/cargo-nivel-regional')) json = { cargos:[], niveles:[], regionales:[] }
    else if (url.pathname.includes('/locations')) json = { data:[] }
    else if (url.pathname.endsWith('/register/77') && request.method()==='PUT') {
      attempts++
      const payload = request.postDataJSON()
      assert.equal(payload.cedula, 'QA-77-EDIT')
      assert(!('password' in payload))
      if (attempts === 1) { status = 400; json = {correo:['Este correo ya está registrado.']} }
      else { await new Promise(resolve=>setTimeout(resolve,400)); Object.assign(user,payload); saved = true; json=user }
    } else if (url.pathname.endsWith('/password')) {
      passwordCalls++
      assert.equal(request.postDataJSON().new_password, 'Safe@NewPass935!')
      json = {message:'Contraseña actualizada'}
    }
    await route.fulfill({status,json})
  })
  await page.goto('http://users.localhost/admin/usuarios')
  await page.getByText('Trabajador QA',{exact:true}).waitFor()
  await page.getByLabel('Estado de las cuentas').click()
  await page.getByRole('option',{name:'Inactivos',exact:true}).click()
  await page.waitForTimeout(150)
  assert.equal(state,'0')
  await page.getByRole('button',{name:'Editar datos'}).click()
  let dialog=page.getByRole('dialog')
  await dialog.getByLabel('12345678').fill('QA-77-EDIT')
  await dialog.getByLabel('Juan Perez').fill('Nombre conservado QA')
  await dialog.getByRole('button',{name:'Guardar cambios'}).click()
  await dialog.getByRole('alert').first().waitFor()
  assert.equal(await dialog.getByLabel('Juan Perez').inputValue(),'Nombre conservado QA')
  assert.equal(await dialog.getByLabel('12345678').inputValue(),'QA-77-EDIT')
  await dialog.getByRole('button',{name:'Guardar cambios'}).dblclick()
  await dialog.waitFor({state:'hidden'})
  assert.equal(attempts,2)
  assert(saved)
  await page.getByText('Nombre conservado QA',{exact:true}).waitFor()
  await page.getByRole('button',{name:'Contraseña',exact:true}).click()
  dialog=page.getByRole('dialog')
  await dialog.getByLabel('Nueva contraseña',{exact:true}).fill('Safe@NewPass935!')
  await dialog.getByLabel('Confirmar contraseña',{exact:true}).fill('different')
  await dialog.getByRole('button',{name:'Actualizar contraseña'}).click()
  await dialog.getByText('Las contraseñas no coinciden.').waitFor()
  assert.equal(passwordCalls,0)
  await dialog.getByLabel('Confirmar contraseña',{exact:true}).fill('Safe@NewPass935!')
  await dialog.getByRole('button',{name:'Actualizar contraseña'}).click()
  await dialog.waitFor({state:'hidden'})
  assert.equal(passwordCalls,1)
  for (const width of [1280,768,390]) {
    await page.setViewportSize({width,height:900})
    await page.getByRole('button',{name:'Editar datos'}).click()
    assert(await page.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth))
    await page.getByRole('button',{name:'Cancelar',exact:true}).click()
  }
  assert.deepEqual(errors,[])
  console.log('PASS: inactive filter, edit document, field errors inside modal, preserved draft, duplicate request guard, password confirmation, responsive 1280/768/390')
  await browser.close()
})().catch(error=>{console.error(error.stack);process.exit(1)})
