/** Configuración segura de cuentas Meta; los secretos nunca se vuelven a mostrar. */
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Box, Button, Card, CardContent, Chip, FormControlLabel,
  MenuItem, Stack, Switch, TextField, ThemeProvider, Typography,
} from '@mui/material'
import { adminChatService, type MetaIntegrationInput } from '../services/admin_chat'
import { crmTheme } from '../theme/crmTheme'

const emptyForm: MetaIntegrationInput = {
  name: '', channel: 'whatsapp', active: false, app_id: '', external_account_id: '',
  phone_number_id: '', page_id: '', instagram_account_id: '', graph_api_version: '',
  configuration: { bot_enabled: false },
}

export default function MetaIntegrationsPage() {
  const client = useQueryClient()
  const [form, setForm] = useState<MetaIntegrationInput>(emptyForm)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [credentialEdit, setCredentialEdit] = useState<Partial<MetaIntegrationInput>>({})
  const integrations = useQuery({ queryKey: ['meta-integrations'], queryFn: adminChatService.getIntegrations })
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
  const validate = useMutation({ mutationFn: adminChatService.validateIntegration })
  const instagramOAuth = useMutation({
    mutationFn: adminChatService.startInstagramOAuth,
    onSuccess: ({ authorization_url }) => window.location.assign(authorization_url),
    onError: (reason: any) => setError(JSON.stringify(reason.response?.data ?? 'No fue posible iniciar el acceso de Instagram.')),
  })
  useEffect(() => {
    const result = new URLSearchParams(window.location.search).get('instagram_oauth')
    if (result === 'success') setError('')
    else if (result) setError('Instagram no pudo completar la autorización. Inicie el acceso nuevamente.')
  }, [])
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
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Canales Meta</Typography>
        <Typography color="text.secondary">Tokens cifrados y configuración de WhatsApp, Messenger e Instagram.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {new URLSearchParams(window.location.search).get('instagram_oauth') === 'success' && (
        <Alert severity="success">Instagram quedó conectado. Ya puede validar y activar el canal.</Alert>
      )}
      <Card variant="outlined"><CardContent>
        <Typography variant="h6" gutterBottom>Nueva integración</Typography>
        <Stack spacing={2}>
          <TextField label="Nombre" value={form.name} onChange={(event) => set('name', event.target.value)} required />
          <TextField select label="Canal" value={form.channel} onChange={(event) => set('channel', event.target.value)}>
            <MenuItem value="whatsapp">WhatsApp</MenuItem><MenuItem value="facebook">Facebook</MenuItem><MenuItem value="instagram">Instagram</MenuItem>
          </TextField>
          <TextField label="Versión Graph API" placeholder="Definida en Meta for Developers" value={form.graph_api_version} onChange={(event) => set('graph_api_version', event.target.value)} />
          <TextField label="App ID" value={form.app_id} onChange={(event) => set('app_id', event.target.value)} />
          <TextField label="WABA / cuenta externa ID" value={form.external_account_id} onChange={(event) => set('external_account_id', event.target.value)} />
          {form.channel === 'whatsapp' && <TextField label="Phone Number ID" value={form.phone_number_id} onChange={(event) => set('phone_number_id', event.target.value)} />}
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
        {validate.data && <Alert severity={validate.data.valid ? 'success' : 'error'}>{validate.data.valid ? `Conexión válida: ${validate.data.name || validate.data.remote_id}` : validate.data.detail}</Alert>}
        {integrations.data?.map((integration) => (
          <Card key={integration.id} variant="outlined"><CardContent>
            <Stack direction={{ xs: 'column', md: 'row' }} sx={{ alignItems: { md: 'center' }, gap: 2 }}>
              <Box sx={{ flex: 1 }}><Typography sx={{ fontWeight: 700 }}>{integration.name}</Typography><Typography variant="body2" color="text.secondary">{integration.channel} · {integration.graph_api_version || 'sin versión'}</Typography></Box>
              <Chip label={integration.has_access_token ? 'Token configurado' : 'Sin token'} color={integration.has_access_token ? 'success' : 'warning'} size="small" />
              <Button size="small" variant="outlined" onClick={() => validate.mutate(integration.id)}>Probar</Button>
              {integration.channel === 'instagram' && (
                <Button size="small" variant="contained" disabled={instagramOAuth.isPending} onClick={() => instagramOAuth.mutate(integration.id)}>
                  Conectar Instagram
                </Button>
              )}
              <Button size="small" onClick={() => { setEditingId(integration.id); setCredentialEdit({}) }}>Rotar credenciales</Button>
              <Switch checked={integration.active} onChange={(event) => update.mutate({ id: integration.id, payload: { active: event.target.checked } })} />
            </Stack>
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
          </CardContent></Card>
        ))}
      </Stack>
    </Stack>
    </ThemeProvider>
  )
}
