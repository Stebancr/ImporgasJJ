const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: unknown
  headers?: Record<string, string>
}

function errorMessage(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(errorMessage).filter(Boolean).join(' ')
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    if (typeof record.message === 'string') return record.message
    if (typeof record.error === 'string') return record.error
    return Object.entries(record)
      .map(([field, detail]) => `${field}: ${errorMessage(detail)}`)
      .filter((part) => !part.endsWith(': '))
      .join(' ')
  }
  return ''
}

// Flag to prevent multiple simultaneous refresh attempts
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refreshToken')
  if (!refreshToken) return null

  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    })
    if (!response.ok) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event('auth:logout'))
      return null
    }
    const data = await response.json()
    localStorage.setItem('authToken', data.access)
    return data.access
  } catch {
    localStorage.removeItem('authToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
    window.dispatchEvent(new Event('auth:logout'))
    return null
  }
}

function buildConfig(method: string, body: unknown, headers: Record<string, string>, token: string | null): RequestInit {
  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }
  if (body) config.body = JSON.stringify(body)
  if (token) {
    config.headers = { ...config.headers, Authorization: `Bearer ${token}` }
  }
  return config
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const token = localStorage.getItem('authToken')
  const config = buildConfig(method, body, headers, token)

  let response = await fetch(`${API_BASE_URL}${endpoint}`, config)

  // If 401 and we have a refresh token, try to refresh and retry once
  if (response.status === 401 && localStorage.getItem('refreshToken')) {
    let newToken: string | null = null

    if (!isRefreshing) {
      isRefreshing = true
      newToken = await tryRefreshToken()
      isRefreshing = false
      if (newToken) onRefreshed(newToken)
    } else {
      // Wait for the ongoing refresh to finish
      newToken = await new Promise<string | null>(resolve => {
        refreshSubscribers.push(resolve)
      })
    }

    if (newToken) {
      const retryConfig = buildConfig(method, body, headers, newToken)
      response = await fetch(`${API_BASE_URL}${endpoint}`, retryConfig)
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Error de conexión' }))
    throw new Error(errorMessage(error) || 'Error en la solicitud')
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, body: unknown) => request<T>(endpoint, { method: 'POST', body }),
  put: <T>(endpoint: string, body: unknown) => request<T>(endpoint, { method: 'PUT', body }),
  patch: <T>(endpoint: string, body: unknown) => request<T>(endpoint, { method: 'PATCH', body }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
}

export default api
