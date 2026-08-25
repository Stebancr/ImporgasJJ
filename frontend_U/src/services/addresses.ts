import api from './api'

export interface UserAddress {
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

export interface CreateAddressPayload {
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
    return response.data
  }

  async update(id: number, payload: Partial<CreateAddressPayload>): Promise<UserAddress> {
    const response = await api.put<{ data: UserAddress }>(`/ecommerce/user/addresses/${id}`, payload)
    return response.data
  }

  async delete(id: number): Promise<void> {
    await api.delete(`/ecommerce/user/addresses/${id}`)
  }
}

export default new AddressesService()
