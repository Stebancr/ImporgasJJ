import { User } from '../types'
import api from './api'

interface LoginCredentials {
  email: string
  password: string
}

interface RegisterData {
  name: string
  email: string
  password: string
  cc: string
  phone?: string
}

interface TokenResponse {
  access: string
  refresh: string
  is_admin: number
}

interface AuthResponse {
  user: User
  token: string
}

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // Backend USERNAME_FIELD='usuario' — map email → usuario
    const response = await api.post<TokenResponse>('/auth/token/', {
      usuario: credentials.email,
      password: credentials.password,
    })
    localStorage.setItem('authToken', response.access)
    localStorage.setItem('refreshToken', response.refresh)
    return { user: {} as User, token: response.access }
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    // Use full email as 'usuario' so the user can log in with their email
    await api.post<{ mensaje: string; usuario_id: number }>('/user/registerUsers', {
      usuario: data.email,
      password: data.password,
      cedula: data.cc,
      nombre_completo: data.name.trim(),
      correo: data.email,
      telefono: data.phone || '',
    })
    return { user: {} as User, token: '' }
  },

  logout: () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  },

  getCurrentUser: async (): Promise<User> => {
    return api.get<User>('/user/perfil/')
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    return api.put<User>('/user/perfil/', data)
  },
}

export default authService
