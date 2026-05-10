import api from './api'
import type { User, LoginCredentials, RegisterData } from '@/types'

interface TokenResponse {
  access: string
  refresh: string
  is_admin: number
}

interface PerfilResponse {
  id: number
  cedula: string
  nombre_completo: string
  correo: string | null
  telefono: string | null
  sede: string | null
  estado: number
  nombre_cargo: string | null
  nombre_nivel: string | null
  nombre_regional: string | null
}

interface LoginResponse {
  user: User
  token: string
}

function mapPerfilToUser(perfil: PerfilResponse, email: string, isAdmin: number): User {
  return {
    id: perfil.id,
    email,
    name: perfil.nombre_completo,
    phone: perfil.telefono ?? '',
    address: '',
    role: isAdmin > 0 ? 'admin' : 'operator',
    is_active: perfil.estado === 1,
    is_staff: isAdmin > 0,
    is_superuser: isAdmin > 1,
    last_login: null,
    created_at: '',
    updated_at: '',
  }
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const tokenRes = await api.post<TokenResponse>('/auth/token/', credentials)
    const { access, refresh, is_admin } = tokenRes.data

    // Store tokens so the request interceptor sends Authorization header on the next call
    localStorage.setItem('token', access)
    localStorage.setItem('refresh', refresh)

    const perfilRes = await api.get<PerfilResponse>('/user/perfil/')
    const user = mapPerfilToUser(perfilRes.data, credentials.email, is_admin)

    return { user, token: access }
  },

  async register(data: RegisterData): Promise<LoginResponse> {
    const tokenRes = await api.post<TokenResponse>('/user/register/', data)
    const { access, refresh, is_admin } = tokenRes.data

    localStorage.setItem('token', access)
    localStorage.setItem('refresh', refresh)

    const perfilRes = await api.get<PerfilResponse>('/user/perfil/')
    const user = mapPerfilToUser(perfilRes.data, data.email, is_admin)

    return { user, token: access }
  },

  async logout(): Promise<void> {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
  },

  async getProfile(): Promise<User> {
    const perfilRes = await api.get<PerfilResponse>('/user/perfil/')
    const storedUser = this.getStoredUser()
    return mapPerfilToUser(perfilRes.data, storedUser?.email ?? '', 0)
  },

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await api.put<PerfilResponse>('/user/perfil/', data)
    const storedUser = this.getStoredUser()
    return mapPerfilToUser(response.data, storedUser?.email ?? '', 0)
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.put('/user/cambiar-contrasena/', { currentPassword, newPassword })
  },

  getStoredUser(): User | null {
    const user = localStorage.getItem('user')
    return user ? JSON.parse(user) : null
  },

  getStoredToken(): string | null {
    return localStorage.getItem('token')
  },

  setAuth(user: User, token: string): void {
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('token', token)
  },

  clearAuth(): void {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
  },

  isAuthenticated(): boolean {
    return !!this.getStoredToken()
  },
}

export default authService
