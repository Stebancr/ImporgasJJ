import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Box, Button, Chip, Dialog, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import api from '../services/admin_api'
import { useAuth } from '../context/AuthContext'
import { adminChatService, type ChatSession } from '../services/admin_chat'

export interface QuickReply {
  id: number; name: string; category: string; text: string; active: boolean; channels: string[]
  variables: string[]; favorite: boolean; last_used_at: string | null; author_name: string
  updated_at: string; attachment_url: string; attachment_metadata: { name?: string; mime_type?: string }
}
const channels = ['ecommerce', 'whatsapp_web', 'facebook', 'instagram', 'whatsapp']
const variables = ['nombre_cliente', 'nombre_agente', 'numero_visita', 'fecha_visita', 'costo_final', 'enlace_pdf', 'nombre_producto', 'enlace_producto']
type Draft = { name: string; category: string; text: string; channels: string[]; active: boolean; id?: number }
const empty: Draft = { name: '', category: '', text: '', channels: ['whatsapp_web', 'facebook', 'instagram', 'ecommerce'], active: true }

export default function TemplateDialog({ open, onClose, session, initialText = '', onInsert }: {
  open: boolean; onClose: () => void; session?: ChatSession; initialText?: string
  onInsert?: (text: string, template: QuickReply, values: Record<string, string>, file?: File) => void
}) {
  const cache = useQueryClient()
  const { user } = useAuth()
  const canManage = user?.tipo_usuario === 4
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [view, setView] = useState('all')
  const [selected, setSelected] = useState<QuickReply | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState('')
  const [draft, setDraft] = useState<Draft | null>(null)
  const [file, setFile] = useState<File>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const list = useQuery({ queryKey: ['crm-templates', search, session?.channel], enabled: open,
    queryFn: async () => (await api.get<QuickReply[]>('/crm-chat/templates/', { params: { search, channel: session?.channel } })).data })
  const items = (list.data || []).filter(t => (!category || t.category === category) && (view !== 'favorites' || t.favorite) && (view !== 'recent' || t.last_used_at))
    .sort((a, b) => view === 'recent' ? (b.last_used_at || '').localeCompare(a.last_used_at || '') : a.name.localeCompare(b.name))
  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError('')
    try { await fn() } catch (e: any) { setError(e.response?.data?.error || JSON.stringify(e.response?.data || 'No fue posible completar la operación.')) }
    finally { setBusy(false) }
  }
  const refresh = () => cache.invalidateQueries({ queryKey: ['crm-templates'] })
  const save = () => run(async () => {
    if (!draft) return
    const data = new FormData()
    data.append('name', draft.name); data.append('category', draft.category); data.append('text', draft.text)
    data.append('channels', JSON.stringify(draft.channels)); data.append('active', String(draft.active))
    if (file) data.append('file', file)
    await api.post(`/crm-chat/templates/${draft.id ? `${draft.id}/` : ''}`, data, { headers: { 'Content-Type': undefined } })
    setDraft(null); setFile(undefined); refresh()
  })
  const select = (template: QuickReply) => {
    setSelected(template); setPreview(''); setError('')
    setValues({ nombre_cliente: session?.user_name || '', nombre_agente: session?.agent_name || '' })
  }
  const insert = () => run(async () => {
    if (!selected || !session || !onInsert) return
    const res = await api.post(`/crm-chat/templates/${selected.id}/preview/`, { session_id: session.id, variables: values })
    if (res.data.text !== preview) { setPreview(res.data.text); return }
    let attachment: File | undefined
    if (selected.attachment_url) {
      const blob = await adminChatService.getAttachmentBlob(selected.attachment_url)
      attachment = new File([blob], selected.attachment_metadata.name || 'adjunto', { type: selected.attachment_metadata.mime_type || blob.type })
    }
    onInsert(preview, selected, values, attachment); onClose(); setSelected(null); setPreview('')
  })
  return <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="md">
    <DialogTitle>Plantillas internas del CRM</DialogTitle>
    <DialogContent>
      <Alert severity="info" sx={{ mb: 2 }}>Respuestas reutilizables. Insertar prepara un borrador editable; no envía mensajes ni utiliza plantillas de pago de Meta.</Alert>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {draft ? <Stack spacing={2}>
        <TextField label="Nombre" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} />
        <TextField label="Categoría" value={draft.category} onChange={e => setDraft({ ...draft, category: e.target.value })} />
        <TextField select slotProps={{ select: { multiple: true } }} label="Canales" value={draft.channels} onChange={e => setDraft({ ...draft, channels: typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value })}>{channels.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}</TextField>
        <TextField label="Texto (sin HTML)" multiline minRows={4} value={draft.text} onChange={e => setDraft({ ...draft, text: e.target.value })} />
        <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>{variables.map(v => <Chip key={v} label={`{{${v}}}`} onClick={() => setDraft({ ...draft, text: draft.text + ` {{${v}}}` })} />)}</Stack>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{draft.text}</Typography>
        <Button component="label">Adjunto opcional<input hidden type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.docx,.xlsx,.mp3,.ogg,.wav,.m4a,.mp4,.webm" onChange={e => setFile(e.target.files?.[0])} /></Button>
        {file && <Chip label={file.name} onDelete={() => setFile(undefined)} />}
        <Stack direction="row" spacing={1}><Button onClick={() => setDraft(null)}>Cancelar</Button><Button disabled={busy || !draft.name.trim() || !draft.text.trim()} onClick={save}>Guardar</Button></Stack>
      </Stack> : <>
        <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ gap: 1, mb: 2 }}>
          <TextField size="small" label="Buscar por nombre o texto" value={search} onChange={e => setSearch(e.target.value)} />
          <TextField select size="small" label="Categoría" value={category} onChange={e => setCategory(e.target.value)} sx={{ minWidth: 140 }}><MenuItem value="">Todas</MenuItem>{[...new Set((list.data || []).map(t => t.category))].map(c => <MenuItem key={c} value={c}>{c || 'Sin categoría'}</MenuItem>)}</TextField>
          <TextField select size="small" value={view} onChange={e => setView(e.target.value)}><MenuItem value="all">Todas</MenuItem><MenuItem value="favorites">Favoritas</MenuItem><MenuItem value="recent">Recientes</MenuItem></TextField>
          {canManage && <Button onClick={() => { setDraft({ ...empty, text: initialText }); setFile(undefined) }}>Crear plantilla</Button>}
        </Stack>
        <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>{items.map(t => <Box key={t.id} sx={{ p: 1, borderBottom: '1px solid #ddd' }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}><Button onClick={() => select(t)}>{t.name}</Button><Chip size="small" label={t.category || 'Sin categoría'} />{!t.active && <Chip label="Inactiva" size="small" />}<Button onClick={() => run(async () => { await api.post(`/crm-chat/templates/${t.id}/favorite/`); refresh() })}>{t.favorite ? '★' : '☆'}</Button>{canManage && <><Button onClick={() => { setDraft(t); setFile(undefined) }}>Editar</Button><Button onClick={() => run(async () => { await api.patch(`/crm-chat/templates/${t.id}/`, { active: !t.active }); refresh() })}>{t.active ? 'Desactivar' : 'Activar'}</Button></>}</Stack>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{t.text}</Typography>
          <Typography variant="caption">{t.author_name} · {new Date(t.updated_at).toLocaleString('es-CO')} · {t.channels.join(', ')}</Typography>
          {t.attachment_url && <Typography variant="caption" sx={{ display: 'block' }}>Adjunto: {t.attachment_metadata.name}</Typography>}
        </Box>)}</Box>
        {!list.isLoading && !items.length && <Typography>No hay plantillas para estos filtros.</Typography>}
        {selected && session && <Stack spacing={1} sx={{ mt: 2 }}>
          <Typography sx={{ fontWeight: 700 }}>Completar: {selected.name}</Typography>
          {selected.variables.map(v => <TextField key={v} size="small" label={v} value={values[v] || ''} onChange={e => { setValues({ ...values, [v]: e.target.value }); setPreview('') }} />)}
          {preview && <Alert severity="success" sx={{ whiteSpace: 'pre-wrap' }}>{preview}</Alert>}
          <Button disabled={busy} onClick={insert}>{preview ? 'Insertar y revisar en el chat' : 'Vista previa final'}</Button>
        </Stack>}
      </>}
      <Button sx={{ mt: 2 }} onClick={onClose}>Cerrar</Button>
    </DialogContent>
  </Dialog>
}
