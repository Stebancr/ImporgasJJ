import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/services/wompiCheckout.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } })
const { getWompiOptions, getWompiCheckoutUrl } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const intent = { total: '150000.25', wompi_reference: 'BACKEND-REF', wompi_public_key: 'pub_test_backend', wompi_signature: 'a'.repeat(64) }

test('uses the exact server amount, reference and public key', () => {
  const options = getWompiOptions(intent, 'pub_prod_wrong', 'qa@example.test', 'Prueba')
  assert.equal(options.amountInCents, 15000025)
  assert.equal(options.reference, 'BACKEND-REF')
  assert.equal(options.publicKey, 'pub_test_backend')
  assert.equal(options.signature.integrity, intent.wompi_signature)
  assert.equal(options.currency, 'COP')
})
test('refuses unsigned or invalid amounts before opening payment', () => {
  for (const change of [{total:'NaN'}, {total:'0'}, {total:'-1'}, {wompi_signature:''}, {wompi_reference:''}]) {
    assert.throws(() => getWompiOptions({...intent,...change}, '', '', ''))
  }
})
test('refuses placeholder or missing public keys', () => {
  assert.throws(() => getWompiOptions({...intent,wompi_public_key:''}, 'pub_test_YOUR_KEY_HERE', '', ''))
  assert.throws(() => getWompiOptions({...intent,wompi_public_key:''}, '', '', ''))
})

test('hosted checkout preserves signed values and the public return URL', () => {
  const url = new URL(getWompiCheckoutUrl(getWompiOptions(intent, '', 'qa@example.test', 'QA'), 'https://shop.example/checkout/resultado?tracking=123'))
  assert.equal(url.searchParams.get('amount-in-cents'), '15000025')
  assert.equal(url.searchParams.get('signature:integrity'), intent.wompi_signature)
  assert.equal(url.searchParams.get('customer-data:email'), 'qa@example.test')
  assert.equal(url.searchParams.get('redirect-url'), 'https://shop.example/checkout/resultado?tracking=123')
  assert.equal(new URL(getWompiCheckoutUrl(getWompiOptions(intent, '', '', ''))).searchParams.has('redirect-url'), false)
})
