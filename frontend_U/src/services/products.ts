import { Product, FilterOptions } from '../types'
import api from './api'

// ── API response shapes ────────────────────────────────────────────────────

interface ApiImage {
  id: number
  image: string
  image_url: string | null
  alt_text: string
  is_primary: boolean
  order: number
}

interface ApiProduct {
  id: number
  name: string
  slug: string
  description: string
  price: number
  original_price: number | null
  discount_percentage: number
  category_id: number
  category_name?: string
  category?: { id: number; name: string; slug: string }
  brand_id: number
  brand_name?: string
  brand?: { id: number; name: string; slug: string }
  total_stock: number
  is_available: boolean
  is_featured: boolean
  rating: number
  reviews_count: number
  images?: ApiImage[]
  specifications?: { attribute_name: string; value: string; attribute_unit: string }[]
  primary_image?: string | null
}

interface PaginatedResponse {
  data: ApiProduct[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// ── Transform API → legacy Product type ────────────────────────────────────

function toProduct(p: ApiProduct): Product {
  const imageUrls = p.images?.map(i => i.image_url || i.image) ||
    (p.primary_image ? [p.primary_image] : [])

  const specs: Record<string, string> = {}
  p.specifications?.forEach(s => {
    specs[s.attribute_name] = s.attribute_unit ? `${s.value} ${s.attribute_unit}` : s.value
  })

  return {
    id: String(p.id),
    name: p.name,
    description: p.description,
    price: Number(p.price),
    originalPrice: p.original_price ? Number(p.original_price) : undefined,
    category: p.category?.slug || String(p.category_id),
    brand: p.brand?.name || p.brand_name || String(p.brand_id),
    images: imageUrls.length > 0 ? imageUrls : ['https://placehold.co/400x400/f3f4f6/9ca3af?text=Producto'],
    rating: Math.round(Number(p.rating)),
    reviewsCount: p.reviews_count,
    stock: p.total_stock,
    specifications: specs,
    isAvailable: p.is_available,
    isFeatured: p.is_featured,
    discount: p.discount_percentage || undefined,
    slug: p.slug,
  }
}

// ── Service ────────────────────────────────────────────────────────────────

export const productsService = {
  getAll: async (filters?: FilterOptions): Promise<Product[]> => {
    const params = new URLSearchParams()
    params.append('per_page', '100')
    if (filters?.categoryId) params.append('category_id', filters.categoryId.toString())
    if (filters?.brandId) params.append('brand_id', filters.brandId.toString())
    if (filters?.minPrice) params.append('min_price', filters.minPrice.toString())
    if (filters?.maxPrice) params.append('max_price', filters.maxPrice.toString())
    if (filters?.search) params.append('search', filters.search)
    if (filters?.sortBy) params.append('sort', filters.sortBy)
    if (filters?.inStock !== undefined) params.append('is_available', 'true')

    const query = params.toString()
    const res = await api.get<PaginatedResponse>(`/products${query ? `?${query}` : ''}`)
    return res.data.map(toProduct)
  },

  getById: async (id: string): Promise<Product> => {
    const res = await api.get<{ data: ApiProduct }>(`/products/${id}`)
    return toProduct(res.data)
  },

  getBySlug: async (slug: string): Promise<Product> => {
    const res = await api.get<{ data: ApiProduct }>(`/products/slug/${slug}`)
    return toProduct(res.data)
  },

  getFeatured: async (): Promise<Product[]> => {
    const res = await api.get<PaginatedResponse>('/products?is_featured=true&per_page=8')
    if (res.data.length > 0) return res.data.map(toProduct)
    // Fall back to best available products (sorted by rating desc)
    const fallback = await api.get<PaginatedResponse>('/products?is_available=true&per_page=8')
    return fallback.data.map(toProduct)
  },

  getRelated: async (productId: string): Promise<Product[]> => {
    // Fetch products from same category — simplified approach
    const product = await api.get<{ data: ApiProduct }>(`/products/${productId}`)
    const res = await api.get<PaginatedResponse>(
      `/products?category_id=${product.data.category_id}&per_page=4`
    )
    return res.data.filter(p => String(p.id) !== productId).map(toProduct)
  },

  getBestSellers: async (): Promise<Product[]> => {
    const res = await api.get<PaginatedResponse>('/products?is_available=true&per_page=8')
    return res.data.map(toProduct)
  },

  search: async (query: string): Promise<Product[]> => {
    const res = await api.get<PaginatedResponse>(`/products?search=${encodeURIComponent(query)}`)
    return res.data.map(toProduct)
  },
}

export default productsService

