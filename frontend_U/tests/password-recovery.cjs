const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
;(async () => {
 const {address} = await require('node:dns').promises.lookup('nginx')
 const fixture = process.env.QA_RESET_API || 'http://password-reset-browser:8098'
 const browser = await chromium.launch({args:[`--host-resolver-rules=MAP crm.localhost ${address}`]})
 try {
  for (const width of [1280,390]) {
   const page = await browser.newPage({viewport:{width,height:900}})
   let requests = 0
   await page.route('**/api/**', async route => {
    const request = route.request()
    if(request.url().includes('/password/reset/request')) requests++
    const url = new URL(request.url())
    const response = await route.fetch({url:fixture+url.pathname.replace(/^\/api/,'')+url.search})
    await route.fulfill({response})
   })
   console.log('STAGE login '+width)
   await page.goto('http://crm.localhost/login')
   await page.getByRole('link',{name:'¿Olvidaste tu contraseña?'}).click()
   assert.equal(new URL(page.url()).pathname,'/recuperar-contrasena')
   await page.getByLabel('Correo electrónico').fill(width===1280?'browser-reset@example.invalid':'unknown@example.invalid')
   await page.getByRole('button',{name:'Enviar enlace de recuperación'}).click()
   console.log('STAGE submitted '+width)
   await page.getByRole('status').filter({hasText:'Si existe una cuenta'}).waitFor()
   assert.equal(requests,1)
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
   if(width===1280) {
    const state = await (await page.request.get(fixture+'/__qa/mail')).json()
    assert.equal(state.count,1); assert.deepEqual(state.states,['sent'])
    const resetURL = state.body.match(/https?:\/\/\S+#uid=\S+/)[0]
    console.log('STAGE reset navigation')
    await page.goto(resetURL)
    await page.getByLabel('Nueva contraseña',{exact:true}).waitFor()
    await page.getByLabel('Nueva contraseña',{exact:true}).fill('Browser-new-synthetic-587!')
    await page.getByLabel('Confirmar nueva contraseña').fill('different-synthetic')
    await page.getByRole('button',{name:'Guardar contraseña'}).click()
    await page.getByRole('alert').filter({hasText:'no coinciden'}).waitFor()
    await page.getByLabel('Nueva contraseña',{exact:true}).fill('password123')
    await page.getByLabel('Confirmar nueva contraseña').fill('password123')
    await page.getByRole('button',{name:'Guardar contraseña'}).click()
    await page.getByRole('alert').filter({hasText:'común'}).waitFor()
    assert.ok(!(await page.getByRole('alert').innerText()).includes('new_password'))
    await page.getByLabel('Nueva contraseña',{exact:true}).fill('Browser-new-synthetic-587!')
    await page.getByLabel('Confirmar nueva contraseña').fill('Browser-new-synthetic-587!')
    await page.getByRole('button',{name:'Mostrar contraseñas'}).click()
    assert.equal(await page.getByLabel('Nueva contraseña',{exact:true}).getAttribute('type'),'text')
    await page.getByRole('button',{name:'Guardar contraseña'}).click()
    console.log('STAGE submitted '+width)
   await page.getByRole('status').filter({hasText:'actualizada correctamente'}).waitFor()
    for(const [password,status] of [['Browser-old-synthetic-942!',401],['Browser-new-synthetic-587!',200]]) {
     const result=await page.request.post(fixture+'/auth/token/',{data:{usuario:'browser-reset@example.invalid',password}})
     assert.equal(result.status(),status)
    }
    console.log('STAGE reset navigation')
    await page.goto(resetURL)
    await page.reload()
    await page.getByRole('alert').filter({hasText:'Enlace inválido o vencido'}).waitFor()
   }
   await page.goto('http://crm.localhost/restablecer-contrasena#uid=invalid&token=invalid')
   await page.getByRole('alert').filter({hasText:'Enlace inválido o vencido'}).waitFor()
   if(width===390) {
    let attempts=0
    await page.route('**/api/user/password/reset/request',async route=>{
     attempts++; await new Promise(resolve=>setTimeout(resolve,150))
     await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'unavailable'})})
    })
    await page.goto('http://crm.localhost/recuperar-contrasena')
    await page.getByLabel('Correo electrónico').fill('preserved@example.invalid')
    await page.locator('form').filter({has:page.getByLabel('Correo electrónico')}).evaluate(form=>{form.requestSubmit();form.requestSubmit()})
    await page.getByRole('alert').filter({hasText:'No fue posible enviar'}).waitFor()
    assert.equal(await page.getByLabel('Correo electrónico').inputValue(),'preserved@example.invalid')
    assert.equal(attempts,1)
   }
   await page.close()
  }
  console.log('PASS desktop/mobile: login link, neutral request, actual locmem email, URL fragment, validation, mismatch preservation, show/hide, reset, old/new login, one use, invalid link; no real SMTP')
 } finally { await browser.close() }
})().catch(error=>{console.error('FAIL '+String(error.message).replace(/https?:\/\/\S+/g,'[URL REDACTED]'));process.exit(1)})
