const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const mode = process.argv[2]
const products = ['Calentador de paso', 'Regulador de gas', 'Manómetro', 'Conexión de latón'].map((name, i) => ({
  id: i + 1, name, slug: 'producto-' + i, description: 'Producto sintético de QA',
  price: 95000 * (i + 1), total_stock: 4, is_available: true, is_featured: false,
  brand_name: 'Marca de prueba', category_id: 1, rating: 0, reviews_count: 0,
  primary_image: '/calentadores.jpg',
}))
;(async () => {
  const browser = await chromium.launch({args:['--no-sandbox','--host-resolver-rules=MAP localhost visit-home-ui-qa']})
  try {
    for (const width of [1440, 768, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } })
      const errors = []
      page.on('pageerror', error => errors.push(error.message))
      let empty = false
      await page.route('**/*', async route => {
        const url = new URL(route.request().url())
        if (url.hostname !== 'localhost') return route.abort()
        if (!url.pathname.startsWith('/api/')) return route.continue()
        if (url.pathname === '/api/shipping/config') return route.fulfill({json:{enabled:false}})
        if (url.pathname === '/api/shipping/cities') return route.fulfill({json:[]})
        const list = url.pathname === '/api/products'
        return route.fulfill({json:list ? {data:empty ? [] : [...products, {...products[0], id: 20, name:'No publicado',is_available:false}, {...products[0], id:21, name:'Sin inventario',total_stock:0}],categories:[],total_pages:1} : {data:[]}})
      })
      await page.goto('http://localhost:' + (mode === 'before' ? 3000 : 3001) + '/')
      await page.getByRole('heading', {name:'Calentador de paso', exact:true}).waitFor()
      if (mode === 'after') {
        assert.equal(await page.getByText('No publicado', {exact:true}).count(),0)
        assert.equal(await page.getByText('Sin inventario', {exact:true}).count(),0)
        const product = await page.getByRole('heading',{name:'Productos disponibles'}).boundingBox()
        const categories = await page.getByRole('heading',{name:'Explora por categoría'}).boundingBox()
        const services = await page.getByRole('heading',{name:'Nuestros Servicios'}).boundingBox()
        assert(product.y < categories.y && categories.y < services.y)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
        assert.deepEqual(errors, [])
      }
      await page.screenshot({path:'/qa/' + mode + '-' + width + '.png', animations:'disabled'})
      if (mode === 'after') {
        empty = true
        await page.reload()
        await page.getByText('No hay productos disponibles en este momento.', {exact:true}).waitFor()
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
      }
      console.log('PASS ' + mode + ' ' + width)
      await page.close()
    }
  } finally { await browser.close() }
})().catch(error => {console.error(error); process.exitCode=1})
