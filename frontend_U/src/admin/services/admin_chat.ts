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
  avatar_url: string
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
  error: string
  external_message_id: string | null
  client_message_id: string | null
  origin: 'customer' | 'mobile' | 'crm' | 'bot'
  external_timestamp: string | null
  timestamp: string
  attachments: ChatAttachment[]
  created_at: string
}

export type Channel = 'ecommerce' | 'whatsapp' | 'whatsapp_web' | 'facebook' | 'instagram'

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
  business_id: string
  display_phone_number: string
  page_id: string
  instagram_account_id: string
  graph_api_version: string
  configuration: Record<string, unknown>
  token_expires_at: string | null
  connection_status: 'pending' | 'connected' | 'error' | 'disconnected'
  last_validated_at: string | null
  last_webhook_at: string | null
  last_error: string
  disconnected_at: string | null
  has_access_token: boolean
  has_app_secret: boolean
  has_verify_token: boolean
  managed_by_meta_oauth: boolean
  whatsapp_coexistence: boolean
}

export interface MetaInstagramAccount {
  instagram_account_id: string
  username: string
  name: string
  profile_picture_url: string
  is_selected: boolean
  is_active: boolean
}

export interface MetaFacebookPage {
  page_id: string
  page_name: string
  tasks: string[]
  is_selected: boolean
  is_active: boolean
  instagram_account?: MetaInstagramAccount | null
}

export interface MetaConnection {
  id: number
  facebook_user_id: string
  granted_scopes: string[]
  token_created_at: string
  token_expires_at: string | null
  token_last_validated_at: string | null
  token_status: 'pending' | 'valid' | 'expired' | 'revoked' | 'error'
  is_active: boolean
  facebook_pages: MetaFacebookPage[]
  created_at: string
  updated_at: string
}

export interface WhatsAppCoexistenceConfig {
  app_id: string
  config_id: string
  graph_api_version: string
  embedded_signup_version: string
  feature_type: 'whatsapp_business_app_onboarding'
  state: string
}

export interface WhatsAppCoexistenceCompletion {
  state: string
  code: string
  event: 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING'
  waba_id: string
  phone_number_id?: string
  business_id?: string
}

export type WhatsAppGatewayState = {
  connection_id: string
  status: 'disconnected' | 'waiting_for_qr' | 'qr_ready' | 'connecting' | 'connected' | 'logged_out' | 'reconnecting' | 'error'
  qr_data_url?: string
  qr_expires_at?: string
  phone_number?: string
  last_connected_at?: string
  last_error?: string
  active?: boolean
  bot_enabled?: boolean
  experimental?: boolean
}

export type MetaIntegrationInput = Omit<MetaIntegration, 'id' | 'active' | 'display_phone_number' | 'connection_status' | 'last_validated_at' | 'last_webhook_at' | 'last_error' | 'disconnected_at' | 'has_access_token' | 'has_app_secret' | 'has_verify_token' | 'managed_by_meta_oauth' | 'whatsapp_coexistence' | 'token_expires_at'> & {
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

  sendMessage: async (sessionId: number, text: string, file?: File): Promise<ChatMessage> => {
    const data = new FormData()
    data.append('text', text)
    data.append('origin', 'crm')
    data.append('client_message_id', crypto.randomUUID())
    if (file) data.append('file', file)
    const res = await api.post(`/crm-chat/sessions/${sessionId}/messages/`, data)
    return res.data
  },

  getAttachmentBlob: async (url: string): Promise<Blob> => {
    const apiPath = url.replace(/^\/api/, '')
    const res = await api.get(apiPath, { responseType: 'blob' })
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

  validateIntegration: async (id: number, activate = false): Promise<{ valid: boolean; remote_id?: string; name?: string; detail?: string }> => {
    const res = await api.post(`/meta/integrations/${id}/validate/`, { activate })
    return res.data
  },

  disconnectIntegration: async (id: number): Promise<void> => {
    await api.delete(`/meta/integrations/${id}/`)
  },

  startInstagramOAuth: async (id: number): Promise<{ authorization_url: string; redirect_uri: string }> => {
    const res = await api.post(`/meta/instagram/integrations/${id}/oauth/start/`)
    return res.data
  },

  startMetaOAuth: async (): Promise<{ authorization_url: string }> => {
    const res = await api.get('/meta/connect/')
    return res.data
  },

  getMetaConnections: async (): Promise<MetaConnection[]> => {
    const res = await api.get('/meta/connections/')
    return res.data.results ?? res.data
  },

  selectMetaAccounts: async (
    id: number,
    payload: { facebook_page_ids: string[]; instagram_account_ids: string[] },
  ): Promise<MetaConnection> => {
    const res = await api.post(`/meta/connections/${id}/accounts/`, payload)
    return res.data
  },

  disconnectMetaConnection: async (id: number): Promise<void> => {
    await api.delete(`/meta/connections/${id}/`)
  },

  getWhatsAppCoexistenceConfig: async (): Promise<WhatsAppCoexistenceConfig> => {
    const res = await api.get('/meta/whatsapp/coexistence/config/')
    return res.data
  },

  completeWhatsAppCoexistence: async (
    payload: WhatsAppCoexistenceCompletion,
  ): Promise<{ connected: boolean; integration: MetaIntegration }> => {
    const res = await api.post('/meta/whatsapp/coexistence/complete/', payload)
    return res.data
  },

  getWhatsAppGatewayStatus: async (): Promise<WhatsAppGatewayState> => {
    const res = await api.get('/crm-chat/whatsapp-web/status/')
    return res.data
  },

  getWhatsAppGatewayRealtimeToken: async (): Promise<{ token: string; expires_in: number }> => {
    const res = await api.post('/crm-chat/whatsapp-web/realtime-token/')
    return res.data
  },

  setWhatsAppGatewayBotEnabled: async (bot_enabled: boolean): Promise<{ bot_enabled: boolean }> => {
    const res = await api.patch('/crm-chat/whatsapp-web/status/', { bot_enabled })
    return res.data
  },

  commandWhatsAppGateway: async (command: 'qr' | 'reconnect' | 'logout'): Promise<{ status: string }> => {
    const res = await api.post(`/crm-chat/whatsapp-web/commands/${command}/`)
    return res.data
  },
}

export default adminChatService
