import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, Send, UserCheck, PhoneOff, RefreshCw, Bot, User, Loader2, Inbox } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { adminChatService } from '@/admin/services/admin_chat'
import type { ChatSession, ChatMessage } from '@/admin/services/admin_chat'

// â”€â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const STATUS_CONFIG = {
  bot:     { label: 'Bot',             color: 'bg-gray-100 text-gray-600' },
  waiting: { label: 'Esperando',       color: 'bg-yellow-100 text-yellow-700' },
  active:  { label: 'Activo',          color: 'bg-green-100 text-green-700' },
  closed:  { label: 'Cerrado',         color: 'bg-red-100 text-red-600' },
} as const

function fmtTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'Ahora'
  if (diffMin < 60) return `${diffMin}m`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h`
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

// â”€â”€â”€ BotMessageText: renderiza texto con markdown y links â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function BotMessageText({ text }: { text: string }) {
  const renderLine = (line: string, lineIdx: number) => {
    const tokens: React.ReactNode[] = []
    let remaining = line
    let tokenKey = 0

    while (remaining) {
      const productMatch = remaining.match(/(\/producto\/\d+)/)
      const boldMatch = remaining.match(/\*\*([^*]+)\*\*/)

      const productIndex = productMatch ? remaining.indexOf(productMatch[0]) : -1
      const boldIndex = boldMatch ? remaining.indexOf(boldMatch[0]) : -1

      if (productIndex >= 0 && (boldIndex < 0 || productIndex < boldIndex)) {
        if (productIndex > 0) {
          tokens.push(<span key={`${lineIdx}-${tokenKey++}`}>{remaining.slice(0, productIndex)}</span>)
        }
        tokens.push(
          <Link
            key={`${lineIdx}-${tokenKey++}`}
            to={productMatch![0]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline underline-offset-2 font-medium hover:opacity-80"
          >
            Ver producto â†’
          </Link>
        )
        remaining = remaining.slice(productIndex + productMatch![0].length)
      } else if (boldIndex >= 0) {
        if (boldIndex > 0) {
          tokens.push(<span key={`${lineIdx}-${tokenKey++}`}>{remaining.slice(0, boldIndex)}</span>)
        }
        tokens.push(
          <strong key={`${lineIdx}-${tokenKey++}`} className="font-semibold">
            {boldMatch![1]}
          </strong>
        )
        remaining = remaining.slice(boldIndex + boldMatch![0].length)
      } else {
        tokens.push(<span key={`${lineIdx}-${tokenKey++}`}>{remaining}</span>)
        break
      }
    }
    return <>{tokens}</>
  }

  const lines = text.split('\n')
  return (
    <div className="text-sm leading-relaxed">
      {lines.map((line, i) => (
        <div key={i}>{renderLine(line, i)}</div>
      ))}
    </div>
  )
}

// â”€â”€â”€ Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function ChatPage() {
  const [sessions, setSessions]           = useState<ChatSession[]>([])
  const [statusFilter, setStatusFilter]   = useState<string>('waiting')
  const [selected, setSelected]           = useState<ChatSession | null>(null)
  const [messages, setMessages]           = useState<ChatMessage[]>([])
  const [inputText, setInputText]         = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [sendingMsg, setSendingMsg]       = useState(false)

  const lastMsgIdRef    = useRef<number | null>(null)
  const pollMsgsRef     = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollSessionsRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const messagesEndRef  = useRef<HTMLDivElement>(null)

  // â”€â”€ load sessions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const loadSessions = useCallback(async () => {
    setLoadingSessions(true)
    try {
      const data = await adminChatService.getSessions(statusFilter === 'all' ? undefined : statusFilter)
      setSessions(data)
    } catch { /* silent */ } finally {
      setLoadingSessions(false)
    }
  }, [statusFilter])

  // Poll session list every 5 s
  useEffect(() => {
    loadSessions()
    pollSessionsRef.current = setInterval(loadSessions, 5000)
    return () => { if (pollSessionsRef.current) clearInterval(pollSessionsRef.current) }
  }, [loadSessions])

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // â”€â”€ open session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const openSession = async (session: ChatSession) => {
    setSelected(session)
    setMessages([])
    lastMsgIdRef.current = null
    if (pollMsgsRef.current) clearInterval(pollMsgsRef.current)

    try {
      const result = await adminChatService.getMessages(session.id)
      setMessages(result.messages)
      if (result.messages.length > 0)
        lastMsgIdRef.current = result.messages[result.messages.length - 1].id
    } catch { /* silent */ }

    // Poll messages every 3 s for the open session
    if (session.status !== 'closed') {
      pollMsgsRef.current = setInterval(async () => {
        try {
          const result = await adminChatService.getMessages(session.id, lastMsgIdRef.current ?? undefined)
          if (result.messages.length > 0) {
            setMessages((prev) => [...prev, ...result.messages])
            lastMsgIdRef.current = result.messages[result.messages.length - 1].id
          }
          if (result.status === 'closed') {
            setSelected((prev) => prev ? { ...prev, status: 'closed' } : prev)
            clearInterval(pollMsgsRef.current!)
          }
        } catch { /* silent */ }
      }, 3000)
    }
  }

  useEffect(() => {
    return () => { if (pollMsgsRef.current) clearInterval(pollMsgsRef.current) }
  }, [])

  // â”€â”€ take session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleTake = async () => {
    if (!selected) return
    try {
      const updated = await adminChatService.takeSession(selected.id)
      setSelected(updated)
      setSessions((prev) => prev.map((s) => s.id === updated.id ? updated : s))
    } catch { /* silent */ }
  }

  // â”€â”€ close session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleClose = async () => {
    if (!selected || !confirm('Â¿Cerrar esta conversacion?')) return
    try {
      const updated = await adminChatService.closeSession(selected.id)
      setSelected(updated)
      setSessions((prev) => prev.map((s) => s.id === updated.id ? updated : s))
      if (pollMsgsRef.current) clearInterval(pollMsgsRef.current)
    } catch { /* silent */ }
  }

  // â”€â”€ send message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleSend = async () => {
    if (!selected || !inputText.trim() || sendingMsg) return
    setSendingMsg(true)
    const text = inputText.trim()
    setInputText('')
    try {
      const msg = await adminChatService.sendMessage(selected.id, text)
      setMessages((prev) => [...prev, msg])
      lastMsgIdRef.current = msg.id
      // Auto-take if still waiting
      if (selected.status === 'waiting') handleTake()
    } catch { /* silent */ } finally {
      setSendingMsg(false)
    }
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <MessageSquare className="h-6 w-6" />
          CRM Chat
        </h1>
        <p className="text-muted-foreground text-sm">Conversaciones de clientes en tiempo real</p>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">

        {/* â”€â”€ Sessions panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        <div className="w-72 flex-shrink-0 flex flex-col border rounded-xl bg-card overflow-hidden">

          {/* Filter + refresh */}
          <div className="p-3 border-b flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex-1 h-8 text-sm rounded-md border bg-background px-2 focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="all">Todos</option>
              <option value="waiting">Esperando</option>
              <option value="active">Activos</option>
              <option value="closed">Cerrados</option>
            </select>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={loadSessions}>
              <RefreshCw className={`h-4 w-4 ${loadingSessions ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm gap-2 p-6">
                <Inbox className="h-8 w-8 opacity-40" />
                <span>Sin conversaciones</span>
              </div>
            ) : sessions.map((s) => {
              const cfg = STATUS_CONFIG[s.status] ?? STATUS_CONFIG.bot
              const isSelected = selected?.id === s.id
              return (
                <button
                  key={s.id}
                  onClick={() => openSession(s)}
                  className={`w-full text-left px-3 py-3 border-b last:border-b-0 hover:bg-accent/50 transition-colors ${isSelected ? 'bg-primary/10 border-l-2 border-l-primary' : ''}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="font-medium text-sm truncate">{s.user_name}</p>
                        {s.unread_by_agent > 0 && (
                          <span className="flex-shrink-0 w-4 h-4 bg-primary text-primary-foreground rounded-full text-[10px] flex items-center justify-center font-bold">
                            {s.unread_by_agent > 9 ? '9+' : s.unread_by_agent}
                          </span>
                        )}
                      </div>
                      {s.user_cedula && <p className="text-xs text-muted-foreground">CC {s.user_cedula}</p>}
                      {s.last_message && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">{s.last_message}</p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 flex-shrink-0">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${cfg.color}`}>
                        {cfg.label}
                      </span>
                      <span className="text-[10px] text-muted-foreground">{fmtTime(s.updated_at)}</span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* â”€â”€ Conversation panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        {!selected ? (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground border rounded-xl bg-card gap-3">
            <MessageSquare className="h-12 w-12 opacity-20" />
            <p>Selecciona una conversacion para responder</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col border rounded-xl bg-card overflow-hidden min-w-0">

            {/* Session header */}
            <div className="px-4 py-3 border-b flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm flex-shrink-0">
                  {selected.user_name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-sm truncate">{selected.user_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {selected.user_cedula ? `CC ${selected.user_cedula}` : ''}
                    {selected.agent_name ? ` Â· Asesor: ${selected.agent_name}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {(selected.status === 'waiting' || selected.status === 'bot') && (
                  <Button size="sm" variant="outline" onClick={handleTake} className="h-8 text-xs gap-1">
                    <UserCheck className="h-3.5 w-3.5" />
                    Tomar
                  </Button>
                )}
                {selected.status !== 'closed' && (
                  <Button size="sm" variant="outline" onClick={handleClose} className="h-8 text-xs gap-1 text-destructive border-destructive/30 hover:bg-destructive/10">
                    <PhoneOff className="h-3.5 w-3.5" />
                    Cerrar
                  </Button>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CONFIG[selected.status]?.color ?? ''}`}>
                  {STATUS_CONFIG[selected.status]?.label ?? selected.status}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-muted/20">
              {messages.map((m) => {
                const isAgent = m.sender_type === 'agent'
                const isUser  = m.sender_type === 'user'
                return (
                  <div key={m.id} className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
                    {isUser && (
                      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center mr-2 flex-shrink-0">
                        <User className="h-3.5 w-3.5 text-primary" />
                      </div>
                    )}
                    <div className={`max-w-[70%] px-3 py-2 rounded-2xl text-sm ${
                      isUser
                        ? 'bg-white border rounded-tl-none shadow-sm'
                        : isAgent
                        ? 'bg-primary text-primary-foreground rounded-tr-none'
                        : 'bg-muted text-muted-foreground rounded-tr-none text-xs italic'
                    }`}>
                      {isAgent && m.sender_name && (
                        <p className="text-[10px] font-semibold opacity-70 mb-0.5">{m.sender_name}</p>
                      )}
                      {!isUser && !isAgent && (
                        <div className="flex items-center gap-1 mb-0.5">
                          <Bot className="h-3 w-3" />
                          <span className="text-[10px] font-medium">Bot</span>
                        </div>
                      )}
                      {!isUser && !isAgent ? (
                        <BotMessageText text={m.text} />
                      ) : (
                        <p className="leading-relaxed">{m.text}</p>
                      )}
                      <p className={`text-[10px] mt-1 ${isUser ? 'text-muted-foreground' : isAgent ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>
                        {new Date(m.created_at).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    {isAgent && (
                      <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center ml-2 flex-shrink-0">
                        <UserCheck className="h-3.5 w-3.5 text-primary-foreground" />
                      </div>
                    )}
                  </div>
                )
              })}
              {messages.length === 0 && (
                <p className="text-center text-muted-foreground text-sm py-8">Sin mensajes aun</p>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t">
              {selected.status === 'closed' ? (
                <p className="text-center text-xs text-muted-foreground py-1">Conversacion cerrada</p>
              ) : (
                <div className="flex gap-2">
                  <Input
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                    placeholder="Escribe tu respuesta..."
                    className="flex-1 h-10"
                  />
                  <Button onClick={handleSend} disabled={!inputText.trim() || sendingMsg} size="icon" className="h-10 w-10">
                    {sendingMsg ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
