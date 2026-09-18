import type { User } from '../types'
import api from './api'

interface LoginCredentials { email: string; password: string }
interface RegisterData { name: string; email: string; password: string; cc: string; phone?: string; termsVersion: string; termsAccepted: boolean }
interface TokenResponse {
  access: string
  refresh: string
  is_admin: number
  location_id: number | null
  location_name: string | null
}
interface ProfileResponse {
  id: number
  nombre_completo: string
  correo: string | null
  telefono: string | null
  estado: number
  terms_version: string
  terms_accepted_at: string | null
  current_terms_version: string
}
interface AuthResponse { user: User; token: string }

function mapUser(profile: ProfileResponse, username: string, token: TokenResponse): User {
  return {
    id: String(profile.id),
    email: profile.correo || username,
    name: profile.nombre_completo,
    role: token.is_admin > 0 ? 'admin' : 'client',
    phone: profile.telefono || '',
    tipo_usuario: token.is_admin,
    location_id: token.location_id,
    location_name: token.location_name,
    is_active: profile.estado === 1,
    is_staff: token.is_admin > 0,
    is_superuser: token.is_admin === 4,
    terms_version: profile.terms_version,
    terms_accepted_at: profile.terms_accepted_at,
    current_terms_version: profile.current_terms_version,
    usuario_rel: {
      nombre_completo: profile.nombre_completo,
      correo: profile.correo || username,
      telefono: profile.telefono || '',
    },
  }
}

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const token = await api.post<TokenResponse>('/auth/token/', {
      usuario: credentials.email,
      password: credentials.password,
    })
    localStorage.setItem('authToken', token.access)
    localStorage.setItem('refreshToken', token.refresh)
    const profile = await api.get<ProfileResponse>('/user/perfil')
    const user = mapUser(profile, credentials.email, token)
    localStorage.setItem('user', JSON.stringify(user))
    return { user, token: token.access }
  },
  register: async (data: RegisterData): Promise<void> => {
    await api.post('/user/registerUsers', {
      usuario: data.email,
      password: data.password,
      cedula: data.cc,
      nombre_completo: data.name.trim(),
      correo: data.email,
      telefono: data.phone || '',
      terms_accepted: data.termsAccepted,
      terms_version: data.termsVersion,
    })
  },
  logout: () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  },
  getStoredUser: (): User | null => {
    const raw = localStorage.getItem('user')
    if (!raw) return null
    try { return JSON.parse(raw) as User } catch { localStorage.removeItem('user'); return null }
  },
  getCurrentUser: async (): Promise<User> => {
    const stored = authService.getStoredUser()
    if (stored) {
      const profile = await api.get<ProfileResponse>('/user/perfil')
      if (profile.estado !== 1) throw new Error('La cuenta no está activa')
      const user = { ...stored, name: profile.nombre_completo, email: profile.correo || stored.email, phone: profile.telefono || '', is_active: true,
        usuario_rel: { nombre_completo: profile.nombre_completo, correo: profile.correo || stored.email, telefono: profile.telefono || '' },
        terms_version: profile.terms_version, terms_accepted_at: profile.terms_accepted_at, current_terms_version: profile.current_terms_version }
      localStorage.setItem('user', JSON.stringify(user))
      return user
    }
    throw new Error('No hay una sesión autenticada')
  },
  updateProfile: async (data: Partial<User>): Promise<User> => api.put<User>('/user/perfil/', data),
}

export default authService
