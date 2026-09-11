import api from './admin_api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatSession {
  id: number
  user_name: string
  user_cedula: string
  status: 'bot' | 'waiting' | 'active' | 'closed'
  channel: Channel
  priority: 'low' | 'normal' | 'high' | 'urgent'
  queue_id: number | null
  contact_id: number | null
  external_thread_id: string
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
  direction: 'inbound' | 'outbound' | 'internal'
  message_type: 'text' | 'image' | 'audio' | 'video' | 'document' | 'sticker' | 'template' | 'interactive'
  status: 'received' | 'queued' | 'sent' | 'delivered' | 'read' | 'failed'
  external_message_id: string | null
  attachments: ChatAttachment[]
  created_at: string
}

export type Channel = 'ecommerce' | 'whatsapp' | 'facebook' | 'instagram'

export interface ChatAttachment {
  id: number
  url: string
  name: string
  mime_type: string
  size: number
}

export interface SessionFilters {
  status?: string
  channel?: string
  search?: string
  unanswered?: boolean
}

export interface AssignmentQueue {
  id: number
  name: string
  active: boolean
  auto_assign: boolean
  channels: Channel[]
  members: Array<{ user_id: number; capacity: number; active: boolean }>
}

export interface MetaIntegration {
  id: number
  name: string
  channel: Exclude<Channel, 'ecommerce'>
  active: boolean
  app_id: string
  external_account_id: string
  phone_number_id: string
  page_id: string
  instagram_account_id: string
  graph_api_version: string
  configuration: Record<string, unknown>
  token_expires_at: string | null
  has_access_token: boolean
  has_app_secret: boolean
  has_verify_token: boolean
}

export type MetaIntegrationInput = Omit<MetaIntegration, 'id' | 'has_access_token' | 'has_app_secret' | 'has_verify_token' | 'token_expires_at'> & {
  access_token?: string
  app_secret?: string
  verify_token?: string
  token_expires_at?: string | null
}

export interface MessagesResponse {
  messages: ChatMessage[]
  status: ChatSession['status']
  agent_name: string
}

// ─── Service ──────────────────────────────────────────────────────────────────

export const adminChatService = {
  getSessions: async (filters: SessionFilters = {}): Promise<ChatSession[]> => {
    const params = {
      ...(filters.status && filters.status !== 'all' ? { status: filters.status } : {}),
      ...(filters.channel && filters.channel !== 'all' ? { channel: filters.channel } : {}),
      ...(filters.search ? { search: filters.search } : {}),
      ...(filters.unanswered ? { unanswered: 'true' } : {}),
    }
    const res = await api.get('/crm-chat/sessions/', { params })
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

  setPriority: async (sessionId: number, priority: ChatSession['priority']): Promise<ChatSession> => {
    const res = await api.patch(`/crm-chat/sessions/${sessionId}/`, { priority })
    return res.data
  },

  getQueues: async (): Promise<AssignmentQueue[]> => {
    const res = await api.get('/crm-chat/queues/')
    return res.data
  },

  assignQueue: async (sessionId: number, queueId: number): Promise<ChatSession> => {
    const res = await api.patch(`/crm-chat/sessions/${sessionId}/`, { queue_id: queueId })
    return res.data
  },

  getIntegrations: async (): Promise<MetaIntegration[]> => {
    const res = await api.get('/meta/integrations/')
    return res.data.results ?? res.data
  },

  createIntegration: async (payload: MetaIntegrationInput): Promise<MetaIntegration> => {
    const res = await api.post('/meta/integrations/', payload)
    return res.data
  },

  updateIntegration: async (id: number, payload: Partial<MetaIntegrationInput>): Promise<MetaIntegration> => {
    const res = await api.patch(`/meta/integrations/${id}/`, payload)
    return res.data
  },

  validateIntegration: async (id: number): Promise<{ valid: boolean; remote_id?: string; name?: string; detail?: string }> => {
    const res = await api.post(`/meta/integrations/${id}/validate/`)
    return res.data
  },

  startInstagramOAuth: async (id: number): Promise<{ authorization_url: string; redirect_uri: string }> => {
    const res = await api.post(`/meta/instagram/integrations/${id}/oauth/start/`)
    return res.data
  },
}

export default adminChatService
