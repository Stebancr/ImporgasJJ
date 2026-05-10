import api from './api'
import type { Brand, ApiResponse, PaginatedResponse } from '@/types'

export interface BrandFilters {
  is_active?: boolean
  search?: string
  page?: number
  per_page?: number
}

export interface CreateBrandData {
  name: string
  slug: string
  logo?: string
  description?: string
  is_active?: boolean
}

export const brandsService = {
  async getAll(filters?: BrandFilters): Promise<PaginatedResponse<Brand>> {
    const response = await api.get<PaginatedResponse<Brand>>('/brands', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Brand> {
    const response = await api.get<ApiResponse<Brand>>(`/brands/${id}`)
    return response.data.data
  },

  async create(data: CreateBrandData): Promise<Brand> {
    const response = await api.post<ApiResponse<Brand>>('/brands', data)
    return response.data.data
  },

  async update(id: number, data: Partial<CreateBrandData>): Promise<Brand> {
    const response = await api.put<ApiResponse<Brand>>(`/brands/${id}`, data)
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/brands/${id}`)
  },

  async toggleActive(id: number): Promise<Brand> {
    const response = await api.patch<ApiResponse<Brand>>(`/brands/${id}/toggle-active`)
    return response.data.data
  },
}

export default brandsService
