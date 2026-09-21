import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { MessageCircle, X, Send, Bot, Sparkles, Loader2, UserCheck, PhoneOff, RotateCcw, LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { chatService } from '../services/chat'
import { locationsService } from '../services/locations'
import { sendMessage as sendOllamaMessage } from '../services/chatbotService'
import type { ChatSession } from '../services/chat'

// ─── types ────────────────────────────────────────────────────────────────────

interface Message {
  id: number
  text: string
  isBot: boolean
  isAgent?: boolean
  needsLogin?: boolean   // muestra botón de inicio de sesión
  senderName?: string
  timestamp: Date
}

type ChatMode = 'local' | 'creating' | 'waiting' | 'active' | 'closed'
type PendingAction = null | 'tracking'

// ─── constants ────────────────────────────────────────────────────────────────────

const quickReplies = [
  'Horarios de atencion',
  'Sedes y servicios',
  'Consultar pedido',
  'Hablar con asesor',
]

// ─── BotMessageText: renderiza texto con markdown y links ─────────────────────

function BotMessageText({ text }: { text: string }) {
  const renderLine = (line: string, lineIdx: number) => {
    const tokens: React.ReactNode[] = []
    let tokenKey = 0
    const pattern = /(\[([^\]]+)\]\(((?:https?:\/\/|\/)[^)]+)\)|\*\*([^*]+)\*\*|(https?:\/\/[^\s]+\/producto\/\d+|\/producto\/\d+))/g
    let cursor = 0
    let match: RegExpExecArray | null

    while ((match = pattern.exec(line)) !== null) {
      if (match.index > cursor) {
        tokens.push(<span key={`${lineIdx}-${tokenKey++}`}>{line.slice(cursor, match.index)}</span>)
      }
      if (match[4]) {
        tokens.push(<strong key={`${lineIdx}-${tokenKey++}`} className="font-semibold">{match[4]}</strong>)
      } else {
        const href = match[3] || match[5]
        const label = match[2] || 'Ver producto →'
        const classes = 'text-[#001575] underline underline-offset-2 font-medium hover:text-[#0020aa]'
        tokens.push(href.startsWith('/') ? (
          <Link key={`${lineIdx}-${tokenKey++}`} to={href} className={classes}>{label}</Link>
        ) : (
          <a key={`${lineIdx}-${tokenKey++}`} href={href} target="_blank" rel="noopener noreferrer" className={classes}>{label}</a>
        ))
      }
      cursor = pattern.lastIndex
    }
    if (cursor < line.length) {
      tokens.push(<span key={`${lineIdx}-${tokenKey++}`}>{line.slice(cursor)}</span>)
    }
    return <>{tokens}</>
  }

  const lines = text.split(/\r?\n/)
  return (
    <div className="text-sm leading-relaxed break-words whitespace-pre-wrap">
      {lines.map((line, i) => (
        <div key={i} className={line.trim() ? 'min-w-0' : 'h-3'}>{renderLine(line, i)}</div>
      ))}
    </div>
  )
}

// ─── component ────────────────────────────────────────────────────────────────

function Chatbot() {
  const { isAuthenticated } = useAuth()

  const [isOpen, setIsOpen]         = useState(false)
  const [messages, setMessages]     = useState<Message[]>([
    { id: 1, text: 'Muchas gracias por comunicarse con ImporGas JJ, especialistas en Gas y Climatización.\n\nSoy el asesor comercial virtual de ImporGas JJ. ¿Cómo podemos ayudarte?', isBot: true, timestamp: new Date() },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping]     = useState(false)
  const [chatMode, setChatMode]     = useState<ChatMode>('local')
  const [pendingAction, setPendingAction] = useState<PendingAction>(null)
  const [sessionId, setSessionId]   = useState<number | null>(null)
  const [ollamaBotSessionId, setOllamaBotSessionId] = useState<number | null>(null) // Sesión del bot de Ollama
  const [agentName, setAgentName]   = useState('')

  const messagesEndRef  = useRef<HTMLDivElement>(null)
  const launcherRef     = useRef<HTMLButtonElement>(null)
  const dialogRef       = useRef<HTMLDivElement>(null)
  const lastMsgIdRef    = useRef<number | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!isOpen) return
    const closeButton = dialogRef.current?.querySelector<HTMLButtonElement>('[aria-label="Cerrar chat"]')
    closeButton?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      launcherRef.current?.focus()
    }
  }, [isOpen])

  // ── scroll ────────────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // ── resume session on mount ───────────────────────────────────────────────
  useEffect(() => {
    if (!isAuthenticated) return
    const storedId = sessionStorage.getItem('chatSessionId')
    if (!storedId) return
    const id = parseInt(storedId, 10)
    chatService.getSession(id)
      .then((session: ChatSession) => {
        if (session.status === 'closed') { sessionStorage.removeItem('chatSessionId'); return }
        setSessionId(id)
        setChatMode(session.status as ChatMode)
        setAgentName(session.agent_name || '')
        return chatService.getMessages(id)
      })
      .then((result) => {
        if (!result) return
        const msgs: Message[] = result.messages.map((m) => ({
          id:         m.id,
          text:       m.text,
          isBot:      m.sender_type !== 'user',
          isAgent:    m.sender_type === 'agent',
          senderName: m.sender_type === 'agent' ? m.sender_name : undefined,
          timestamp:  new Date(m.created_at),
        }))
        if (msgs.length > 0) {
          setMessages(msgs)
          lastMsgIdRef.current = result.messages[result.messages.length - 1].id
        }
      })
      .catch(() => sessionStorage.removeItem('chatSessionId'))
  }, [isAuthenticated])

  // ── polling ───────────────────────────────────────────────────────────────
  const startPolling = useCallback((id: number) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    const poll = async () => {
      try {
        const result = await chatService.getMessages(id, lastMsgIdRef.current ?? undefined)
        if (result.messages.length > 0) {
          const newMsgs: Message[] = result.messages
            .filter((m) => m.sender_type !== 'user')
            .map((m) => ({
              id:         Date.now() + m.id,
              text:       m.text,
              isBot:      true,
              isAgent:    m.sender_type === 'agent',
              senderName: m.sender_type === 'agent' ? m.sender_name : undefined,
              timestamp:  new Date(m.created_at),
            }))
          if (newMsgs.length > 0) setMessages((prev) => [...prev, ...newMsgs])
          lastMsgIdRef.current = result.messages[result.messages.length - 1].id
        }
        if (result.status === 'active') { setChatMode('active'); if (result.agent_name) setAgentName(result.agent_name) }
        if (result.status === 'closed') { setChatMode('closed'); clearInterval(pollIntervalRef.current!) }
      } catch { /* silent */ }
    }
    pollIntervalRef.current = setInterval(poll, 3000)
  }, [])

  useEffect(() => {
    if (sessionId && (chatMode === 'waiting' || chatMode === 'active')) startPolling(sessionId)
    return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current) }
  }, [sessionId, chatMode, startPolling])

  // ── helpers ───────────────────────────────────────────────────────────────
  const pushBotMsg = (text: string) =>
    setMessages((prev) => [...prev, { id: Date.now(), text, isBot: true, timestamp: new Date() }])

  // ── send ──────────────────────────────────────────────────────────────────
  const handleSend = async (text?: string) => {
    const messageText = (text ?? inputValue).trim()
    if (!messageText || isTyping || chatMode === 'creating') return
    setMessages((prev) => [...prev, { id: Date.now(), text: messageText, isBot: false, timestamp: new Date() }])
    setInputValue('')

    // Session mode: forward to agent
    if ((chatMode === 'waiting' || chatMode === 'active') && sessionId) {
      chatService.sendMessage(sessionId, messageText).catch(() => {})
      return
    }

    // Pending action: awaiting tracking number
    if (pendingAction === 'tracking') {
      setPendingAction(null)
      setIsTyping(true)
      try {
        const result = await chatService.getOrderStatus(messageText)
        setIsTyping(false)
        if (result.found) {
          pushBotMsg(
            `Pedido encontrado:

Número: ${result.order_number}
Cliente: ${result.customer_name}
Estado: ${result.status_label}
Total: $${Number(result.total).toLocaleString('es-CO')}
Fecha: ${result.created_at}

¿Necesitas algo más?`
          )
        } else {
          pushBotMsg(`No encontramos ningún pedido con el número "${messageText}". Verifica que sea correcto (Ej: ORD-00001) o ingresa el código de seguimiento.`)
        }
      } catch {
        setIsTyping(false)
        pushBotMsg('Ocurrió un error al consultar el pedido. Intenta de nuevo en unos momentos.')
      }
      return
    }

    // Local bot response - Usar Ollama
    setIsTyping(true)
    try {
      const response = await sendOllamaMessage(messageText, ollamaBotSessionId)
      setOllamaBotSessionId(response.session_id) // Guardar la sesión del bot de Ollama
      setIsTyping(false)
      
      // Agregar respuesta del bot con flag de needs_login si aplica
      if (response.message) {
        setMessages((prev) => [...prev, {
          id: Date.now(), text: response.message, isBot: true,
          needsLogin: response.needs_login === true, timestamp: new Date(),
        }])
      }

      // Si necesita agente y está autenticado, escalar automáticamente
      if (response.needs_agent) {
        setSessionId(response.session_id)
        sessionStorage.setItem('chatSessionId', String(response.session_id))
        lastMsgIdRef.current = response.bot_message_id ?? response.user_message_id
        setChatMode(response.status === 'active' ? 'active' : 'waiting')
      }
    } catch (error) {
      console.error('Error al comunicarse con Ollama:', error)
      setIsTyping(false)
      pushBotMsg('Lo siento, estoy teniendo problemas técnicos. Por favor intenta nuevamente en unos momentos.')
    }
  }

  const handleQuickReply = (reply: string) => {
    if (reply === 'Hablar con asesor') { handleSend(reply); return }

    if (reply === 'Consultar pedido') {
      setMessages((prev) => [...prev, { id: Date.now(), text: reply, isBot: false, timestamp: new Date() }])
      setPendingAction('tracking')
      pushBotMsg('Por favor ingresa tu número de orden (Ej: ORD-00001) o el código de seguimiento:')
      return
    }

    if (reply === 'Sedes y servicios') {
      setMessages((prev) => [...prev, { id: Date.now(), text: reply, isBot: false, timestamp: new Date() }])
      setIsTyping(true)
      locationsService.getActive()
        .then((locs) => {
          setIsTyping(false)
          if (locs.length === 0) {
            pushBotMsg('Por el momento no tenemos sedes registradas. Contáctanos para más información.')
            return
          }
          let msg = 'Nuestras sedes:\n\n'
          locs.forEach((loc) => {
            msg += `📍 ${loc.name} — ${loc.city}\n`
            if (loc.address) msg += `   ${loc.address}\n`
            if (loc.phone) msg += `   Tel: ${loc.phone}\n`
            if (loc.hours_weekday) msg += `   L-V: ${loc.hours_weekday}\n`
            if (loc.hours_saturday) msg += `   Sáb: ${loc.hours_saturday}\n`
            msg += '\n'
          })
          msg += 'Para confirmar servicios disponibles, escribe "Hablar con asesor".'
          pushBotMsg(msg)
        })
        .catch(() => {
          setIsTyping(false)
          pushBotMsg('No tengo la información de sedes y servicios disponible en este momento. Escribe "Hablar con asesor" para que podamos ayudarte.')
        })
      return
    }

    handleSend(reply)
  }

  const handleClose = () => {
    // Solo cierra el widget visualmente — NO cierra la sesión (eso es tarea del asesor)
    setIsOpen(false)
  }

  const handleReset = () => {
    // Reinicia el chat a modo local para una nueva consulta
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    setSessionId(null)
    setOllamaBotSessionId(null)
    setAgentName('')
    setChatMode('local')
    setMessages([
      { id: Date.now(), text: 'Hola, gracias por comunicarte con IMPORGAS JJ. Soy tu asesor comercial virtual. ¿En qué puedo ayudarte el día de hoy?', isBot: true, timestamp: new Date() },
    ])
    setInputValue('')
    setPendingAction(null)
    sessionStorage.removeItem('chatSessionId')
  }

  // ── status label ──────────────────────────────────────────────────────────
  const { dot, statusText } = (() => {
    if (chatMode === 'waiting' || chatMode === 'creating')
      return { dot: 'bg-yellow-400 animate-pulse', statusText: chatMode === 'creating' ? 'Conectando...' : 'Esperando asesor...' }
    if (chatMode === 'active')
      return { dot: 'bg-[#10B981]', statusText: agentName ? `Con ${agentName}` : 'Con asesor' }
    if (chatMode === 'closed')
      return { dot: 'bg-gray-400', statusText: 'Chat cerrado' }
    return { dot: 'bg-[#10B981] animate-pulse', statusText: 'En linea' }
  })()

  return (
    <>
      {/* Float button */}
      <button
        ref={launcherRef}
        aria-label="Abrir chat de ayuda" aria-expanded={isOpen} tabIndex={isOpen ? -1 : 0}
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
      >
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-[#001575] to-[#F58634] rounded-full blur opacity-75 group-hover:opacity-100 transition-opacity" />
          <div className="relative w-14 h-14 bg-gradient-to-r from-[#001575] to-[#00104f] rounded-full flex items-center justify-center shadow-lg">
            <MessageCircle className="w-6 h-6 text-white" />
          </div>
          <span className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-white ${dot}`} />
        </div>
      </button>

      {/* Chat window */}
      {isOpen && (
      <div ref={dialogRef} role="dialog" aria-label="Chat de ayuda" className="fixed bottom-4 right-4 z-50 w-[380px] max-w-[calc(100vw-2rem)] overflow-hidden">
        <div className="bg-white rounded-2xl shadow-2xl max-h-[calc(100dvh-2rem)] flex flex-col overflow-hidden border border-[#E5E7EB]">

          {/* Header */}
          <div className="bg-gradient-to-r from-[#001575] to-[#00104f] text-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
                  {chatMode === 'active' ? <UserCheck className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Asesor comercial IMPORGAS JJ</h3>
                  <div className="flex items-center gap-1.5 text-sm text-white/80">
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    {statusText}
                  </div>
                </div>
              </div>
              <button aria-label="Cerrar chat" onClick={handleClose} className="w-10 h-10 hover:bg-white/10 rounded-xl transition-colors flex items-center justify-center">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="h-80 min-h-0 overflow-y-auto p-4 bg-[#F9FAFB]">
            <div className="space-y-4">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.isBot ? 'justify-start' : 'justify-end'}`}>
                  {message.isBot && (
                    <div className="w-8 h-8 bg-gradient-to-br from-[#001575] to-[#00104f] rounded-lg flex items-center justify-center mr-2 flex-shrink-0">
                      {message.isAgent ? <UserCheck className="w-4 h-4 text-white" /> : <Sparkles className="w-4 h-4 text-white" />}
                    </div>
                  )}
                  <div className={`min-w-0 max-w-[85%] px-4 py-3 rounded-2xl ${
                    message.isBot
                      ? 'bg-white text-[#1A1D21] shadow-sm border border-[#E5E7EB] rounded-tl-none'
                      : 'bg-gradient-to-r from-[#001575] to-[#00104f] text-white rounded-tr-none'
                  }`}>
                    {message.isAgent && message.senderName && (
                      <p className="text-[10px] font-semibold text-[#001575] mb-1">{message.senderName}</p>
                    )}
                    <BotMessageText text={message.text} />
                    {/* Botón de login cuando el bot requiere autenticación */}
                    {message.needsLogin && (
                      <Link
                        to="/login"
                        onClick={() => setIsOpen(false)}
                        className="mt-3 flex items-center justify-center gap-2 w-full py-2 px-3 bg-[#001575] text-white text-xs font-semibold rounded-xl hover:bg-[#0020aa] transition-colors"
                      >
                        <LogIn className="w-3.5 h-3.5" />
                        Iniciar sesión para continuar
                      </Link>
                    )}
                    <p className={`text-xs mt-1.5 ${message.isBot ? 'text-[#9CA3AF]' : 'text-white/70'}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}

              {(isTyping || chatMode === 'creating') && (
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-[#001575] to-[#00104f] rounded-lg flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-[#E5E7EB]">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              {chatMode === 'waiting' && (
                <div className="flex items-center gap-2 bg-yellow-50 border border-yellow-200 rounded-xl px-3 py-2 text-xs text-yellow-700">
                  <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
                  Un asesor se conectara en breve. Puedes seguir escribiendo.
                </div>
              )}
              {chatMode === 'closed' && (
                <div className="flex flex-col gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs text-gray-500">
                  <div className="flex items-center gap-1.5">
                    <PhoneOff className="w-3.5 h-3.5 flex-shrink-0" />
                    La conversacion ha sido cerrada.
                  </div>
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1.5 text-[#001575] font-medium hover:underline self-start"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Hacer otra consulta
                  </button>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Quick replies — local mode only */}
          {chatMode === 'local' && (
            <div className="px-4 py-3 bg-white border-t border-[#E5E7EB]">
              <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    onClick={() => handleQuickReply(reply)}
                    className="flex-shrink-0 px-3 py-1.5 text-xs bg-[#F3F4F6] text-[#4B5563] rounded-full hover:bg-[#E5E7EB] hover:text-[#1A1D21] transition-colors whitespace-nowrap"
                  >
                    {reply}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 bg-white border-t border-[#E5E7EB]">
            {chatMode === 'closed' ? (
              <button
                onClick={handleReset}
                className="w-full flex items-center justify-center gap-2 py-2.5 text-sm font-medium text-[#001575] bg-[#F0F5FF] rounded-xl hover:bg-[#E0ECFF] transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Nueva consulta
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={chatMode === 'waiting' ? 'Escribe, tu asesor lo vera...' : 'Escribe un mensaje...'}
                  className="flex-1 px-4 py-3 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:outline-none focus:border-[#001575] focus:bg-white transition-all text-sm"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!inputValue.trim() || isTyping || chatMode === 'creating'}
                  className="w-12 h-12 bg-gradient-to-r from-[#001575] to-[#00104f] text-white rounded-xl flex items-center justify-center hover:shadow-lg hover:shadow-[#001575]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      )}
    </>
  )
}

export default Chatbot
