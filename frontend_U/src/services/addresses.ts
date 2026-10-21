import api from './api'
import type { TCCAddress } from './shipping'

export interface UserAddress extends Partial<TCCAddress> {
  id: number
  label: string
  recipient_name: string
  phone: string
  address: string
  city: string
  department: string
  postal_code: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface CreateAddressPayload extends Partial<TCCAddress> {
  label: string
  recipient_name: string
  phone: string
  address: string
  city: string
  department: string
  postal_code?: string
  is_default?: boolean
}

class AddressesService {
  async getAll(): Promise<UserAddress[]> {
    const response = await api.get<{ data: UserAddress[] }>('/ecommerce/user/addresses')
    return response.data
  }

  async getById(id: number): Promise<UserAddress> {
    const response = await api.get<{ data: UserAddress }>(`/ecommerce/user/addresses/${id}`)
    return response.data
  }

  async create(payload: CreateAddressPayload): Promise<UserAddress> {
    const response = await api.post<{ data: UserAddress }>('/ecommerce/user/addresses', payload)
    window.dispatchEvent(new Event('delivery:location-changed'))
    return response.data
  }

  async update(id: number, payload: Partial<CreateAddressPayload>): Promise<UserAddress> {
    const response = await api.put<{ data: UserAddress }>(`/ecommerce/user/addresses/${id}`, payload)
    window.dispatchEvent(new Event('delivery:location-changed'))
    return response.data
  }

  async delete(id: number): Promise<void> {
    await api.delete(`/ecommerce/user/addresses/${id}`)
    window.dispatchEvent(new Event('delivery:location-changed'))
  }
}

export default new AddressesService()
