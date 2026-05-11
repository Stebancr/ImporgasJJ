import api from './api'
import type { User, ApiResponse, PaginatedResponse } from '@/types'

export interface UserFilters {
  role?: 'admin' | 'operator' | 'client'
  is_active?: boolean
  search?: string
  page?: number
  per_page?: number
}

export interface CreateUserData {
  email: string
  name: string
  password: string
  phone?: string
  address?: string
  role?: 'admin' | 'operator' | 'client'
  is_active?: boolean
}

export interface UpdateUserData {
  email?: string
  name?: string
  phone?: string
  address?: string
  role?: 'admin' | 'operator' | 'client'
  is_active?: boolean
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

export const usersService = {
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
