import { writeFileSync } from 'node:fs'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { loadCategoryIcons, categories } from './category-icons-loader.mjs'
const after = await loadCategoryIcons()
const before = await loadCategoryIcons('/evidence/CategoryIcon.before.tsx')
for (const [name, mod] of [['before',before],['after',after]]) {
 const html = categories.map(c => `<article>${renderToStaticMarkup(createElement(mod.CategoryIcon,{slug:c.slug,name:c.icon}))}<span>${c.name}</span></article>`).join('')
 writeFileSync(`/evidence/icons-${name}.html`,`<!doctype html><meta charset="utf-8"><title>ImporGas JJ — ${name}</title><style>*{box-sizing:border-box}body{font:15px system-ui;background:#f6f8fc;color:#001575;margin:0;padding:32px}h1{font-size:24px}main{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}article{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:24px 12px;display:flex;align-items:center;flex-direction:column;gap:16px;min-height:140px;text-align:center}svg{width:40px;height:40px;flex-shrink:0}span{color:#1a1d21;font-weight:600}@media(max-width:700px){main{grid-template-columns:repeat(2,1fr)}}@media(prefers-color-scheme:dark){body{background:#141820;color:#c1cdff}article{background:#232938;border-color:#4a5262}span{color:#f3f4f6}}</style><h1>ImporGas JJ · ${name==='before'?'Antes':'Después'}</h1><main>${html}</main>`)
}
