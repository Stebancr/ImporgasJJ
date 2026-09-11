/**
 * Servicio de Chatbot - Integración con Ollama
 * Permite chatear con el bot y deriva a agentes humanos cuando es necesario
 */

import api from './api';
const API_URL = '/api/crm-chat/bot';

export interface ChatMessage {
  id?: number;
  text: string;
  sender_type: 'user' | 'bot' | 'agent';
  sender_name?: string;
  created_at?: string;
}

export interface ChatResponse {
  session_id: number;
  message: string;
  sender_type: string;
  status: 'bot' | 'waiting' | 'active' | 'closed';
  needs_agent: boolean;
  needs_login: boolean;    // true cuando el usuario anónimo quiere un asesor
  user_message_id: number;
  bot_message_id: number;
}

export interface SessionMessagesResponse {
  session_id: number;
  status: string;
  messages: ChatMessage[];
  agent_name?: string | null;
}

/**
 * Envía un mensaje al chatbot
 */
export const sendMessage = async (
  message: string,
  sessionId?: number | null,
  userName?: string,
  userEmail?: string
): Promise<ChatResponse> => {
  try {
    return await api.post<ChatResponse>('/crm-chat/bot/chat/', {
        message,
        session_id: sessionId,
        user_name: userName,
        user_email: userEmail,
    });
  } catch (error) {
    console.error('Error en sendMessage:', error);
    throw error;
  }
};

/**
 * Obtiene todos los mensajes de una sesión
 */
export const getSessionMessages = async (
  sessionId: number,
  afterMessageId?: number
): Promise<SessionMessagesResponse> => {
  try {
    const url = afterMessageId
      ? `${API_URL}/sessions/${sessionId}/messages/?after=${afterMessageId}`
      : `${API_URL}/sessions/${sessionId}/messages/`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Error al obtener mensajes');
    }

    return await response.json();
  } catch (error) {
    console.error('Error en getSessionMessages:', error);
    throw error;
  }
};

/**
 * Hook para polling de nuevos mensajes (cuando está con un agente)
 */
export const pollNewMessages = (
  sessionId: number,
  lastMessageId: number,
  onNewMessages: (messages: ChatMessage[]) => void,
  intervalMs: number = 3000
): () => void => {
  const intervalId = setInterval(async () => {
    try {
      const data = await getSessionMessages(sessionId, lastMessageId);
      if (data.messages && data.messages.length > 0) {
        onNewMessages(data.messages);
      }
    } catch (error) {
      console.error('Error en polling:', error);
    }
  }, intervalMs);

  // Retorna función para detener el polling
  return () => clearInterval(intervalId);
};
