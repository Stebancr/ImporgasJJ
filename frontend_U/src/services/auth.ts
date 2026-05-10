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

const DEMO_ADMIN = {
  email: 'admin@gmail.com',
  password: 'admin***',
}

function createDemoAdminUser(): User {
  return {
    id: '1',
    email: DEMO_ADMIN.email,
    name: 'Admin Demo',
    phone: '',
    address: '',
    role: 'admin',
  }
}

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // Demo login: check credentials locally
    if (credentials.email === DEMO_ADMIN.email && credentials.password === DEMO_ADMIN.password) {
      const token = 'fake-token-admin-demo-' + Date.now()
      localStorage.setItem('authToken', token)
      localStorage.setItem('refreshToken', 'fake-refresh-token')
      const user = createDemoAdminUser()
      localStorage.setItem('user', JSON.stringify(user))
      return { user, token }
    }

    // Real login from backend
    const response = await api.post<TokenResponse>('/auth/token/', credentials)
    localStorage.setItem('authToken', response.access)
    localStorage.setItem('refreshToken', response.refresh)
    return { user: {} as User, token: response.access }
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const nameParts = data.name.trim().split(' ')
    const nombre = nameParts[0] || data.name
    const apellido = nameParts.slice(1).join(' ') || '-'
    const usuario = data.email.split('@')[0]

    await api.post<{ mensaje: string; usuario_id: number }>('/user/register/', {
      usuario,
      password: data.password,
      idcolaborador: {
        cc_colaborador: data.cc,
        nombre_colaborador: nombre,
        apellido_colaborador: apellido,
        correo_colaborador: data.email,
        telefo_colaborador: data.phone || '',
      },
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
