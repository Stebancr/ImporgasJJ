import api from './api'

interface WompiPaymentData {
  orderId: string
  amount: number
  customerEmail: string
  customerName: string
  customerPhone: string
}

interface WompiResponse {
  redirectUrl: string
  transactionId: string
}

interface PaymentStatus {
  transactionId: string
  status: 'APPROVED' | 'DECLINED' | 'PENDING' | 'VOIDED' | 'ERROR'
  amount: number
  orderId: string
}

export const paymentsService = {
  createWompiPayment: async (data: WompiPaymentData): Promise<WompiResponse> => {
    return api.post<WompiResponse>('/payments/wompi/create', data)
  },

  getPaymentStatus: async (transactionId: string): Promise<PaymentStatus> => {
    return api.get<PaymentStatus>(`/payments/status/${transactionId}`)
  },

  verifyWebhook: async (payload: unknown): Promise<{ valid: boolean }> => {
    return api.post('/payments/wompi/webhook', payload)
  },
}

export default paymentsService
