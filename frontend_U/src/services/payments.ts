import api from './api'

export type WompiStatus = 'APPROVED' | 'DECLINED' | 'PENDING' | 'VOIDED' | 'ERROR'
export interface PaymentResult {
  order_number: string; tracking_code: string; payment_tracking_code: string; reference: string; transaction_id: string
  payment_status: WompiStatus; amount: string; currency: 'COP'; customer_name: string
  items: { product_name: string; quantity: number; unit_price: string }[]
}

export const paymentsService = {
  getPaymentStatus: (trackingCode: string, transactionId?: string): Promise<PaymentResult> => {
    const params = new URLSearchParams({ tracking: trackingCode })
    if (transactionId) params.set('transaction_id', transactionId)
    return api.get<PaymentResult>(`/payments/wompi/status?${params.toString()}`)
  },
}

export default paymentsService
