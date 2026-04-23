import { User } from '../types'
import api from './api'

interface LoginCredentials {
  email: string
  password: string
}

interface RegisterData extends LoginCredentials {
  name: string
  phone?: string
}

interface AuthResponse {
  user: User
  token: string
}

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/login', credentials)
    localStorage.setItem('authToken', response.token)
    return response
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/register', data)
    localStorage.setItem('authToken', response.token)
    return response
  },

  logout: () => {
    localStorage.removeItem('authToken')
  },

  getCurrentUser: async (): Promise<User> => {
    return api.get<User>('/auth/me')
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    return api.put<User>('/auth/profile', data)
  },

  forgotPassword: async (email: string): Promise<void> => {
    await api.post('/auth/forgot-password', { email })
  },

  resetPassword: async (token: string, password: string): Promise<void> => {
    await api.post('/auth/reset-password', { token, password })
  },
}

export default authService
