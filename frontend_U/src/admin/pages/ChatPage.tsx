/** Bandeja omnicanal del CRM con React Query y actualización WebSocket. */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Avatar, Box, Button, Chip, CircularProgress, FormControlLabel,
  IconButton, MenuItem, Paper, Stack, Switch, TextField,
  ThemeProvider, Tooltip, Typography,
} from '@mui/material'
import {
  ArrowDown, Bell, BellOff, Bot, Check, CheckCheck, ExternalLink, Inbox, Paperclip, RefreshCw, Send,
  UserCheck, XCircle,
} from 'lucide-react'

import { ChannelBadge } from '../components/ChannelBadge'
import { useCRMWebSocket } from '../hooks/useCRMWebSocket'
import { crmTheme } from '../theme/crmTheme'
import {
  adminChatService,
  type ChatMessage,
  type ChatSession,
  type SessionFilters,
} from '../services/admin_chat'

const statusLabel: Record<ChatSession['status'], string> = {
  bot: 'Con bot', waiting: 'Pendiente', active: 'Abierto', closed: 'Cerrado',
}

const statusColor: Record<ChatSession['status'], 'default' | 'warning' | 'success' | 'info'> = {
  bot: 'info', waiting: 'warning', active: 'success', closed: 'default',
}

/** Renderiza inline: **negrita** y texto plano */
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = []
  const regex = /\*\*(.+?)\*\*/g
  let last = 0
  let match
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(<span key={key++}>{text.slice(last, match.index)}</span>)
    parts.push(<strong key={key++}>{match[1]}</strong>)
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(<span key={key++}>{text.slice(last)}</span>)
  return <>{parts}</>
}

/** Renderiza texto del bot respetando saltos de línea, viñetas y links de producto */
function BotMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <Box>
      {lines.map((line, i) => {
        // Link de producto: /producto/123
        const productMatch = line.trim().match(/^\/producto\/(\d+)$/)
        if (productMatch) {
          return (
            <Box key={i} sx={{ mt: 0.75 }}>
              <Button
                component="a"
                href={line.trim()}
                target="_blank"
                size="small"
                variant="outlined"
                startIcon={<ExternalLink size={13} />}
                sx={{
                  fontSize: '0.72rem',
                  textTransform: 'none',
                  borderColor: '#b45309',
                  color: '#b45309',
                  '&:hover': { borderColor: '#92400e', bgcolor: '#fff7ed' },
                }}
              >
                Ver producto
              </Button>
            </Box>
          )
        }

        // Línea vacía → espaciado
        if (!line.trim()) {
          return <Box key={i} sx={{ height: '0.35em' }} />
        }

        // Viñeta: empieza con "- "
        if (line.startsWith('- ')) {
          return (
            <Stack key={i} direction="row" spacing={0.75} sx={{ alignItems: 'flex-start' }}>
              <Typography variant="body2" sx={{ mt: '2px', lineHeight: 1 }}>•</Typography>
              <Typography variant="body2" sx={{ flex: 1 }}>{renderInline(line.slice(2))}</Typography>
            </Stack>
          )
        }

        return (
          <Typography key={i} variant="body2" sx={{ lineHeight: 1.5 }}>
            {renderInline(line)}
          </Typography>
        )
      })}
    </Box>
  )
}

function messageState(message: ChatMessage) {
  if (message.status === 'failed') return (
    <Tooltip title={message.error || 'Meta rechazó el envío'} arrow>
      <Box component="span" sx={{ display: 'inline-flex', cursor: 'help' }}>
        <XCircle size={13} color="#dc2626" />
      </Box>
    </Tooltip>
  )
  if (message.status === 'read') return <CheckCheck size={13} color="#2563eb" />
  if (message.status === 'delivered') return <CheckCheck size={13} />
  if (['sent', 'received'].includes(message.status)) return <Check size={13} />
  return null
}

function ConversationMessage({ message }: { message: ChatMessage }) {
  const incoming = message.direction === 'inbound' || message.sender_type === 'user'
  const bot = message.sender_type === 'bot'
  const originLabel = bot ? 'Ollama' : message.origin === 'mobile' ? 'Celular' : message.origin === 'crm' ? 'CRM' : 'Cliente'
  return (
    <Stack direction="row" spacing={1} sx={{ justifyContent: incoming ? 'flex-start' : 'flex-end' }}>
      {incoming && <Avatar sx={{ width: 28, height: 28, bgcolor: '#ffedd5', color: '#b45309', fontSize: 13 }}>C</Avatar>}
      <Paper
        variant="outlined"
        sx={{
          maxWidth: '72%', px: 1.5, py: 1,
          bgcolor: incoming ? '#fff' : bot ? '#f1f5f9' : '#b45309',
          color: incoming || bot ? '#0f172a' : '#fff',
          borderRadius: incoming ? '4px 14px 14px 14px' : '14px 4px 14px 14px',
        }}
      >
        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center', mb: 0.75 }}>
          {bot && <Bot size={13} />}
          <Typography variant="caption" sx={{ fontWeight: 700 }}>{originLabel}</Typography>
        </Stack>
        {message.text && (bot
          ? <BotMarkdown text={message.text} />
          : <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{message.text}</Typography>
        )}
        {message.attachments.map((attachment) => (
          attachment.url ? (
            <Button key={attachment.id} size="small" startIcon={<Paperclip size={14} />} href={attachment.url} target="_blank">
              {attachment.name || attachment.mime_type || 'Adjunto'}
            </Button>
          ) : (
            <Button key={attachment.id} size="small" startIcon={<Paperclip size={14} />} disabled>{attachment.name || 'Adjunto pendiente'}</Button>
          )
        ))}
        <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end', alignItems: 'center', mt: 0.5, opacity: 0.75 }}>
          <Typography variant="caption">{new Date(message.timestamp || message.created_at).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}</Typography>
          {!incoming && messageState(message)}
        </Stack>
      </Paper>
    </Stack>
  )
}

export default function ChatPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [status, setStatus] = useState('all')
  const [channel, setChannel] = useState('all')
  const [search, setSearch] = useState('')
  const [unanswered, setUnanswered] = useState(false)
  const [text, setText] = useState('')
  const messagesBoxRef = useRef<HTMLDivElement | null>(null)
  const forceScrollRef = useRef(true)
  const lastMessageIdRef = useRef<number | null>(null)
  const [nearBottom, setNearBottom] = useState(true)
  const [hasNewMessage, setHasNewMessage] = useState(false)
  const notificationsSupported = typeof window !== 'undefined' && 'Notification' in window
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    () => notificationsSupported && Notification.permission === 'granted' && localStorage.getItem('crm-notifications') === 'enabled',
  )

  const filters: SessionFilters = useMemo(
    () => ({ status, channel, search: search.trim(), unanswered }),
    [status, channel, search, unanswered],
  )
  const sessions = useQuery({
    queryKey: ['crm-sessions', filters],
    queryFn: () => adminChatService.getSessions(filters),
    refetchInterval: 30_000,
  })
  const queues = useQuery({ queryKey: ['crm-queues'], queryFn: adminChatService.getQueues })
  const selected = sessions.data?.find((item) => item.id === selectedId) ?? null
  const messages = useQuery({
    queryKey: ['crm-messages', selectedId],
    queryFn: () => adminChatService.getMessages(selectedId!),
    enabled: selectedId !== null,
    refetchInterval: 30_000,
  })
  const orderedMessages = useMemo(() => {
    const unique = new Map<number, ChatMessage>()
    for (const message of messages.data?.messages || []) unique.set(message.id, message)
    return [...unique.values()].sort((left, right) => {
      const difference = new Date(left.timestamp || left.created_at).getTime() - new Date(right.timestamp || right.created_at).getTime()
      return difference || left.id - right.id
    })
  }, [messages.data?.messages])

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['crm-sessions'] })
    if (selectedId) queryClient.invalidateQueries({ queryKey: ['crm-messages', selectedId] })
  }
  const connected = useCRMWebSocket((event) => {
    queryClient.invalidateQueries({ queryKey: ['crm-sessions'] })
    if (event.session_id === selectedId) queryClient.invalidateQueries({ queryKey: ['crm-messages', selectedId] })
    if (event.type === 'session.pending' && notificationsEnabled && Notification.permission === 'granted') {
      const notification = new Notification('Nuevo chat pendiente', { body: 'Un usuario ha iniciado una nueva conversación.', tag: `crm-session-${event.session_id}` })
      notification.onclick = () => { window.focus(); window.location.href = '/admin/chat'; notification.close() }
    }
  })

  const scrollToLatest = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const box = messagesBoxRef.current
    if (!box) return
    box.scrollTo({ top: box.scrollHeight, behavior })
    setHasNewMessage(false)
  }, [])

  useEffect(() => {
    forceScrollRef.current = true
    lastMessageIdRef.current = null
    setNearBottom(true)
    setHasNewMessage(false)
  }, [selectedId])

  useLayoutEffect(() => {
    if (!orderedMessages.length) return
    const lastId = orderedMessages.at(-1)!.id
    if (lastMessageIdRef.current === lastId) return
    lastMessageIdRef.current = lastId
    if (forceScrollRef.current || nearBottom) {
      scrollToLatest(forceScrollRef.current ? 'auto' : 'smooth')
      forceScrollRef.current = false
    } else {
      setHasNewMessage(true)
    }
  }, [orderedMessages, nearBottom, scrollToLatest])

  const toggleNotifications = async () => {
    if (!notificationsSupported) return
    if (notificationsEnabled) {
      localStorage.setItem('crm-notifications', 'disabled')
      setNotificationsEnabled(false)
      return
    }
    const permission = Notification.permission === 'default' ? await Notification.requestPermission() : Notification.permission
    if (permission === 'granted') {
      localStorage.setItem('crm-notifications', 'enabled')
      setNotificationsEnabled(true)
    } else {
      localStorage.setItem('crm-notifications', 'disabled')
      setNotificationsEnabled(false)
    }
  }

  const send = useMutation({
    mutationFn: () => adminChatService.sendMessage(selectedId!, text.trim()),
    onSuccess: () => { setText(''); invalidate() },
  })
  const take = useMutation({ mutationFn: () => adminChatService.takeSession(selectedId!), onSuccess: invalidate })
  const close = useMutation({ mutationFn: () => adminChatService.closeSession(selectedId!), onSuccess: invalidate })
  const priority = useMutation({
    mutationFn: (value: ChatSession['priority']) => adminChatService.setPriority(selectedId!, value),
    onSuccess: invalidate,
  })
  const assignQueue = useMutation({
    mutationFn: (queueId: number) => adminChatService.assignQueue(selectedId!, queueId),
    onSuccess: invalidate,
  })

  return (
    <ThemeProvider theme={crmTheme}>
      <Stack spacing={2} sx={{ minHeight: 'calc(100dvh - 8rem)', height: { xs: 'auto', lg: 'calc(100dvh - 8rem)' }, minWidth: 0, color: '#0f172a' }}>
        <Stack direction={{ xs: 'column', md: 'row' }} sx={{ justifyContent: 'space-between', alignItems: { md: 'center' }, gap: 1 }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>Bandeja omnicanal</Typography>
            <Typography variant="body2" color="text.secondary">Ecommerce, WhatsApp, Facebook e Instagram en una sola conversación.</Typography>
          </Box>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <Button size="small" variant="outlined" startIcon={notificationsEnabled ? <BellOff size={16} /> : <Bell size={16} />} disabled={!notificationsSupported || Notification.permission === 'denied'} onClick={toggleNotifications}>
              {!notificationsSupported ? 'Notificaciones no disponibles' : Notification.permission === 'denied' ? 'Notificaciones bloqueadas' : notificationsEnabled ? 'Desactivar notificaciones' : 'Activar notificaciones'}
            </Button>
            <Chip size="small" color={connected ? 'success' : 'warning'} label={connected ? 'Tiempo real conectado' : 'Reconectando tiempo real'} />
          </Stack>
        </Stack>

        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} sx={{ flex: 1, minHeight: 0 }}>
          <Paper variant="outlined" sx={{ width: { xs: '100%', lg: 320 }, maxHeight: { xs: 400, lg: 'none' }, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Stack spacing={1} sx={{ p: 1.5, borderBottom: '1px solid #e2e8f0' }}>
              <TextField size="small" placeholder="Buscar cliente o identificador" value={search} onChange={(event) => setSearch(event.target.value)} />
              <Stack direction="row" spacing={1}>
                <TextField select size="small" label="Canal" value={channel} onChange={(event) => setChannel(event.target.value)} fullWidth>
                  <MenuItem value="all">Todos</MenuItem><MenuItem value="whatsapp">WhatsApp Cloud</MenuItem><MenuItem value="whatsapp_web">WhatsApp Web experimental</MenuItem><MenuItem value="facebook">Facebook</MenuItem><MenuItem value="instagram">Instagram</MenuItem><MenuItem value="ecommerce">Ecommerce</MenuItem>
                </TextField>
                <TextField select size="small" label="Estado" value={status} onChange={(event) => setStatus(event.target.value)} fullWidth>
                  <MenuItem value="all">Todos</MenuItem><MenuItem value="waiting">Pendientes</MenuItem><MenuItem value="active">Abiertos</MenuItem><MenuItem value="closed">Cerrados</MenuItem><MenuItem value="bot">Con bot</MenuItem>
                </TextField>
                <Tooltip title="Actualizar"><IconButton onClick={() => sessions.refetch()}><RefreshCw size={17} /></IconButton></Tooltip>
              </Stack>
              <FormControlLabel control={<Switch size="small" checked={unanswered} onChange={(event) => setUnanswered(event.target.checked)} />} label="Sin responder" />
            </Stack>
            <Box sx={{ flex: 1, overflowY: 'auto' }}>
              {sessions.isLoading && <Stack sx={{ alignItems: 'center', p: 4 }}><CircularProgress size={24} /></Stack>}
              {!sessions.isLoading && !sessions.data?.length && <Stack sx={{ alignItems: 'center', p: 4, color: 'text.secondary' }}><Inbox size={32} /><Typography variant="body2">Sin conversaciones</Typography></Stack>}
              {sessions.data?.map((session) => (
                <Box
                  component="button"
                  key={session.id}
                  onClick={() => setSelectedId(session.id)}
                  sx={{
                    width: '100%', border: 0, borderBottom: '1px solid #e2e8f0', p: 1.5,
                    textAlign: 'left', cursor: 'pointer', bgcolor: selectedId === session.id ? '#fff7ed' : '#fff',
                    borderLeft: selectedId === session.id ? '3px solid #b45309' : '3px solid transparent',
                    '&:hover': { bgcolor: '#f8fafc' },
                  }}
                >
                  <Stack direction="row" spacing={1} sx={{ justifyContent: 'space-between' }}>
                    <Box sx={{ minWidth: 0 }}>
                      <Stack direction="row" useFlexGap spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap', minWidth: 0 }}><Typography variant="body2" noWrap sx={{ fontWeight: 700 }}>{session.user_name}</Typography>{session.unread_by_agent > 0 && <Chip size="small" color="primary" label={session.unread_by_agent} />}</Stack>
                      <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>{session.last_message || 'Sin mensajes'}</Typography>
                    </Box>
                    <Stack spacing={0.5} sx={{ alignItems: 'flex-end' }}><ChannelBadge channel={session.channel} compact /><Chip size="small" label={statusLabel[session.status]} color={statusColor[session.status]} /></Stack>
                  </Stack>
                </Box>
              ))}
            </Box>
          </Paper>

          {!selected ? (
            <Paper variant="outlined" sx={{ flex: 1, display: 'grid', placeItems: 'center', color: '#64748b' }}><Stack sx={{ alignItems: 'center' }}><Inbox size={48} /><Typography>Selecciona una conversación</Typography></Stack></Paper>
          ) : (
            <Paper variant="outlined" sx={{ flex: 1, minWidth: 0, minHeight: { xs: 480, lg: 0 }, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Stack direction={{ xs: 'column', md: 'row' }} sx={{ justifyContent: 'space-between', alignItems: { md: 'center' }, p: 1.5, gap: 1, borderBottom: '1px solid #e2e8f0' }}>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}><Avatar sx={{ bgcolor: '#b45309' }}>{selected.user_name.charAt(0).toUpperCase()}</Avatar><Box><Typography sx={{ fontWeight: 800 }}>{selected.user_name}</Typography><Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><ChannelBadge channel={selected.channel} /><Typography variant="caption" color="text.secondary">{selected.external_thread_id || selected.user_cedula}</Typography></Stack></Box></Stack>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  <TextField
                    select
                    size="small"
                    label="Cola"
                    value={selected.queue_id ?? ''}
                    onChange={(event) => assignQueue.mutate(Number(event.target.value))}
                    sx={{ minWidth: 130 }}
                  >
                    {queues.data?.filter((queue) => queue.active).map((queue) => (
                      <MenuItem key={queue.id} value={queue.id}>{queue.name}</MenuItem>
                    ))}
                  </TextField>
                  <TextField select size="small" label="Prioridad" value={selected.priority} onChange={(event) => priority.mutate(event.target.value as ChatSession['priority'])}><MenuItem value="low">Baja</MenuItem><MenuItem value="normal">Normal</MenuItem><MenuItem value="high">Alta</MenuItem><MenuItem value="urgent">Urgente</MenuItem></TextField>
                  {(selected.status === 'waiting' || selected.status === 'bot') && <Button size="small" variant="outlined" startIcon={<UserCheck size={16} />} disabled={take.isPending} onClick={() => take.mutate()}>Tomar</Button>}
                  {selected.status !== 'closed' && <Button size="small" color="error" variant="outlined" disabled={close.isPending} onClick={() => close.mutate()}>Cerrar</Button>}
                </Stack>
              </Stack>
              <Stack ref={messagesBoxRef} onScroll={(event) => { const box = event.currentTarget; const closeToBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 96; setNearBottom(closeToBottom); if (closeToBottom) setHasNewMessage(false) }} spacing={1.5} sx={{ position: 'relative', flex: 1, overflowY: 'auto', overflowX: 'hidden', p: 2, bgcolor: '#f8fafc', scrollBehavior: 'smooth' }}>
                {messages.isLoading && <Stack sx={{ alignItems: 'center', p: 4 }}><CircularProgress size={24} /></Stack>}
                {orderedMessages.map((message) => <ConversationMessage key={message.id} message={message} />)}
              </Stack>
              {hasNewMessage && <Button onClick={() => scrollToLatest()} startIcon={<ArrowDown size={16} />} variant="contained" size="small" sx={{ alignSelf: 'center', mb: 1, borderRadius: 99 }}>Nuevo mensaje</Button>}
              <Box sx={{ p: 1.5, borderTop: '1px solid #e2e8f0' }}>
                {send.error && <Alert severity="error" sx={{ mb: 1 }}>{(send.error as any).response?.data?.error || 'No fue posible enviar el mensaje.'}</Alert>}
                <Stack direction="row" spacing={1}>
                  <TextField fullWidth size="small" multiline maxRows={4} value={text} disabled={selected.status === 'closed'} placeholder={selected.status === 'closed' ? 'Conversación cerrada' : `Responder por ${selected.channel}`} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (text.trim() && !send.isPending && selected.status !== 'closed') send.mutate() } }} />
                  <IconButton aria-label="Enviar mensaje" color="primary" disabled={!text.trim() || send.isPending || selected.status === 'closed'} onClick={() => send.mutate()}>{send.isPending ? <CircularProgress size={20} /> : <Send size={20} />}</IconButton>
                </Stack>
              </Box>
            </Paper>
          )}
        </Stack>
      </Stack>
    </ThemeProvider>
  )
}
