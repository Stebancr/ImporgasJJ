import tsParser from '@typescript-eslint/parser'

export default [{
  ignores: ['dist/**', 'node_modules/**', 'tests/**'],
}, {
  files: ['src/**/*.{ts,tsx}'],
  languageOptions: {parser: tsParser, ecmaVersion: 'latest', sourceType: 'module', parserOptions: {ecmaFeatures: {jsx: true}}},
  rules: {
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    'no-debugger': 'error',
    'no-unreachable': 'error',
    'no-unsafe-finally': 'error',
    'no-constant-binary-expression': 'error',
    'valid-typeof': 'error',
  },
}]
