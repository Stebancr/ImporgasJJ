/**
 * Axios client with JWT authentication and automatic token refresh.
 *
 * Tokens are stored securely using expo-secure-store.
 * On 401, the client refreshes the access token transparently.
 * On refresh failure, it clears credentials and triggers auth logout.
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import * as SecureStore from 'expo-secure-store'

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Change to your production URL when deploying.
// In development with Expo Go on a physical device, use your computer's LAN IP.
export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'https://v8jsj64l-8000.use.devtunnels.ms'

// Keys used in SecureStore
export const ACCESS_TOKEN_KEY  = 'intagas_access'
export const REFRESH_TOKEN_KEY = 'intagas_refresh'

// ─── Client ───────────────────────────────────────────────────────────────────
const client = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Request interceptor — attach access token ────────────────────────────────
client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Response interceptor — refresh on 401 ────────────────────────────────────
let _logoutCallback: (() => void) | null = null
let _isRefreshing = false
let _pendingQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null) => {
  _pendingQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token!)
  )
  _pendingQueue = []
}

export function setLogoutCallback(cb: () => void) {
  _logoutCallback = cb
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // Skip refresh for token endpoints themselves
    if (
      originalRequest.url?.includes('/auth/token/') ||
      originalRequest.url?.includes('/auth/token/refresh/')
    ) {
      _logoutCallback?.()
      return Promise.reject(error)
    }

    if (_isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        _pendingQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return client(originalRequest)
        })
        .catch((err) => Promise.reject(err))
    }

    originalRequest._retry = true
    _isRefreshing = true

    try {
      const refresh = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY)
      if (!refresh) throw new Error('No refresh token')

      const { data } = await axios.post<{ access: string }>(
        `${API_BASE}/auth/token/refresh/`,
        { refresh },
        { headers: { 'Content-Type': 'application/json' } },
      )

      await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, data.access)
      client.defaults.headers.Authorization = `Bearer ${data.access}`
      processQueue(null, data.access)

      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return client(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY)
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY)
      _logoutCallback?.()
      return Promise.reject(refreshError)
    } finally {
      _isRefreshing = false
    }
  },
)

export default client
