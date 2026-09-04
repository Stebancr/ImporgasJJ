import api from './admin_api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatSession {
  id: number
  user_name: string
  user_cedula: string
  status: 'bot' | 'waiting' | 'active' | 'closed'
  agent_name: string
  unread_by_agent: number
  created_at: string
  updated_at: string
  last_message: string | null
}

export interface ChatMessage {
  id: number
  text: string
  sender_type: 'user' | 'bot' | 'agent'
  sender_name: string
  created_at: string
}

export interface MessagesResponse {
  messages: ChatMessage[]
  status: ChatSession['status']
  agent_name: string
}

// ─── Service ──────────────────────────────────────────────────────────────────

export const adminChatService = {
  getSessions: async (status?: string): Promise<ChatSession[]> => {
    const res = await api.get('/crm-chat/sessions/', { params: status ? { status } : {} })
    return res.data
  },

  getPendingCount: async (): Promise<number> => {
    const res = await api.get('/crm-chat/sessions/pending-count/')
    return res.data.count ?? 0
  },

  getMessages: async (sessionId: number, afterId?: number): Promise<MessagesResponse> => {
    const params = afterId != null ? { after: afterId } : {}
    const res = await api.get(`/crm-chat/sessions/${sessionId}/messages/`, { params })
    return res.data
  },

  sendMessage: async (sessionId: number, text: string): Promise<ChatMessage> => {
    const res = await api.post(`/crm-chat/sessions/${sessionId}/messages/`, { text })
    return res.data
  },

  takeSession: async (sessionId: number): Promise<ChatSession> => {
    const res = await api.patch(`/crm-chat/sessions/${sessionId}/`, { take: true })
    return res.data
  },

  closeSession: async (sessionId: number): Promise<ChatSession> => {
    const res = await api.patch(`/crm-chat/sessions/${sessionId}/`, { status: 'closed' })
    return res.data
  },
}

export default adminChatService
