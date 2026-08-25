import api from './api'

export interface Favorite {
  id: number
  product: {
    id: string
    name: string
    slug: string
    price: number
    original_price?: number
    discount_percentage: number
    category_id: number
    category_name: string
    brand_id: number
    brand_name: string
    total_stock: number
    is_available: boolean
    is_featured: boolean
    rating: number
    reviews_count: number
    primary_image: string | null
    created_at: string
  }
  created_at: string
}

class FavoritesService {
  async getAll(): Promise<Favorite[]> {
    const response = await api.get<{ data: Favorite[] }>('/ecommerce/user/favorites')
    return response.data
  }

  async add(productId: number): Promise<Favorite> {
    const response = await api.post<{ data: Favorite }>('/ecommerce/user/favorites', {
      product_id: productId,
    })
    return response.data
  }

  async remove(id: number): Promise<void> {
    await api.delete(`/ecommerce/user/favorites/${id}`)
  }

  async removeByProduct(productId: number): Promise<void> {
    await api.delete(`/ecommerce/user/favorites/product/${productId}`)
  }
}

export default new FavoritesService()
