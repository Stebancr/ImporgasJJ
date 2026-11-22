import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { loadCategoryIcons, categories } from './category-icons-loader.mjs'
const { categoryIcons, categoryIconBySlug, resolveCategoryIcon, CategoryIcon } = await loadCategoryIcons()
const render = props => renderToStaticMarkup(createElement(CategoryIcon, props))

test('all 15 production slugs resolve to valid, distinct keys and distinct SVG geometry', () => {
  assert.equal(categories.length, 15)
  assert.deepEqual(Object.keys(categoryIconBySlug), categories.map(c => c.slug))
  const keys = categories.map(c => resolveCategoryIcon(c.slug, c.icon))
  assert.equal(new Set(keys).size, 15)
  for (const key of keys) assert(categoryIcons[key])
  const geometry = categories.map(c => render(c).replace(/class="[^"]*"/g, ''))
  assert.equal(new Set(geometry).size, 15)
})
test('slugs distinguish stored legacy keys consistently and do not mutate category data', () => {
  const before = JSON.stringify(categories)
  assert.notEqual(resolveCategoryIcon('calentadores', 'flame'), resolveCategoryIcon('calefactores', 'flame'))
  assert.notEqual(resolveCategoryIcon('reguladores', 'gauge'), resolveCategoryIcon('manometro', 'gauge'))
  categories.forEach(c => render(c))
  assert.equal(JSON.stringify(categories), before)
})
test('unknown categories preserve configured icons or safely fall back, including hostile property names', () => {
  assert.equal(resolveCategoryIcon('new-category', 'wrench'), 'wrench')
  for (const value of [undefined, '', 'does-not-exist', '__proto__', 'constructor']) {
    assert.equal(resolveCategoryIcon(value, value), undefined)
    assert.match(render({ slug: value, name: value }), /lucide-folder-tree/)
  }
})
test('icons inherit currentColor, consistent stroke, 24x24 viewbox and are decorative', () => {
  for (const c of categories) {
    const svg = render({ ...c, className: 'h-5 w-5' })
    for (const attribute of ['viewBox="0 0 24 24"', 'fill="none"', 'stroke="currentColor"', 'stroke-width="2"', 'stroke-linecap="round"', 'stroke-linejoin="round"', 'aria-hidden="true"', 'focusable="false"']) assert(svg.includes(attribute), c.slug+' '+attribute)
    assert(!/<(?:image|script|foreignObject)|(?:href|src)=/.test(svg))
  }
})
test('home, public desktop/mobile filters and admin use the same slug resolver', () => {
  for (const file of ['../src/app/pages/HomePage.tsx', '../src/app/pages/ProductsPage.tsx', '../src/admin/pages/CategoriesPage.tsx']) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8')
    assert.match(source, /<CategoryIcon slug=\{category.slug\}/)
  }
})
