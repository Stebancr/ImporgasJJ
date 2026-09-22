import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { io } from 'socket.io-client'
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, FormControlLabel, Stack, Switch, Typography } from '@mui/material'
import { adminChatService, type WhatsAppGatewayState } from '../services/admin_chat'

const labels: Record<WhatsAppGatewayState['status'], string> = {
  disconnected: 'Desconectado',
  waiting_for_qr: 'Esperando un código nuevo',
  qr_ready: 'Código QR disponible',
  connecting: 'Conectando',
  connected: 'Conectado',
  logged_out: 'Sesión cerrada',
  reconnecting: 'Reconectando',
  error: 'Error',
}

export default function WhatsAppWebGatewayCard() {
  const client = useQueryClient()
  const [liveState, setLiveState] = useState<WhatsAppGatewayState | null>(null)
  const [error, setError] = useState('')
  const status = useQuery({
    queryKey: ['whatsapp-web-gateway'],
    queryFn: adminChatService.getWhatsAppGatewayStatus,
    refetchInterval: 30_000,
  })

  useEffect(() => {
    let disposed = false
    let socket: ReturnType<typeof io> | undefined
    let refreshTimer: ReturnType<typeof setInterval> | undefined
    let refreshing = false

    const refreshToken = async (reconnect = false) => {
      if (disposed || refreshing) return
      refreshing = true
      try {
        const { token } = await adminChatService.getWhatsAppGatewayRealtimeToken()
        if (disposed) return
        if (!socket) {
          socket = io(window.location.origin, {
            path: '/whatsapp-gateway/socket.io',
            transports: ['websocket', 'polling'],
            auth: { token },
            autoConnect: false,
            reconnection: true,
            reconnectionDelayMax: 10_000,
          })
          socket.on('connect', () => setError(''))
          socket.on('gateway.state', (next: WhatsAppGatewayState) => {
            setLiveState(next)
            setError('')
            void client.invalidateQueries({ queryKey: ['whatsapp-web-gateway'] })
          })
          socket.on('connect_error', (reason) => {
            if (disposed) return
            setError(`No fue posible recibir el estado en tiempo real: ${reason.message}`)
            if (reason.message === 'unauthorized') void refreshToken(true)
          })
          socket.connect()
        } else {
          socket.auth = { token }
          if (reconnect && !socket.connected) socket.connect()
        }
      } catch (reason: any) {
        if (!disposed) setError(reason.response?.data?.detail ?? 'No fue posible autorizar el panel del gateway.')
      } finally {
        refreshing = false
      }
    }

    void refreshToken()
    // El token dura 120 segundos. Mantener uno reciente permite que Socket.IO
    // se autentique de nuevo si el gateway se reinicia o cambia de IP.
    refreshTimer = setInterval(() => { void refreshToken(false) }, 90_000)
    return () => {
      disposed = true
      if (refreshTimer) clearInterval(refreshTimer)
      socket?.removeAllListeners()
      socket?.disconnect()
    }
  }, [client])

  const command = useMutation({
    mutationFn: adminChatService.commandWhatsAppGateway,
    onSuccess: () => {
      setError('')
      void client.invalidateQueries({ queryKey: ['whatsapp-web-gateway'] })
    },
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'El gateway rechazó la operación.'),
  })
  const botToggle = useMutation({
    mutationFn: adminChatService.setWhatsAppGatewayBotEnabled,
    onSuccess: () => {
      setError('')
      void client.invalidateQueries({ queryKey: ['whatsapp-web-gateway'] })
    },
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'No fue posible actualizar el chatbot.'),
  })
  const current = status.data || liveState ? { ...(status.data ?? {}), ...(liveState ?? {}) } as WhatsAppGatewayState : undefined
  const isConnected = current?.status === 'connected'
  const isBusy = command.isPending || ['connecting', 'reconnecting'].includes(current?.status ?? '')

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'center' } }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6">WhatsApp Web Gateway</Typography>
              <Typography variant="body2" color="text.secondary">
                Canal experimental independiente mediante vinculación QR. No usa WhatsApp Business Account ni WhatsApp Cloud API.
              </Typography>
            </Box>
            {status.isLoading && !current ? <CircularProgress size={24} /> : (
              <Chip
                label={current ? labels[current.status] : 'Sin estado'}
                color={isConnected ? 'success' : current?.status === 'error' ? 'error' : 'default'}
                size="small"
              />
            )}
          </Stack>

          <Alert severity="warning">
            Esta integración usa una librería no oficial. WhatsApp puede desconectar o bloquear la sesión y no garantiza sincronizar todo el historial. Úsala como canal experimental y vincula únicamente un número autorizado por la empresa.
          </Alert>
          <Alert severity="info">
            El sistema solo responde a mensajes reales recibidos. No crea campañas, plantillas, mensajes proactivos ni funciones de Meta con cobro.
          </Alert>
          {error && <Alert severity="error">{error}</Alert>}
          {current?.last_error && <Alert severity="error">{current.last_error}</Alert>}

          {current?.qr_data_url && current.status === 'qr_ready' && (
            <Box sx={{ alignSelf: 'center', textAlign: 'center', maxWidth: 360 }}>
              <Box
                component="img"
                src={current.qr_data_url}
                alt="Código QR temporal para vincular WhatsApp Web"
                sx={{ width: '100%', maxWidth: 320, height: 'auto', display: 'block' }}
              />
              <Typography variant="caption" color="text.secondary">
                Abre WhatsApp en el teléfono, entra a Dispositivos vinculados y escanea este código. El QR no se guarda en el navegador ni en la base de datos.
              </Typography>
            </Box>
          )}

          {isConnected && current?.phone_number && (
            <Typography variant="body2">Número conectado: <strong>{current.phone_number}</strong></Typography>
          )}
          {current?.last_connected_at && (
            <Typography variant="body2" color="text.secondary">
              Última conexión: {new Date(current.last_connected_at).toLocaleString()}
            </Typography>
          )}
          <FormControlLabel
            control={(
              <Switch
                checked={Boolean(status.data?.bot_enabled)}
                disabled={botToggle.isPending}
                onChange={(event) => botToggle.mutate(event.target.checked)}
              />
            )}
            label="Habilitar chatbot Ollama para respuestas reactivas"
          />
          <Typography variant="caption" color="text.secondary">
            Ollama responderá únicamente después de recibir un mensaje real mientras esta sesión esté conectada. No inicia conversaciones ni envía campañas.
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            {!isConnected && (
              <Button variant="contained" color="success" disabled={isBusy} onClick={() => command.mutate('qr')}>
                {isBusy ? 'Conectando…' : 'Generar nuevo QR'}
              </Button>
            )}
            <Button variant="outlined" disabled={isBusy} onClick={() => command.mutate('reconnect')}>Reconectar</Button>
            <Button
              color="error"
              disabled={command.isPending || current?.status === 'logged_out'}
              onClick={() => window.confirm('¿Cerrar la sesión vinculada de WhatsApp Web? Deberás escanear un QR nuevo.') && command.mutate('logout')}
            >Cerrar sesión</Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}
