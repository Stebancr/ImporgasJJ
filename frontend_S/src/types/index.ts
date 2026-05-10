// User Types
export interface User {
  id: number
  email: string
  name: string
  phone: string
  address: string
  role: 'admin' | 'operator' | 'client'
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  last_login: string | null
  created_at: string
  updated_at: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  name: string
  password: string
  phone?: string
  address?: string
}

// Brand Types
export interface Brand {
  id: number
  name: string
  slug: string
  logo: string
  description: string
  is_active: boolean
  created_at: string
}

// Category Types
export interface Category {
  id: number
  name: string
  slug: string
  icon: string
  description: string
  parent_id: number | null
  order: number
  is_active: boolean
  created_at: string
}

// Location Types
export interface Location {
  id: number
  name: string
  address: string
  city: string
  phone: string
  is_active: boolean
  created_at: string
}

// Spec Attribute Types
export interface SpecAttribute {
  id: number
  name: string
  slug: string
  unit: string
  description: string
  order: number
}

// Product Types
export interface Product {
  id: number
  name: string
  slug: string
  description: string
  price: number
  original_price: number | null
  category_id: number
  brand_id: number
  total_stock: number
  is_available: boolean
  is_featured: boolean
  rating: number
  reviews_count: number
  created_at: string
  updated_at: string
  category?: Category
  brand?: Brand
  images?: ProductImage[]
  specs?: ProductSpec[]
  stock?: ProductStock[]
}

export interface ProductImage {
  id: number
  product_id: number
  image: string
  alt_text: string
  is_primary: boolean
  order: number
}

export interface ProductStock {
  id: number
  product_id: number
  location_id: number
  quantity: number
  updated_at: string
  location?: Location
}

export interface ProductSpec {
  id: number
  product_id: number
  attribute_id: number
  value: string
  order: number
  attribute?: SpecAttribute
}

// Review Types
export interface Review {
  id: number
  product_id: number
  user_id: number
  rating: number
  title: string
  comment: string
  created_at: string
  updated_at: string
  user?: User
}

// Order Types
export type OrderStatus = 'pending' | 'paid' | 'preparing' | 'shipping' | 'delivered' | 'installed'

export interface Order {
  id: number
  user_id: number
  total: number
  status: OrderStatus
  payment_method: string
  shipping_address: string
  created_at: string
  updated_at: string
  user?: User
  items?: OrderItem[]
  tracking_events?: TrackingEvent[]
}

export interface OrderItem {
  id: number
  order_id: number
  product_id: number
  quantity: number
  unit_price: number
  product?: Product
}

export interface TrackingEvent {
  id: number
  order_id: number
  status: OrderStatus
  description: string
  location: string
  timestamp: string
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Auth Context Types
export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}
