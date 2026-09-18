/** Configuración segura de cuentas Meta; los secretos nunca se vuelven a mostrar. */
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Box, Button, Card, CardContent, Checkbox, Chip, Divider, FormControlLabel,
  MenuItem, Stack, Switch, TextField, ThemeProvider, Typography,
} from '@mui/material'
import { adminChatService, type MetaConnection, type MetaIntegration, type MetaIntegrationInput } from '../services/admin_chat'
import { crmTheme } from '../theme/crmTheme'

const emptyForm: MetaIntegrationInput = {
  name: '', channel: 'whatsapp', app_id: '', external_account_id: '', business_id: '',
  phone_number_id: '', page_id: '', instagram_account_id: '', graph_api_version: '',
  configuration: { bot_enabled: false },
}

export default function MetaIntegrationsPage() {
  const client = useQueryClient()
  const [form, setForm] = useState<MetaIntegrationInput>(emptyForm)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [credentialEdit, setCredentialEdit] = useState<Partial<MetaIntegrationInput>>({})
  const [selectedPages, setSelectedPages] = useState<Record<number, string[]>>({})
  const [selectedInstagram, setSelectedInstagram] = useState<Record<number, string[]>>({})
  const integrations = useQuery({ queryKey: ['meta-integrations'], queryFn: adminChatService.getIntegrations })
  const connections = useQuery({ queryKey: ['meta-connections'], queryFn: adminChatService.getMetaConnections })
  const create = useMutation({
    mutationFn: adminChatService.createIntegration,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
      setForm(emptyForm)
      setError('')
    },
    onError: (reason: any) => setError(JSON.stringify(reason.response?.data ?? 'No fue posible guardar.')),
  })
  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<MetaIntegrationInput> }) => adminChatService.updateIntegration(id, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
      setEditingId(null)
      setCredentialEdit({})
      setError('')
    },
    onError: (reason: any) => setError(JSON.stringify(reason.response?.data ?? 'No fue posible actualizar.')),
  })
  const validate = useMutation({
    mutationFn: ({ id, activate }: { id: number; activate: boolean }) => adminChatService.validateIntegration(id, activate),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
      setError('')
    },
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'Meta no pudo validar la cuenta.'),
  })
  const instagramOAuth = useMutation({
    mutationFn: adminChatService.startInstagramOAuth,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
    onError: (reason: any) => setError(JSON.stringify(reason.response?.data ?? 'No fue posible iniciar el acceso de Instagram.')),
  })
  const metaOAuth = useMutation({
    mutationFn: adminChatService.startMetaOAuth,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'No fue posible iniciar la conexión con Meta.'),
  })
  const selectAccounts = useMutation({
    mutationFn: ({ id, facebook_page_ids, instagram_account_ids }: {
      id: number
      facebook_page_ids: string[]
      instagram_account_ids: string[]
    }) => adminChatService.selectMetaAccounts(id, { facebook_page_ids, instagram_account_ids }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-connections'] })
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
      setError('')
    },
    onError: (reason: any) => setError(JSON.stringify(reason.response?.data ?? 'No fue posible conectar las cuentas seleccionadas.')),
  })
  const disconnect = useMutation({
    mutationFn: adminChatService.disconnectMetaConnection,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-connections'] })
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
    },
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'No fue posible desconectar la cuenta.'),
  })
  const disconnectIntegration = useMutation({
    mutationFn: adminChatService.disconnectIntegration,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['meta-integrations'] })
      setEditingId(null)
      setCredentialEdit({})
      setError('')
    },
    onError: (reason: any) => setError(reason.response?.data?.detail ?? 'No fue posible desconectar.'),
  })
  useEffect(() => {
    if (!connections.data) return
    setSelectedPages(Object.fromEntries(connections.data.map((connection) => [
      connection.id,
      connection.facebook_pages.filter((page) => page.is_selected).map((page) => page.page_id),
    ])))
    setSelectedInstagram(Object.fromEntries(connections.data.map((connection) => [
      connection.id,
      connection.facebook_pages
        .map((page) => page.instagram_account)
        .filter((account) => account?.is_selected)
        .map((account) => account!.instagram_account_id),
    ])))
  }, [connections.data])
  useEffect(() => {
    const result = new URLSearchParams(window.location.search).get('instagram_oauth')
    if (result === 'success') setError('')
    else if (result) setError('Instagram no pudo completar la autorización. Inicie el acceso nuevamente.')
  }, [])
  const toggle = (values: Record<number, string[]>, setter: typeof setSelectedPages, connectionId: number, id: string) => {
    const current = values[connectionId] ?? []
    setter({ ...values, [connectionId]: current.includes(id) ? current.filter((value) => value !== id) : [...current, id] })
  }
  const connectionStatus = (connection: MetaConnection) => {
    if (connection.token_status === 'revoked') return { label: 'Desconectada', color: 'default' as const }
    if (connection.token_status === 'expired') return { label: 'Token expirado', color: 'error' as const }
    if (connection.token_status === 'error') return { label: 'Error', color: 'error' as const }
    if (connection.is_active) return { label: 'Cuentas autorizadas', color: 'info' as const }
    return { label: 'Pendiente de selección', color: 'warning' as const }
  }
  const integrationStatus = (integration: MetaIntegration) => {
    if (integration.connection_status === 'error') return { label: 'Validación fallida', color: 'error' as const }
    if (integration.connection_status === 'disconnected') return { label: 'Desconectada', color: 'default' as const }
    if (integration.active && integration.connection_status === 'connected') return { label: 'Mensajería comprobada', color: 'success' as const }
    if (integration.active && integration.last_webhook_at) return { label: 'Webhook recibido; falta envío', color: 'info' as const }
    if (integration.active) return { label: 'Graph validado; esperando webhook', color: 'warning' as const }
    return { label: 'Pendiente de validar', color: 'warning' as const }
  }
  const maskId = (id: string) => id ? `${'•'.repeat(Math.max(0, id.length - 4))}${id.slice(-4)}` : 'Sin configurar'
  const set = (name: keyof MetaIntegrationInput, value: unknown) => setForm((current) => ({ ...current, [name]: value }))
  const setCredential = (name: keyof MetaIntegrationInput, value: unknown) => {
    setCredentialEdit((current) => ({ ...current, [name]: value }))
  }
  const saveCredentials = (id: number) => {
    const payload = Object.fromEntries(
      Object.entries(credentialEdit).filter(([, value]) => value !== '' && value !== undefined),
    ) as Partial<MetaIntegrationInput>
    if (Object.keys(payload).length) update.mutate({ id, payload })
  }

  return (
    <ThemeProvider theme={crmTheme}>
    <Stack spacing={3}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Facebook e Instagram</Typography>
        <Typography color="text.secondary">Conecta páginas de Facebook y cuentas profesionales de Instagram sin compartir credenciales con el navegador.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {new URLSearchParams(window.location.search).get('meta_oauth') === 'select' && (
        <Alert severity="info">Meta autorizó el acceso. Selecciona las páginas y cuentas que quieres conectar.</Alert>
      )}
      {new URLSearchParams(window.location.search).get('meta_oauth') === 'denied' && (
        <Alert severity="warning">La autorización fue cancelada en Meta.</Alert>
      )}
      {['error', 'invalid_state'].includes(new URLSearchParams(window.location.search).get('meta_oauth') ?? '') && (
        <Alert severity="error">No fue posible validar la autorización. Inicia nuevamente la conexión.</Alert>
      )}
      <Card variant="outlined"><CardContent>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6">Conexión oficial de Meta</Typography>
            <Typography variant="body2" color="text.secondary">Solicita exclusivamente permisos de Facebook Pages e Instagram Professional.</Typography>
          </Box>
          <Button variant="contained" disabled={metaOAuth.isPending} onClick={() => metaOAuth.mutate()}>
            {metaOAuth.isPending ? 'Conectando…' : 'Conectar Facebook e Instagram'}
          </Button>
        </Stack>
      </CardContent></Card>
      {connections.data?.map((connection) => {
        const statusInfo = connectionStatus(connection)
        return (
          <Card key={connection.id} variant="outlined"><CardContent>
            <Stack spacing={2}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'center' } }}>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontWeight: 700 }}>{connection.token_status === 'revoked' ? 'Cuenta Meta desvinculada' : `Cuenta Meta ${connection.facebook_user_id}`}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {connection.token_status === 'revoked' ? 'Conectar otra cuenta' : `${connection.facebook_pages.length} página(s) disponible(s)`}
                  </Typography>
                </Box>
                <Chip size="small" label={statusInfo.label} color={statusInfo.color} />
              </Stack>
              <Divider />
              {connection.token_status === 'revoked' && <Alert severity="info">Cuenta desconectada. Conecta otra cuenta con Meta para volver a recibir mensajes.</Alert>}
              {connection.token_status !== 'revoked' && connection.facebook_pages.length === 0 && (
                <Alert severity="warning">Meta no devolvió páginas administradas. Verifica roles y permisos de la cuenta.</Alert>
              )}
              {connection.token_status !== 'revoked' && connection.facebook_pages.map((page) => (
                <Box key={page.page_id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
                  <FormControlLabel
                    control={<Checkbox checked={(selectedPages[connection.id] ?? []).includes(page.page_id)} onChange={() => toggle(selectedPages, setSelectedPages, connection.id, page.page_id)} />}
                    label={`Facebook: ${page.page_name} (${page.page_id})`}
                  />
                  {page.instagram_account && (
                    <FormControlLabel
                      sx={{ display: 'flex', ml: 3 }}
                      control={<Checkbox checked={(selectedInstagram[connection.id] ?? []).includes(page.instagram_account.instagram_account_id)} onChange={() => toggle(selectedInstagram, setSelectedInstagram, connection.id, page.instagram_account!.instagram_account_id)} />}
                      label={`Instagram: @${page.instagram_account.username || page.instagram_account.instagram_account_id}`}
                    />
                  )}
                </Box>
              ))}
              {connection.token_status !== 'revoked' && <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  disabled={selectAccounts.isPending || connection.facebook_pages.length === 0}
                  onClick={() => selectAccounts.mutate({
                    id: connection.id,
                    facebook_page_ids: selectedPages[connection.id] ?? [],
                    instagram_account_ids: selectedInstagram[connection.id] ?? [],
                  })}
                >Guardar selección</Button>
                <Button
                  color="error"
                  disabled={disconnect.isPending}
                  onClick={() => window.confirm('¿Desconectar esta cuenta de Meta? Las conversaciones existentes se conservarán.') && disconnect.mutate(connection.id)}
                >Desconectar</Button>
              </Stack>}
            </Stack>
          </CardContent></Card>
        )
      })}
      <Divider><Chip label="Configuración manual y estado por canal" size="small" /></Divider>
      {new URLSearchParams(window.location.search).get('instagram_oauth') === 'success' && (
        <Alert severity="info">Instagram devolvió un token y una cuenta profesional. Valida la integración antes de activarla; la mensajería se confirma al recibir y responder un mensaje real.</Alert>
      )}
      <Card variant="outlined"><CardContent>
        <Typography variant="h6" gutterBottom>Nueva integración manual</Typography>
        {form.channel === 'whatsapp' && <Alert severity="info" sx={{ mb: 2 }}>
          WhatsApp Cloud API se configura manualmente: WABA ID, Phone Number ID y token. Guardar no activa el número. Después usa “Validar y activar”; el backend comprobará la cuenta y los permisos sin enviar mensajes de prueba.
        </Alert>}
        <Stack spacing={2}>
          <TextField label="Nombre" value={form.name} onChange={(event) => set('name', event.target.value)} required />
          <TextField select label="Canal" value={form.channel} onChange={(event) => set('channel', event.target.value)}>
            <MenuItem value="whatsapp">WhatsApp</MenuItem><MenuItem value="facebook">Facebook</MenuItem><MenuItem value="instagram">Instagram</MenuItem>
          </TextField>
          <TextField label="Versión Graph API" placeholder="Definida en Meta for Developers" value={form.graph_api_version} onChange={(event) => set('graph_api_version', event.target.value)} />
          <TextField label="App ID" value={form.app_id} onChange={(event) => set('app_id', event.target.value)} />
          <TextField label={form.channel === 'whatsapp' ? 'WABA ID' : 'Cuenta externa ID'} value={form.external_account_id} onChange={(event) => set('external_account_id', event.target.value)} />
          {form.channel === 'whatsapp' && <TextField label="Phone Number ID" value={form.phone_number_id} onChange={(event) => set('phone_number_id', event.target.value)} />}
          {form.channel === 'whatsapp' && <TextField label="Business ID (opcional)" value={form.business_id} onChange={(event) => set('business_id', event.target.value)} />}
          {form.channel === 'facebook' && <TextField label="Page ID" value={form.page_id} onChange={(event) => set('page_id', event.target.value)} />}
          {form.channel === 'instagram' && <TextField label="Instagram Professional Account ID" value={form.instagram_account_id} onChange={(event) => set('instagram_account_id', event.target.value)} />}
          <TextField label="Access Token" type="password" autoComplete="new-password" onChange={(event) => set('access_token', event.target.value)} helperText="Solo se envía al backend; después no se mostrará." />
          <TextField label="App Secret" type="password" autoComplete="new-password" onChange={(event) => set('app_secret', event.target.value)} />
          <TextField label="Webhook Verify Token" type="password" autoComplete="new-password" onChange={(event) => set('verify_token', event.target.value)} />
          <FormControlLabel control={<Switch checked={Boolean(form.configuration.bot_enabled)} onChange={(event) => set('configuration', { ...form.configuration, bot_enabled: event.target.checked })} />} label="Permitir respuestas automáticas de Ollama" />
          <Button variant="contained" disabled={create.isPending} onClick={() => create.mutate(form)}>Guardar integración</Button>
        </Stack>
      </CardContent></Card>
      <Stack spacing={1}>
        {validate.data && <Alert severity={validate.data.valid ? 'info' : 'error'}>{validate.data.valid ? `Graph confirmó la cuenta ${validate.data.name || validate.data.remote_id}. La recepción y el envío se verifican con una conversación real.` : validate.data.detail}</Alert>}
        {(['facebook', 'instagram', 'whatsapp'] as const).map((channel) => <Stack key={channel} spacing={1}>
          <Typography variant="h6" sx={{ mt: 2 }}>{channel === 'facebook' ? 'Facebook Messenger' : channel === 'instagram' ? 'Instagram Professional' : 'WhatsApp Business Cloud API'}</Typography>
          {!integrations.data?.some((item) => item.channel === channel) && <Typography variant="body2" color="text.secondary">No hay cuentas configuradas.</Typography>}
          {integrations.data?.filter((item) => item.channel === channel).map((integration) => (
          <Card key={integration.id} variant="outlined"><CardContent>
            <Stack spacing={1.5}>
            <Stack direction={{ xs: 'column', md: 'row' }} sx={{ alignItems: { md: 'center' }, gap: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography sx={{ fontWeight: 700 }}>{integration.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {integration.connection_status === 'disconnected' ? 'Cuenta anterior desvinculada; historial conservado' : (
                  integration.channel === 'whatsapp'
                    ? `${integration.display_phone_number || 'Número pendiente'} · WABA ${integration.external_account_id || 'sin ID'} · Phone ID ${maskId(integration.phone_number_id)}`
                    : integration.channel === 'facebook'
                      ? `Página ${integration.page_id || 'sin ID'}`
                      : `Cuenta ${integration.instagram_account_id || 'sin ID'}`)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Última validación: {integration.last_validated_at ? new Date(integration.last_validated_at).toLocaleString() : 'pendiente'}
                </Typography>
              </Box>
              <Chip label={integrationStatus(integration).label} color={integrationStatus(integration).color} size="small" />
              <Chip label={integration.has_access_token ? 'Token configurado' : 'Sin token'} color={integration.has_access_token ? 'success' : 'warning'} size="small" />
              {integration.managed_by_meta_oauth && <Chip label="Gestionado por OAuth Meta" color="info" size="small" />}
              <Button size="small" variant="outlined" disabled={validate.isPending || !integration.has_access_token} onClick={() => validate.mutate({ id: integration.id, activate: false })}>Validar Graph</Button>
              {!integration.active && integration.has_access_token && <Button size="small" variant="contained" disabled={validate.isPending} onClick={() => validate.mutate({ id: integration.id, activate: true })}>Validar y activar</Button>}
              {integration.channel === 'instagram' && !integration.managed_by_meta_oauth && (
                <Button size="small" variant="contained" disabled={instagramOAuth.isPending} onClick={() => instagramOAuth.mutate(integration.id)}>
                  Conectar Instagram
                </Button>
              )}
              {!integration.managed_by_meta_oauth && <Button size="small" onClick={() => { setEditingId(integration.id); setCredentialEdit({}) }}>Rotar credenciales</Button>}
              {!integration.managed_by_meta_oauth && <Button size="small" color="error" disabled={disconnectIntegration.isPending || integration.connection_status === 'disconnected'} onClick={() => window.confirm('¿Desconectar esta cuenta? Sus conversaciones se conservarán.') && disconnectIntegration.mutate(integration.id)}>Desconectar</Button>}
            </Stack>
            {integration.active && <FormControlLabel
              control={<Switch checked={Boolean(integration.configuration.bot_enabled)} disabled={update.isPending} onChange={(event) => update.mutate({
                id: integration.id,
                payload: { configuration: { ...integration.configuration, bot_enabled: event.target.checked } },
              })} />}
              label="Permitir respuestas reactivas de Ollama en esta cuenta"
            />}
            {integration.last_error && <Alert severity="error">{integration.last_error}</Alert>}
            {integration.connection_status === 'disconnected' && <Alert severity="info">La cuenta anterior ya no puede enviar. Para usar otra cuenta, crea una integración nueva; el historial permanece disponible.</Alert>}
            {editingId === integration.id && (
              <Stack spacing={1.5} sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Alert severity="info">Los valores actuales no se muestran. Complete únicamente los que desea reemplazar.</Alert>
                <TextField size="small" label="Nuevo Access Token" type="password" autoComplete="new-password" onChange={(event) => setCredential('access_token', event.target.value)} />
                <TextField size="small" label="Nuevo App Secret" type="password" autoComplete="new-password" onChange={(event) => setCredential('app_secret', event.target.value)} />
                <TextField size="small" label="Nuevo Verify Token" type="password" autoComplete="new-password" onChange={(event) => setCredential('verify_token', event.target.value)} />
                <TextField size="small" label="Versión Graph API" defaultValue={integration.graph_api_version} onChange={(event) => setCredential('graph_api_version', event.target.value)} />
                <TextField size="small" label="Vencimiento del token" type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} onChange={(event) => setCredential('token_expires_at', event.target.value || null)} />
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" disabled={update.isPending} onClick={() => saveCredentials(integration.id)}>Guardar rotación</Button>
                  <Button onClick={() => { setEditingId(null); setCredentialEdit({}) }}>Cancelar</Button>
                </Stack>
              </Stack>
            )}
            </Stack>
          </CardContent></Card>
        ))}
        </Stack>)}
      </Stack>
    </Stack>
    </ThemeProvider>
  )
}
