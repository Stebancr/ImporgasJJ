import api from './api'
import type { Location, ApiResponse, PaginatedResponse } from '@/types'

export interface LocationFilters {
  city?: string
  is_active?: boolean
  search?: string
  page?: number
  per_page?: number
}

export interface CreateLocationData {
  name: string
  address: string
  city: string
  phone?: string
  is_active?: boolean
}

export const locationsService = {
  async getAll(filters?: LocationFilters): Promise<PaginatedResponse<Location>> {
    const response = await api.get<PaginatedResponse<Location>>('/locations', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Location> {
    const response = await api.get<ApiResponse<Location>>(`/locations/${id}`)
    return response.data.data
  },

  async create(data: CreateLocationData): Promise<Location> {
    const response = await api.post<ApiResponse<Location>>('/locations', data)
    return response.data.data
  },

  async update(id: number, data: Partial<CreateLocationData>): Promise<Location> {
    const response = await api.put<ApiResponse<Location>>(`/locations/${id}`, data)
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/locations/${id}`)
  },

  async toggleActive(id: number): Promise<Location> {
    const response = await api.patch<ApiResponse<Location>>(`/locations/${id}/toggle-active`)
    return response.data.data
  },
}

export default locationsService
