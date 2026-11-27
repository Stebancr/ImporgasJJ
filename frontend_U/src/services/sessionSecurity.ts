const credentialKeys = ['authToken', 'refreshToken', 'user', 'token', 'refresh', 'adminUser']
export const revokedMessage = 'Tu sesión expiró o fue cerrada por una actualización de seguridad. Inicia sesión nuevamente.'

export function safeLoginReturn(path: string | null | undefined, admin = false): string {
  const fallback = admin ? '/admin/dashboard' : '/'
  if (!path?.startsWith('/') || path.startsWith('//') || path.includes('\\')
    || Array.from(path).some(char => char.charCodeAt(0) <= 32 || char.charCodeAt(0) === 127)) return fallback
  try {
    const url = new URL(path, window.location.origin)
    if (url.origin !== window.location.origin) return fallback
    const pathname = decodeURIComponent(url.pathname)
    if (pathname.startsWith('//') || pathname.includes('\\')) return fallback
    const isAdmin = /^\/admin(?:\/|$)/i.test(pathname)
    if (admin !== isAdmin || /^\/(?:admin\/)?login(?:\/|$)/i.test(pathname)) return fallback
    return url.pathname + url.search + url.hash
  } catch { return fallback }
}

// Race protection only. Claims here never authorize a request; the server verifies them.
export function isSameBrowserSession(previous: string, current: string | null): boolean {
  if (!current) return false
  if (previous === current) return true
  try {
    const decode = (token: string) => JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    const before = decode(previous), after = decode(current)
    return typeof before.session_id === 'string' && !!before.session_id && before.session_id === after.session_id
      && before.user_id !== undefined && String(before.user_id) === String(after.user_id)
      && Number.isInteger(before.global_auth_version) && before.global_auth_version === after.global_auth_version
      && Number.isInteger(before.password_version) && before.password_version === after.password_version
  } catch { return false }
}

export function revokeBrowserSession(expected?: { key: string; value: string }, broadcast = true): void {
  if (expected && !isSameBrowserSession(expected.value, localStorage.getItem(expected.key))) return
  const hadCredentials = credentialKeys.some(key => localStorage.getItem(key))
  if (!hadCredentials && sessionStorage.getItem('auth:revoked')) return
  sessionStorage.setItem('auth:revoked', '1')
  // Notify other tabs before their token-removal listeners unmount editors.
  if (broadcast) localStorage.setItem('auth:revocation', String(Date.now()))
  credentialKeys.forEach(key => localStorage.removeItem(key))
  window.dispatchEvent(new Event('session:revoked'))
  window.dispatchEvent(new Event('auth:logout'))
  window.dispatchEvent(new Event('admin:logout'))
}

window.addEventListener('storage', event => {
  if (event.key === 'auth:revocation') revokeBrowserSession(undefined, false)
  else if (event.key === 'authToken' && event.newValue === null) window.dispatchEvent(new Event('auth:logout'))
})
