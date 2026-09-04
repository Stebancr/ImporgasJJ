import api from './api'

export interface Review {
  id: number
  product_id: number
  user_id: number
  user_name: string
  is_owner: boolean
  rating: number
  title: string
  comment: string
  created_at: string
  updated_at: string
}

interface ReviewListResponse { data: Review[]; total: number; page: number; per_page: number }

export const reviewsService = {
  list: (productId: number) => api.get<ReviewListResponse>(`/products/${productId}/reviews?per_page=100`),
  create: (productId: number, data: { rating: number; comment: string; title?: string }) =>
    api.post<{ data: Review }>(`/products/${productId}/reviews`, data),
  update: (productId: number, reviewId: number, data: { rating: number; comment: string }) =>
    api.patch<{ data: Review }>(`/products/${productId}/reviews/${reviewId}`, data),
  remove: (productId: number, reviewId: number) => api.delete<void>(`/products/${productId}/reviews/${reviewId}`),
}
