import api from './api'
import type { Product, ProductImage, ProductSpec, ProductStock, ApiResponse, PaginatedResponse } from '@/types'

export interface ProductFilters {
  category_id?: number
  brand_id?: number
  is_available?: boolean
  is_featured?: boolean
  min_price?: number
  max_price?: number
  search?: string
  page?: number
  per_page?: number
}

export interface CreateProductData {
  name: string
  slug: string
  description: string
  price: number
  original_price?: number
  category_id: number
  brand_id: number
  is_available?: boolean
  is_featured?: boolean
}

export const productsService = {
  async getAll(filters?: ProductFilters): Promise<PaginatedResponse<Product>> {
    const response = await api.get<PaginatedResponse<Product>>('/products', { params: filters })
    return response.data
  },

  async getById(id: number): Promise<Product> {
    const response = await api.get<ApiResponse<Product>>(`/products/${id}`)
    return response.data.data
  },

  async getBySlug(slug: string): Promise<Product> {
    const response = await api.get<ApiResponse<Product>>(`/products/slug/${slug}`)
    return response.data.data
  },

  async create(data: CreateProductData): Promise<Product> {
    const response = await api.post<ApiResponse<Product>>('/products', data)
    return response.data.data
  },

  async update(id: number, data: Partial<CreateProductData>): Promise<Product> {
    const response = await api.put<ApiResponse<Product>>(`/products/${id}`, data)
    return response.data.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/products/${id}`)
  },

  // Product Images
  async addImage(productId: number, image: File, isPrimary?: boolean): Promise<ProductImage> {
    const formData = new FormData()
    formData.append('image', image)
    if (isPrimary) formData.append('is_primary', 'true')
    
    const response = await api.post<ApiResponse<ProductImage>>(`/products/${productId}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data.data
  },

  async deleteImage(productId: number, imageId: number): Promise<void> {
    await api.delete(`/products/${productId}/images/${imageId}`)
  },

  // Product Specs
  async addSpec(productId: number, attributeId: number, value: string): Promise<ProductSpec> {
    const response = await api.post<ApiResponse<ProductSpec>>(`/products/${productId}/specs`, {
      attribute_id: attributeId,
      value,
    })
    return response.data.data
  },

  async updateSpec(productId: number, specId: number, value: string): Promise<ProductSpec> {
    const response = await api.put<ApiResponse<ProductSpec>>(`/products/${productId}/specs/${specId}`, { value })
    return response.data.data
  },

  async deleteSpec(productId: number, specId: number): Promise<void> {
    await api.delete(`/products/${productId}/specs/${specId}`)
  },

  // Product Stock
  async updateStock(productId: number, locationId: number, quantity: number): Promise<ProductStock> {
    const response = await api.put<ApiResponse<ProductStock>>(`/products/${productId}/stock`, {
      location_id: locationId,
      quantity,
    })
    return response.data.data
  },

  async getStock(productId: number): Promise<ProductStock[]> {
    const response = await api.get<ApiResponse<ProductStock[]>>(`/products/${productId}/stock`)
    return response.data.data
  },

  // Search
  async search(query: string): Promise<Product[]> {
    const response = await api.get<ApiResponse<Product[]>>('/products/search', { params: { q: query } })
    return response.data.data
  },
}

export default productsService
