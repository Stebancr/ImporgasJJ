import api from './admin_api'
import type { User, ApiResponse, PaginatedResponse } from '@/admin/types'

export interface UserFilters {
  role?: 'admin' | 'operator' | 'client'
  is_active?: boolean
  search?: string
  page?: number
  per_page?: number
}

export interface CreateUserData {
  usuario: string
  password: string
  cedula: string
  nombre_completo: string
  correo?: string | null
  telefono?: string | null
  cargo?: number | null
  tipo_usuario?: number
  location_id?: number | null
}

export interface UpdateUserData {
  nombre_completo?: string
  correo?: string | null
  telefono?: string | null
  cargo?: number | null
  location_id?: number | null
}

export interface SelectOption {
  id: number
  nombre: string
}

export interface CargoNivelRegionalData {
  cargos: SelectOption[]
  niveles: SelectOption[]
  regionales: SelectOption[]
}

export interface ColaboradorData {
  id: number
  cedula: string
  nombre_completo: string
  correo: string
  telefono: string
  estado: number
  nombre_cargo: string | null
  cargo: number | null
  usuario: string | null
  tipo_usuario: number
  location_id: number | null
  location_name: string | null
}

export interface ColaboradorListResponse {
  count: number
  page: number
  page_size: number
  results: ColaboradorData[]
}

export const usersService = {
  // ── Legacy generic methods (kept for compatibility) ──────────────────────
  async getAll(filters?: UserFilters): Promise<PaginatedResponse<User>> {
    const response = await api.get<PaginatedResponse<User>>('/users', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<User> {
    const response = await api.get<ApiResponse<User>>(`/users/${id}`)
    return response.data.data
  },

  async create(data: CreateUserData): Promise<User> {
    const response = await api.post<ApiResponse<User>>('/users', data)
    return response.data.data
  },

  async update(id: number, data: UpdateUserData): Promise<User> {
    const response = await api.put<ApiResponse<User>>(`/users/${id}`, data)
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/users/${id}`)
  },

  async toggleActive(id: number): Promise<User> {
    const response = await api.patch<ApiResponse<User>>(`/users/${id}/toggle-active`)
    return response.data.data
  },

  async changeRole(id: number, role: 'admin' | 'operator' | 'client'): Promise<User> {
    const response = await api.patch<ApiResponse<User>>(`/users/${id}/role`, { role })
    return response.data.data
  },

  async resetPassword(id: number, newPassword: string): Promise<void> {
    await api.patch(`/users/${id}/reset-password`, { password: newPassword })
  },

  // ── Real backend endpoints ────────────────────────────────────────────────

  /** GET /user/lista-usuarios — list colaboradores (admin only) */
  async listarColaboradores(params?: { search?: string; page?: number; page_size?: number; tipo?: 'normal' | 'trabajador' }): Promise<ColaboradorListResponse> {
    const response = await api.get('/user/lista-usuarios', { params })
    return response.data
  },

  /** POST /user/register — create new user (authenticated, admin only) */
  async crearColaborador(data: CreateUserData): Promise<{ mensaje: string; usuario_id: number; usuario_rel_id: number }> {
    const response = await api.post('/user/register', data)
    return response.data
  },

  /** GET /user/register/<id> — get colaborador detail */
  async getColaborador(usuarioRelId: number): Promise<ColaboradorData> {
    const response = await api.get(`/user/register/${usuarioRelId}`)
    return response.data
  },

  /** PUT /user/register/<id> — update colaborador profile data */
  async actualizarColaborador(usuarioRelId: number, data: UpdateUserData): Promise<ColaboradorData> {
    const response = await api.put(`/user/register/${usuarioRelId}`, data)
    return response.data
  },

  /** PATCH /user/cambiar-estado-usuario/<id> — toggle active/inactive */
  async cambiarEstado(usuarioRelId: number, estado: 0 | 1): Promise<void> {
    await api.patch(`/user/cambiar-estado-usuario/${usuarioRelId}`, { estado })
  },

  /** PATCH /user/actualizar-rol-usuario/<id> — change tipo_usuario */
  async actualizarRol(usuarioRelId: number, tipo_usuario: number): Promise<void> {
    await api.patch(`/user/actualizar-rol-usuario/${usuarioRelId}`, { tipo_usuario })
  },

  /** GET/POST /user/cargos — list and create cargos */
  async getCargos(): Promise<{ idcargo: number; nombrecargo: string }[]> {
    const res = await api.get('/user/cargos')
    return res.data
  },

  async createCargo(nombre: string): Promise<{ idcargo: number; nombrecargo: string }> {
    const res = await api.post('/user/cargos', { nombrecargo: nombre })
    return res.data
  },

  async updateCargo(id: number, nombre: string): Promise<{ idcargo: number; nombrecargo: string }> {
    const res = await api.put(`/user/cargos/${id}`, { nombrecargo: nombre })
    return res.data
  },

  async deleteCargo(id: number): Promise<void> {
    await api.delete(`/user/cargos/${id}`)
  },

  async getCargoNivelRegional(): Promise<CargoNivelRegionalData> {
    const response = await api.get('/user/cargo-nivel-regional')
    const data = response.data
    return {
      cargos: (data.cargos ?? []).map((c: { idcargo: number; nombrecargo: string }) => ({ id: c.idcargo, nombre: c.nombrecargo })),
      niveles: (data.niveles ?? []).map((n: { idnivel: number; nombrenivel: string }) => ({ id: n.idnivel, nombre: n.nombrenivel })),
      regionales: (data.regionales ?? []).map((r: { idregional: number; nombreregional: string }) => ({ id: r.idregional, nombre: r.nombreregional })),
    }
  },
}

export default usersService

