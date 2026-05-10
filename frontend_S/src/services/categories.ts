import api from './api'
import type { Category, ApiResponse, PaginatedResponse } from '@/types'

export interface CategoryFilters {
  is_active?: boolean
  parent_id?: number | null
  search?: string
  page?: number
  per_page?: number
}

export interface CreateCategoryData {
  name: string
  slug: string
  icon?: string
  description?: string
  parent_id?: number | null
  order?: number
  is_active?: boolean
}

export const categoriesService = {
  async getAll(filters?: CategoryFilters): Promise<PaginatedResponse<Category>> {
    const response = await api.get<PaginatedResponse<Category>>('/categories', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Category> {
    const response = await api.get<ApiResponse<Category>>(`/categories/${id}`)
    return response.data.data
  },

  async create(data: CreateCategoryData): Promise<Category> {
    const response = await api.post<ApiResponse<Category>>('/categories', data)
    return response.data.data
  },

  async update(id: number, data: Partial<CreateCategoryData>): Promise<Category> {
    const response = await api.put<ApiResponse<Category>>(`/categories/${id}`, data)
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/categories/${id}`)
  },

  async toggleActive(id: number): Promise<Category> {
    const response = await api.patch<ApiResponse<Category>>(`/categories/${id}/toggle-active`)
    return response.data.data
  },

  async getTree(): Promise<Category[]> {
    const response = await api.get<ApiResponse<Category[]>>('/categories/tree')
    return response.data.data
  },
}

export default categoriesService
