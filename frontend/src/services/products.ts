import { Product, FilterOptions } from '../types'
import api from './api'

export const productsService = {
  getAll: async (filters?: FilterOptions): Promise<Product[]> => {
    const params = new URLSearchParams()
    
    if (filters?.category) params.append('category', filters.category)
    if (filters?.brand) params.append('brand', filters.brand)
    if (filters?.minPrice) params.append('minPrice', filters.minPrice.toString())
    if (filters?.maxPrice) params.append('maxPrice', filters.maxPrice.toString())
    if (filters?.inStock !== undefined) params.append('inStock', filters.inStock.toString())
    if (filters?.sortBy) params.append('sortBy', filters.sortBy)

    const query = params.toString()
    return api.get<Product[]>(`/products${query ? `?${query}` : ''}`)
  },

  getById: async (id: string): Promise<Product> => {
    return api.get<Product>(`/products/${id}`)
  },

  getFeatured: async (): Promise<Product[]> => {
    return api.get<Product[]>('/products/featured')
  },

  getRelated: async (productId: string): Promise<Product[]> => {
    return api.get<Product[]>(`/products/${productId}/related`)
  },

  getBestSellers: async (): Promise<Product[]> => {
    return api.get<Product[]>('/products/best-sellers')
  },

  search: async (query: string): Promise<Product[]> => {
    return api.get<Product[]>(`/products/search?q=${encodeURIComponent(query)}`)
  },
}

export default productsService
