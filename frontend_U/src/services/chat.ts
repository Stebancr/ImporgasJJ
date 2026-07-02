import api from './api'

export interface ChatSession {
  id: number
  user_name: string
  status: 'bot' | 'waiting' | 'active' | 'closed'
  agent_name: string
  created_at: string
}

export interface ChatMessageData {
  id: number
  text: string
  sender_type: 'user' | 'bot' | 'agent'
  sender_name: string
  created_at: string
}

export interface MessagesResponse {
  messages: ChatMessageData[]
  status: ChatSession['status']
  agent_name: string
}

export interface OrderStatusResult {
  found: boolean
  order_number?: string
  status?: string
  status_label?: string
  customer_name?: string
  total?: string
  created_at?: string
}

export const chatService = {
  createSession: (initialMessages: { text: string; is_bot: boolean }[]): Promise<ChatSession> =>
    api.post<ChatSession>('/crm-chat/sessions/', { initial_messages: initialMessages }),

  getSession: (id: number): Promise<ChatSession> =>
    api.get<ChatSession>(`/crm-chat/sessions/${id}/`),

  getMessages: (sessionId: number, afterId?: number): Promise<MessagesResponse> =>
    api.get<MessagesResponse>(
      `/crm-chat/sessions/${sessionId}/messages/${afterId != null ? `?after=${afterId}` : ''}`
    ),

  sendMessage: (sessionId: number, text: string): Promise<ChatMessageData> =>
    api.post<ChatMessageData>(`/crm-chat/sessions/${sessionId}/messages/`, { text }),

  closeSession: (sessionId: number): Promise<ChatSession> =>
    api.patch<ChatSession>(`/crm-chat/sessions/${sessionId}/`, { status: 'closed' }),

  getOrderStatus: (q: string): Promise<OrderStatusResult> =>
    api.get<OrderStatusResult>(`/orders/status?q=${encodeURIComponent(q)}`),
}
