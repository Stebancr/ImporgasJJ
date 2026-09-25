import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

let pendingRefresh: Promise<string | null> | null = null

export function tokenExpiresIn(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return Number(payload.exp) * 1000 - Date.now()
  } catch {
    return 0
  }
}

export function refreshAdminToken(): Promise<string | null> {
  if (pendingRefresh) return pendingRefresh
  const refresh = localStorage.getItem('refresh')
  if (!refresh) return Promise.resolve(null)

  pendingRefresh = axios.post<{ access: string; refresh?: string }>(
    `${API_BASE_URL}/auth/token/refresh/`,
    { refresh },
    { timeout: 20000 },
  ).then(({ data }) => {
    localStorage.setItem('token', data.access)
    if (data.refresh) localStorage.setItem('refresh', data.refresh)
    window.dispatchEvent(new CustomEvent<string>('admin:token-refreshed', { detail: data.access }))
    return data.access
  }).catch(() => null).finally(() => {
    pendingRefresh = null
  })
  return pendingRefresh
}
