export interface Product {
  id: string
  name: string
  description: string
  price: number
  originalPrice?: number
  category: string
  brand: string
  images: string[]
  rating: number
  reviewsCount: number
  stock: number
  specifications: Record<string, string>
  isAvailable: boolean
  isFeatured?: boolean
  discount?: number
}

export interface Category {
  id: string
  name: string
  slug: string
  icon: string
  productCount: number
}

export interface CartItem {
  product: Product
  quantity: number
}

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'operator' | 'client'
  phone?: string
  address?: string
}

export interface Order {
  id: string
  userId: string
  items: CartItem[]
  total: number
  status: 'pending' | 'paid' | 'preparing' | 'shipping' | 'delivered' | 'installed'
  paymentMethod: string
  shippingAddress: string
  createdAt: string
  updatedAt: string
  trackingHistory: TrackingEvent[]
}

export interface TrackingEvent {
  status: string
  description: string
  timestamp: string
  location?: string
}

export interface FilterOptions {
  category?: string
  brand?: string
  minPrice?: number
  maxPrice?: number
  inStock?: boolean
  sortBy?: 'price-asc' | 'price-desc' | 'rating' | 'newest'
}
