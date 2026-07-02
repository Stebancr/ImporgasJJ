import api from './api'

export interface ApiLocation {
  id: number
  name: string
  address: string
  city: string
  phone: string
  hours_weekday: string
  hours_saturday: string
  hours_sunday: string
  is_active: boolean
  created_at: string
}

interface PaginatedLocations {
  data: ApiLocation[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export const locationsService = {
  async getActive(): Promise<ApiLocation[]> {
    const res = await api.get<PaginatedLocations>('/locations?is_active=true&per_page=100')
    return res.data ?? []
  },
}

export default locationsService
