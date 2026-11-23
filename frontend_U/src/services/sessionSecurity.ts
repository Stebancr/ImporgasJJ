const credentialKeys = ['authToken', 'refreshToken', 'user', 'token', 'refresh', 'adminUser']
export const revokedMessage = 'La plataforma fue actualizada. Por seguridad, inicia sesión nuevamente.'

export function revokeBrowserSession(expected?: { key: string; value: string }): void {
  if (expected && localStorage.getItem(expected.key) !== expected.value) return
  const hadCredentials = credentialKeys.some(key => localStorage.getItem(key))
  credentialKeys.forEach(key => localStorage.removeItem(key))
  if (!hadCredentials && sessionStorage.getItem('auth:revoked')) return
  sessionStorage.setItem('auth:revoked', '1')
  localStorage.setItem('auth:revocation', String(Date.now()))
  window.dispatchEvent(new Event('session:revoked'))
  window.dispatchEvent(new Event('auth:logout'))
  window.dispatchEvent(new Event('admin:logout'))
}

window.addEventListener('storage', event => {
  if (event.key === 'auth:revocation') revokeBrowserSession()
})
