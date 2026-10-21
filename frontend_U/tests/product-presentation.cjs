// All API calls are intercepted: no persistent products, files or carts are changed.
const { chromium } = require('/tmp/crm-ui/node_modules/playwright')
const assert = require('node:assert/strict')
const before = process.env.CAPTURE_BEFORE === '1'
const description = 'Características principales\n* Calentador de prueba\n- Cobre & seguridad\n• Garantía: 3 años\n\nSegundo párrafo\nCon otro salto\n<script>window.injected=true</script>'
const product = { id: 991, name: 'Calentador QA', slug: 'calentador-qa', description, price: 450000, category_id: 1, category_name: 'Calentadores', category: { id: 1, name: 'Calentadores', slug: 'calentadores' }, brand_id: 1, brand_name: 'QA', brand: { id: 1, name: 'QA' }, total_stock: 3, is_available: true, rating: 0, reviews_count: 0, specifications: [], stock_entries: [], images: [{ id: 11, image: '/qa-blue.svg', image_url: '/qa-blue.svg', order: 0, is_primary: false }, { id: 12, image: '/qa-orange.svg', image_url: '/qa-orange.svg', order: 1, is_primary: true }] }
;(async () => {
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP crm.localhost nginx'] })
  const page = await browser.newPage()
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    const token = `test.${btoa(JSON.stringify({exp: Math.floor(Date.now()/1000)+3600}))}.synthetic`
    localStorage.setItem('authToken', token)
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify({ id: '998', name: 'QA', role: 'client' }))
    localStorage.setItem('adminUser', JSON.stringify({ id: 998, email: 'qa@example.invalid' }))
  })
  await page.routeWebSocket('**/ws/**', ws => ws.close())
  let cart = []
  let cartPosts = 0
  let editorSaves = 0
  await page.route('**/qa-*.svg', route => route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect x="100" y="40" width="200" height="320" rx="20" fill="${route.request().url().includes('blue') ? '#2563eb' : '#ea580c'}"/></svg>` }))
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    let body = { data: [] }
    if (path.endsWith('/user/perfil')) body = { id: 998, tipo_usuario: 4, nombre_completo: 'QA', estado: 1 }
    else if (path.endsWith('/products/991/editor') && method === 'POST') {
      const payload = JSON.parse(route.request().postData().match(/name="payload"\r\n\r\n([\s\S]*?)\r\n--/)[1])
      assert.deepEqual(payload.images.map(image => image.id), [11, 12])
      product.images.forEach((image, index) => { image.is_primary = index === payload.primary })
      editorSaves++
      body = { data: product }
    }
    else if (path.endsWith('/cart')) {
      if (method === 'POST') {
        const payload = route.request().postDataJSON()
        assert.deepEqual(payload, { product_id: 991, quantity: 1 })
        cart = [payload]; cartPosts++
      }
      body = { items: cart }
    }
    else if (path.endsWith('/favorites')) body = { data: [{ id: 77, product: { ...product, primary_image: product.images.find(i => i.is_primary)?.image } }] }
    else if (/\/products\/991$/.test(path)) body = { data: product }
    else if (/\/products$/.test(path)) body = { data: [{ ...product, primary_image: product.images.find(i => i.is_primary)?.image }], total: 1, total_pages: 1 }
    else if (path.includes('/reviews')) body = { data: [], total: 0 }
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('http://crm.localhost/producto/991')
  await page.getByRole('heading', { name: product.name, exact: true }).waitFor()
  for (const width of [1280, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.screenshot({ path: `/evidence/${before ? 'before' : 'after'}-${width}.png`, fullPage: true })
    if (!before) assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow ${width}`)
  }
  if (!before) {
    assert.equal(await page.locator('.product-description li').count(), 3)
    assert.equal(await page.locator('.product-description script').count(), 0)
    assert.equal(await page.evaluate(() => window.injected), undefined)
    assert.equal(await page.getByText('Envío Gratis', { exact: true }).count(), 0)
    assert.equal(await page.getByText('5 años de garantía', { exact: true }).count(), 0)
    assert.equal(await page.locator('.product-detail-layout img').first().getAttribute('src'), '/qa-orange.svg')
    await page.getByRole('button', { name: 'Ver imagen 2', exact: true }).focus()
    await page.keyboard.press('Enter')
    assert.equal(await page.locator('.product-detail-layout img').first().getAttribute('src'), '/qa-blue.svg')
    await page.getByRole('button', { name: 'Agregar al Carrito', exact: true }).click()
    await page.getByRole('button', { name: 'Agregado al Carrito', exact: true }).waitFor()
    assert.equal(cartPosts, 1)
    const original = product.description
    for (const [text, lists, paragraphs] of [['Texto simple', 0, 1], ['', 0, 1], ['Párrafo 1\n\nPárrafo 2', 0, 2], ['Uno\nDos', 0, 1], ['* Uno\n- Dos\n• Tres', 3, 0], ['Áé & <img src=x onerror="window.injected=true"> https://example.invalid/' + 'x'.repeat(300), 0, 1]]) {
      product.description = text
      await page.reload()
      await page.getByRole('heading', { name: product.name, exact: true }).waitFor()
      assert.equal(await page.locator('.product-description li').count(), lists)
      assert.equal(await page.locator('.product-description p').count(), paragraphs)
      assert.equal(await page.locator('.product-description img, .product-description script').count(), 0)
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    }
    product.description = original
    const images = product.images
    for (const values of [[images[0]], []]) {
      product.images = values
      await page.reload()
      await page.getByRole('heading', { name: product.name, exact: true }).waitFor()
      const src = await page.locator('.product-detail-layout img').first().getAttribute('src')
      assert(values.length ? src === '/qa-blue.svg' : src.includes('placehold.co'))
    }
    product.images = images
    await page.setViewportSize({ width: 1280, height: 1000 })
    await page.goto('http://crm.localhost/admin/productos')
    await page.getByRole('button', { name: 'Editar', exact: true }).click()
    await page.getByLabel('Descripción', { exact: true }).waitFor()
    assert.equal(await page.getByLabel('Descripción', { exact: true }).inputValue(), description)
    await page.getByText('Vista previa de la descripción', { exact: true }).click()
    assert.equal(await page.locator('.product-description li').count(), 3)
    await page.getByRole('button', { name: 'Usar imagen 1 como principal', exact: true }).click()
    await page.waitForFunction(() => document.querySelector('[aria-label="Usar imagen 1 como principal"]')?.getAttribute('aria-pressed') === 'true')
    assert.equal(editorSaves, 0, 'Selecting the main image must remain local until the editor is saved')
    await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click()
    await page.getByRole('dialog').waitFor({state:'hidden'})
    assert.equal(editorSaves, 1)
    await page.getByRole('button', { name: 'Editar', exact: true }).click()
    await page.getByRole('button', { name: 'Usar imagen 1 como principal', exact: true }).waitFor()
    for (const width of [1280, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 })
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `admin overflow ${width}`)
      await page.getByRole('button', { name: 'Usar imagen 1 como principal', exact: true }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: `/evidence/admin-after-${width}.png`, fullPage: true })
    }
    await page.reload()
    await page.getByRole('button', { name: 'Editar', exact: true }).click()
    await page.getByRole('button', { name: 'Usar imagen 1 como principal', exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Usar imagen 1 como principal', exact: true }).getAttribute('aria-pressed'), 'true')
    for (const path of ['/productos', '/productos?search=Calentador', '/producto/991', '/carrito', '/favoritos']) {
      await page.goto(`http://crm.localhost${path}`)
      await page.locator('img[src="/qa-blue.svg"]').first().waitFor()
    }
    assert.deepEqual(errors, [])
  }
  console.log(before ? 'Before screenshots saved (synthetic fixtures)' : 'PASS: description paragraphs/newlines/*/-/•/empty/special/XSS/long text; one/multiple/no images; keyboard gallery; admin selection and reload; catalog/search/detail/cart/favorites; one add-to-cart; responsive 1280/768/390; no browser errors. All APIs mocked.')
  await browser.close()
})().catch(e => { console.error(e); process.exit(1) })
