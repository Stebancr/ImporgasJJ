import axios from 'axios'
import { refreshAdminToken } from './admin_token'
import { revokeBrowserSession, isSameBrowserSession } from '../../services/sessionSecurity'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para agregar token de autenticación
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para manejar errores de respuesta
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/token/')) {
      const sentToken = String(error.config?.headers?.Authorization || '').replace(/^Bearer /, '')
      if (sentToken && localStorage.getItem('token') && !isSameBrowserSession(sentToken, localStorage.getItem('token'))) return Promise.reject(error)
      if (error.response?.data?.code === 'SESSION_REVOKED') {
        revokeBrowserSession(sentToken ? { key: 'token', value: sentToken } : undefined)
        return Promise.reject(error)
      }
      if (!error.config?._retried) {
        error.config._retried = true
        const token = await refreshAdminToken()
        if (token) {
          error.config.headers.Authorization = `Bearer ${token}`
          return api(error.config)
        }
      }
      // The editor retains its pending files and reports the expired session inline.
      // Authentication is still enforced by the server; no request is replayed unauthenticated.
      if (/\/products\/(?:\d+\/)?editor$/.test(error.config?.url || '')) {
        return Promise.reject(error)
      }
      revokeBrowserSession(sentToken ? { key: 'token', value: sentToken } : undefined)
    }
    return Promise.reject(error)
  }
)

export default api
