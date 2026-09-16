import api from './admin_api'
import type { User, LoginCredentials, RegisterData } from '@/admin/types'

export interface PublicRegisterData {
  usuario: string
  password: string
  cedula: string
  nombre_completo: string
  tipo_usuario?: number
  correo?: string | null
  telefono?: string | null
  sede?: string | null
  cargo?: number | null
  nivel?: number | null
  regional?: number | null
}

interface TokenResponse {
  access: string
  refresh: string
  is_admin: number
  location_id: number | null
  location_name: string | null
}

interface PerfilResponse {
  tipo_usuario: number
  location_id: number | null
  location_name: string | null
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

function mapPerfilToUser(
  perfil: PerfilResponse,
  email: string,
  isAdmin: number,
  locationId: number | null = null,
  locationName: string | null = null,
): User {
  return {
    id: perfil.id,
    email,
    name: perfil.nombre_completo,
    phone: perfil.telefono ?? '',
    address: '',
    role: [1, 4].includes(isAdmin) ? 'admin' : 'operator',
    tipo_usuario: isAdmin,
    location_id: locationId,
    location_name: locationName,
    is_active: perfil.estado === 1,
    is_staff: [1, 4].includes(isAdmin),
    is_superuser: isAdmin === 4,
    last_login: null,
    created_at: '',
    updated_at: '',
  }
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const tokenRes = await api.post<TokenResponse>('/auth/token/', credentials)
    const { access, refresh, is_admin, location_id, location_name } = tokenRes.data

    // Store tokens so the request interceptor sends Authorization header on the next call
    localStorage.setItem('token', access)
    localStorage.setItem('refresh', refresh)

    const perfilRes = await api.get<PerfilResponse>('/user/perfil')
    const user = mapPerfilToUser(perfilRes.data, credentials.usuario, is_admin, location_id ?? null, location_name ?? null)

    if (!user.is_active || user.role !== 'admin') {
      this.clearAuth()
      throw new Error('Esta cuenta no tiene acceso administrativo.')
    }
    return { user, token: access }
  },

  async register(data: RegisterData): Promise<LoginResponse> {
    const tokenRes = await api.post<TokenResponse>('/user/register', data)
    const { access, refresh, is_admin } = tokenRes.data

    localStorage.setItem('token', access)
    localStorage.setItem('refresh', refresh)

    const perfilRes = await api.get<PerfilResponse>('/user/perfil')
    const user = mapPerfilToUser(perfilRes.data, data.email, is_admin)

    return { user, token: access }
  },

  async logout(): Promise<void> {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh')
    localStorage.removeItem('adminUser')
  },

  async getProfile(): Promise<User> {
    const perfilRes = await api.get<PerfilResponse>('/user/perfil')
    const storedUser = this.getStoredUser()
    return mapPerfilToUser(perfilRes.data, storedUser?.email ?? '', perfilRes.data.tipo_usuario, perfilRes.data.location_id, perfilRes.data.location_name)
  },

  async updateProfile(data: Partial<User>): Promise<User> {
    const perfilRes = await api.put<PerfilResponse>('/user/perfil', data)
    const storedUser = this.getStoredUser()
    return mapPerfilToUser(perfilRes.data, storedUser?.email ?? '', perfilRes.data.tipo_usuario, perfilRes.data.location_id, perfilRes.data.location_name)
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.put('/user/cambiar-contrasena/', { currentPassword, newPassword })
  },

  getStoredUser(): User | null {
    const user = localStorage.getItem('adminUser')
    try { return user ? JSON.parse(user) : null } catch { return null }
  },

  getStoredToken(): string | null {
    return localStorage.getItem('token')
  },

  setAuth(user: User, token: string): void {
    localStorage.setItem('adminUser', JSON.stringify(user))
    localStorage.setItem('token', token)
  },

  clearAuth(): void {
    localStorage.removeItem('refresh')
    localStorage.removeItem('adminUser')
    localStorage.removeItem('token')
  },

  isAuthenticated(): boolean {
    return !!this.getStoredToken()
  },

  async publicRegister(data: PublicRegisterData): Promise<{ mensaje: string; usuario_id: number; usuario_rel_id: number }> {
    const response = await api.post('/user/register-public', data)
    return response.data
  },
}

export default authService
