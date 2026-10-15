import api from './api'

export interface ShippingProfile {
  requires_shipping: boolean
  weight_kg: string | null
  height_cm: string | null
  width_cm: string | null
  length_cm: string | null
  packages_per_unit: number | null
  declared_value: string | null
  packaging_code: string
  fragile: boolean
}
export const emptyShippingProfile: ShippingProfile = { requires_shipping: true, weight_kg: null, height_cm: null,
  width_cm: null, length_cm: null, packages_per_unit: 1, declared_value: null, packaging_code: 'CLEM_CAJA', fragile: false }

export interface TCCCity { code: string; city: string; department: string }
export interface ShippingQuote {
  id: string; carrier: string; tcc_rate: string; surcharge: string; total: string; subtotal: string; order_total: string
  expires_at: string; package_count: number; real_kg: string; volumetric_kg: string; billable_kg: string
}
export interface ShipmentInfo {
  id: number; carrier: string; state: string; state_label: string; waybill: string | null; last_update: string
  last_sync_at: string | null; tracking_url: string; tracking_api_available: boolean
  history: Array<{state: string; description: string; created_at: string}>
  account_type?: string; account?: string; real_kg?: string; volumetric_kg?: string; billable_kg?: string
  tcc_rate?: string; surcharge?: string; charged?: string; last_error?: string; retry_allowed?: boolean
  documents?: Record<string,string>; environment?: string
}

export interface TCCAddress {
  tcc_city_code: string; complement: string; neighborhood: string; delivery_instructions: string
}
export const shippingService = {
  config: () => api.get<{enabled:boolean; tracking_api_available:boolean}>('/shipping/config'),
  cities: () => api.get<TCCCity[]>('/shipping/cities'),
  quote: (payload: unknown) => api.post<ShippingQuote>('/shipping/quote',payload),
}
