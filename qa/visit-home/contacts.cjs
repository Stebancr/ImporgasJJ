const { chromium } = require('playwright')
const assert = require('node:assert/strict')
;(async () => {
  const browser = await chromium.launch({args:['--host-resolver-rules=MAP localhost visit-home-ui-qa']})
  try {
    const page = await browser.newPage({viewport:{width:768,height:1024}})
    await page.addInitScript(() => {
      const claims = btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}))
      localStorage.setItem('token','mock.'+claims+'.mock')
    })
    const client = {id:2,nombre:'Cliente QA',telefono:'3001234567',correo:'qa@example.test',direccion:'Calle de prueba',indicaciones_llegada:'Portería 2'}
    await page.route('**/*', route => {
      const url = new URL(route.request().url())
      if (url.hostname !== 'localhost') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      const p = url.pathname
      if (p === '/api/user/perfil') return route.fulfill({json:{id:1,tipo_usuario:4,estado:1,nombre_completo:'Admin QA'}})
      if (p.endsWith('/clientes/buscar/')) {
        assert.deepEqual(route.request().postDataJSON(), {term:'Cliente QA'})
        return route.fulfill({json:[client]})
      }
      if (p.endsWith('/clientes/2/historial/')) return route.fulfill({json:{next:null,results:[{id:1,numero_tarea:'1000',fecha:'2026-11-27',estado:'finalizada'}]}})
      return route.fulfill({json:[]})
    })
    await page.goto('http://localhost:3001/admin/visitas')
    await page.getByRole('button',{name:'Nueva Visita',exact:true}).click()
    await page.getByLabel('Buscar cliente por nombre, teléfono o correo').fill('Cliente QA')
    await page.getByRole('button',{name:'Buscar',exact:true}).click()
    await page.getByRole('button',{name:/Cliente QA.*3001234567/}).click()
    await page.getByText('Historial de visitas',{exact:true}).waitFor()
    await page.getByText('Calle de prueba',{exact:true}).waitFor()
    await page.getByRole('button',{name:'Registrar cliente nuevo'}).click()
    await page.getByText('Los datos se guardarán al crear la visita.').waitFor()
    assert.equal(await page.getByText('Historial de visitas',{exact:true}).count(),0)
    console.log('PASS administración: búsqueda, selección, autocompletado, historial, cambio a nuevo cliente')
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
