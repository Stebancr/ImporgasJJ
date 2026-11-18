import { readFileSync } from 'node:fs'
import ts from 'typescript'

export async function loadCategoryIcons(path = new URL('../src/components/CategoryIcon.tsx', import.meta.url)) {
  const source = readFileSync(path, 'utf8').replace(/^\uFEFF/, '')
  let { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX } })
  for (const pkg of ['lucide-react', 'react/jsx-runtime']) {
    outputText = outputText.replaceAll(`"${pkg}"`, JSON.stringify(import.meta.resolve(pkg))).replaceAll(`'${pkg}'`, JSON.stringify(import.meta.resolve(pkg)))
  }
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
}
export const categories = JSON.parse(readFileSync(new URL('./fixtures/category-icons.json', import.meta.url), 'utf8').replace(/^\uFEFF/, ''))
