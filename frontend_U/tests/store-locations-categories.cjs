const { chromium } = require('/tools/node_modules/playwright')
const assert = require('node:assert/strict')
const place = 'ChIJXf6b2uupMI4RNN6J4-rm_jo'
const categories = [
  ['Electricidad', 'electricidad', 'zap'], ['Medidor de gas', 'medidor-de-gas', 'meter'],
  ['Manómetro', 'manometro', 'gauge'], ['Regulador de gas', 'regulador-de-gas', 'sliders'],
  ['Latón', 'laton', 'link'], ['Galvanizado', 'galvanizado', 'construction'],
  ['Tanque de acumulación', 'tanque-de-acumulacion', 'cylinder'],
].map(([name, slug, icon], index) => ({ id: index + 1, name, slug, icon, product_count: 0 }))
const locations = [
  { id: 1, name: 'SEDE CALI NORTE', address: 'Av. 6 Norte #30N-46, piso 1, San Vicente', city: 'Cali',
    latitude: '3.4718433', longitude: '-76.5266492', google_place_id: place },
  { id: 2, name: 'SEDE CALI SUR', address: 'Cll 10 # 65a-75 local 809', city: 'Cali' },
]

;(async () => {
  const browser = await chromium.launch()
  try {
    for (const width of [1440, 768, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } })
      await page.routeWebSocket('**/ws/**', socket => socket.close())
      await page.route('https://**/*', route => {
        if (route.request().url().startsWith('https://www.google.com/maps?')) {
          if (width === 390) return new Promise(() => {})
          return route.fulfill({ contentType: 'text/html', body: '<p>Mapa simulado · prueba de interfaz</p>' })
        }
        return route.abort()
      })
      await page.route('**/api/**', route => {
        const { pathname } = new URL(route.request().url())
        return route.fulfill({ json: pathname.endsWith('/locations') ? { data: locations } :
          pathname.endsWith('/products') ? { data: [], total: 0, total_pages: 1, categories, brands: [] } : {} })
      })
      await page.goto('http://localhost:4173/', { waitUntil: 'domcontentloaded' })
      for (const { name, id } of categories) {
        const link = page.locator('a[href="/productos?category_id=' + id + '"]').filter({ hasText: name })
        await link.waitFor()
        assert.equal(await link.locator('h3').locator('..').locator('svg[aria-hidden=true]').count(), 1)
      }
      const north = page.getByRole('link', { name: 'Cómo llegar' })
      const url = new URL(await north.getAttribute('href'))
      assert.equal(url.protocol, 'https:')
      assert.equal(url.searchParams.get('destination_place_id'), place)
      assert.equal(url.searchParams.get('destination'), '3.4718433,-76.5266492')
      const map = page.locator('iframe[title="Ubicación de SEDE CALI NORTE"]')
      const embed = new URL(await map.getAttribute('src'))
      assert.equal(embed.searchParams.get('q'), '3.4718433,-76.5266492')
      assert.equal(embed.searchParams.has('key'), false)
      if (width === 390) {
        await page.getByText('Cargando mapa…').waitFor()
        await page.getByText('No se pudo cargar el mapa.', { exact: false }).waitFor({ timeout: 15000 })
        assert.equal(await north.isVisible(), true)
      } else {
        await page.getByRole('button', { name: /SEDE CALI SUR/ }).click()
        const south = new URL(await north.getAttribute('href'))
        assert.equal(south.searchParams.get('destination'), locations[1].address + ', Cali, Colombia')
      }
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      await page.goto('http://localhost:4173/contacto', { waitUntil: 'domcontentloaded' })
      await page.getByRole('link', { name: 'Cómo llegar' }).waitFor()
      assert.equal(new URL(await page.getByRole('link', { name: 'Cómo llegar' }).getAttribute('href')).searchParams.get('destination_place_id'), place)
      await page.close()
    }
    console.log('PASS: 7 categorías/iconos, enlace Norte, Sur, error y mapa sin clave a 1440/768/390 px')
  } finally {
    await browser.close()
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
