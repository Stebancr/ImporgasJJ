import axios from 'axios'
import { refreshAdminToken } from './admin_token'

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
      if (!error.config?._retried) {
        error.config._retried = true
        const token = await refreshAdminToken()
        if (token) {
          error.config.headers.Authorization = `Bearer ${token}`
          return api(error.config)
        }
      }
      localStorage.removeItem('token')
      localStorage.removeItem('adminUser')
      localStorage.removeItem('refresh')
      window.dispatchEvent(new Event('admin:logout'))
    }
    return Promise.reject(error)
  }
)

export default api
