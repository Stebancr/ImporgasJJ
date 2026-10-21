import { useState, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Box, Button, Chip, Dialog, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import api from '../services/admin_api'
import { useAuth } from '../context/AuthContext'
import { adminChatService, type ChatSession } from '../services/admin_chat'
import TemplateMessagePreview from './TemplateMessagePreview'
import MessageFormatToolbar from './MessageFormatToolbar'
import { channelText, channelTextLimits } from '../../components/chat/messageFormat'

export interface QuickReply {
  id: number; name: string; category: string; text: string; active: boolean; channels: string[]
  variables: string[]; favorite: boolean; last_used_at: string | null; author_name: string
  updated_at: string; attachment_url: string; attachment_metadata: { name?: string; mime_type?: string }
}
const channels = ['ecommerce', 'whatsapp_web', 'facebook', 'instagram', 'whatsapp']
const samples:Record<string,string> = {nombre_cliente:'María Pérez',nombre_agente:'Asesor de ejemplo',numero_visita:'V-123',fecha_visita:'20/10/2026',costo_final:'$80.000',enlace_pdf:'https://example.com/informe',nombre_producto:'Calentador de ejemplo',enlace_producto:'https://example.com/producto',numero_pedido:'PED-123',estado_pedido:'En preparación',nombre_tecnico:'Técnico de ejemplo',enlace_seguimiento:'https://example.com/seguimiento'}
samples.enlace_pago = 'https://example.com/pago'
const variables = Object.keys(samples)
const channelLabels:Record<string,string>={ecommerce:'E-commerce',whatsapp_web:'WhatsApp Web',whatsapp:'WhatsApp',facebook:'Facebook',instagram:'Instagram'}
function invalidText(text:string){return /{{|}}/.test(text.replace(/{{\s*([a-z_]+)\s*}}/g,(all,key)=>variables.includes(key)?'':all))}
const example=(text:string)=>text.replace(/{{\s*([a-z_]+)\s*}}/g,(_,key)=>samples[key]||'')
type Draft = { name: string; category: string; text: string; channels: string[]; active: boolean; id?: number; attachment_url?: string; attachment_metadata?: QuickReply['attachment_metadata'] }
const empty: Draft = { name: '', category: '', text: '', channels: ['whatsapp_web', 'facebook', 'instagram', 'ecommerce'], active: true }

export default function TemplateDialog({ open, onClose, session, initialText = '', onInsert }: {
  open: boolean; onClose: () => void; session?: ChatSession; initialText?: string
  onInsert?: (text: string, template: QuickReply, values: Record<string, string>, file?: File) => void
}) {
  const cache = useQueryClient()
  const contentRef = useRef<HTMLTextAreaElement>(null)
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
  const busyRef = useRef(false)
  const [fieldErrors,setFieldErrors]=useState<Record<string,string>>({})
  const [variable,setVariable]=useState('')
  const [channel,setChannel]=useState('')
  const [status,setStatus]=useState('')
  const [notice,setNotice]=useState('')
  const [previewChannel,setPreviewChannel]=useState('whatsapp_web')
  const [deleting,setDeleting]=useState<QuickReply|null>(null)
  const list = useQuery({ queryKey: ['crm-templates', search, session?.channel], enabled: open,
    queryFn: async () => (await api.get<QuickReply[]>('/crm-chat/templates/', { params: { search, channel: session?.channel } })).data })
  const items = (list.data || []).filter(t => (!channel||t.channels.includes(channel))&&(!status||String(t.active)===status)&&(!category || JSON.stringify(t.category) === category) && (view !== 'favorites' || t.favorite) && (view !== 'recent' || t.last_used_at))
    .sort((a, b) => view === 'recent' ? (b.last_used_at || '').localeCompare(a.last_used_at || '') : a.name.localeCompare(b.name))
  const run = async (fn: () => Promise<void>) => {
    if(busyRef.current)return
    busyRef.current=true;setBusy(true);setError('');setNotice('');setFieldErrors({})
    try { await fn();setNotice('Operación completada.') } catch (e: any) {
      const data=e.response?.data
      const fields:Record<string,string>={}
      if(data&&typeof data==='object')for(const key of ['name','category','text','channels','file'])if(data[key])fields[key]=Array.isArray(data[key])?data[key].join(' '):String(data[key])
      setFieldErrors(fields)
      setError(typeof data?.error==='string'?data.error:Object.keys(fields).length?'Revisa los campos indicados. Tu contenido se conserva.':'No fue posible completar la operación. Inténtalo nuevamente.')
    }
    finally { busyRef.current=false;setBusy(false) }
  }
  const insertVariable=(key:string)=>{
    if(!draft||!key)return
    const input=contentRef.current,start=input?.selectionStart??draft.text.length,end=input?.selectionEnd??start
    const token=`{{${key}}}`
    setDraft({...draft,text:draft.text.slice(0,start)+token+draft.text.slice(end)});setVariable('')
    requestAnimationFrame(()=>{input?.focus();input?.setSelectionRange(start+token.length,start+token.length)})
  }
  const tooLong=!!draft&&(draft.text.length>4000||draft.channels.some(c=>channelText(example(draft.text),c).length>(channelTextLimits[c]||4000)))
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
    setPreviewChannel(session?.channel || (template.channels.includes(channel) ? channel : template.channels[0]) || 'whatsapp_web')
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
  return <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth={draft ? 'lg' : 'md'}>
    <DialogTitle>Plantillas internas del CRM</DialogTitle>
    <DialogContent>
      <Alert severity="info" sx={{ mb: 2 }}>Respuestas reutilizables. Insertar prepara un borrador editable; no envía mensajes ni utiliza plantillas de pago de Meta.</Alert>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {notice&&<Alert severity="success" sx={{mb:1}}>{notice}</Alert>}
      {list.isError&&<Alert severity="error">No fue posible cargar las plantillas. <Button onClick={()=>list.refetch()}>Reintentar</Button></Alert>}
      {list.isLoading&&<Typography role="status">Cargando plantillas…</Typography>}
      {draft ? <Box sx={{display:'grid',gridTemplateColumns:{xs:'minmax(0,1fr)',md:'minmax(0,1fr) minmax(0,.9fr)'},gap:3,alignItems:'start'}}><Stack spacing={2} sx={{minWidth:0}}>
        <Typography variant="h6">{draft.id?'Editar plantilla':'Nueva plantilla'}</Typography>
        <TextField required label="Nombre" value={draft.name} slotProps={{htmlInput:{maxLength:120}}} error={!!fieldErrors.name||!draft.name.trim()} helperText={fieldErrors.name||(!draft.name.trim()?'Escribe un nombre para la plantilla.':'')} onChange={e => {setFieldErrors({...fieldErrors,name:''});setDraft({ ...draft, name: e.target.value })}} />
        <TextField label="Categoría" error={!!fieldErrors.category} helperText={fieldErrors.category} value={draft.category} onChange={e => setDraft({ ...draft, category: e.target.value })} />
        <TextField select error={!!fieldErrors.channels||!draft.channels.length} helperText={fieldErrors.channels||(!draft.channels.length?'Selecciona al menos un canal.':'')} slotProps={{ select: { multiple: true } }} label="Canales" value={draft.channels} onChange={e => setDraft({ ...draft, channels: typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value })}>{channels.map(c => <MenuItem key={c} value={c}>{channelLabels[c]}</MenuItem>)}</TextField>
        <MessageFormatToolbar input={contentRef} value={draft.text} onChange={text=>setDraft({...draft,text})}/>
        <TextField inputRef={contentRef} label="Contenido" multiline minRows={6} slotProps={{htmlInput:{maxLength:4000}}} error={!!fieldErrors.text||invalidText(draft.text)||tooLong} helperText={fieldErrors.text||(invalidText(draft.text)?'Hay variables desconocidas o incompletas. Usa el selector.':tooLong?'El contenido de ejemplo supera el límite de uno de los canales. Reduce el texto o cambia los canales.':`${draft.text.length}/4000 caracteres`)} value={draft.text} onChange={e => {setFieldErrors({...fieldErrors,text:''});setDraft({ ...draft, text: e.target.value })}} />
        <TextField select label="Insertar variable" value={variable} onChange={e=>insertVariable(e.target.value)} helperText="Se insertará en la posición del cursor; la vista previa usa datos de ejemplo.">{variables.map(v=><MenuItem key={v} value={v}>{v.replace(/_/g,' ')}</MenuItem>)}</TextField>
        <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>{variables.map(v => <Chip key={v} label={`{{${v}}}`} onMouseDown={e=>e.preventDefault()} onClick={() => insertVariable(v)} />)}</Stack>
        <Button component="label">Adjunto opcional<input hidden type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.docx,.xlsx,.mp3,.ogg,.wav,.m4a,.mp4,.webm" onChange={e => setFile(e.target.files?.[0])} /></Button>
        {file && <Chip label={file.name} onDelete={() => setFile(undefined)} />}
        {fieldErrors.file&&<Alert severity="error">{fieldErrors.file}</Alert>}
        <TextField select label="Estado de la plantilla" value={String(draft.active)} onChange={e=>setDraft({...draft,active:e.target.value==='true'})}><MenuItem value="true">Activa</MenuItem><MenuItem value="false">Inactiva</MenuItem></TextField>
        <Stack direction="row" spacing={1}><Button disabled={busy} onClick={() => setDraft(null)}>Cancelar</Button><Button variant="contained" disabled={busy || !draft.name.trim() || !draft.text.trim() || invalidText(draft.text)||tooLong||!draft.channels.length} onClick={save}>{busy?'Guardando…':'Guardar plantilla'}</Button></Stack>
      </Stack><Box sx={{minWidth:0,position:{md:'sticky'},top:0}}><TemplateMessagePreview text={example(draft.text)} channels={draft.channels} channel={previewChannel} onChannelChange={setPreviewChannel} file={file} attachment={draft.attachment_url ? {url:draft.attachment_url,...draft.attachment_metadata} : undefined} example />{invalidText(draft.text)&&<Alert severity="warning" sx={{mt:1}}>Completa las variables marcadas en el contenido antes de guardar.</Alert>}</Box></Box> : <>
        <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ gap: 1, mb: 2,flexWrap:'wrap' }}>
          {!session&&<TextField select size="small" label="Canal" sx={{minWidth:140}} value={channel} onChange={e=>setChannel(e.target.value)}><MenuItem value="">Todos</MenuItem>{channels.map(c=><MenuItem key={c} value={c}>{channelLabels[c]}</MenuItem>)}</TextField>}
          <TextField select size="small" label="Estado" sx={{minWidth:130}} value={status} onChange={e=>setStatus(e.target.value)}><MenuItem value="">Todos</MenuItem><MenuItem value="true">Activas</MenuItem><MenuItem value="false">Inactivas</MenuItem></TextField>
          <TextField size="small" label="Buscar por nombre o texto" value={search} onChange={e => setSearch(e.target.value)} />
          <TextField select size="small" label="Categoría" value={category} onChange={e => setCategory(e.target.value)} sx={{ minWidth: 140 }}><MenuItem value="">Todas</MenuItem>{[...new Set((list.data || []).map(t => t.category))].map(c => <MenuItem key={c} value={JSON.stringify(c)}>{c || 'Sin categoría'}</MenuItem>)}</TextField>
          <TextField select size="small" value={view} onChange={e => setView(e.target.value)}><MenuItem value="all">Todas</MenuItem><MenuItem value="favorites">Favoritas</MenuItem><MenuItem value="recent">Recientes</MenuItem></TextField>
          {canManage && <Button variant="contained" onClick={() => { setPreviewChannel('whatsapp_web');setDraft({ ...empty, text: initialText }); setFile(undefined) }}>Crear plantilla</Button>}
        </Stack>
        <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>{items.map(t => <Box key={t.id} sx={{ p: 1, borderBottom: '1px solid #ddd' }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}><Button onClick={() => select(t)}>{t.name}</Button><Chip size="small" label={t.category || 'Sin categoría'} />{!t.active && <Chip label="Inactiva" size="small" />}<Button onClick={() => run(async () => { await api.post(`/crm-chat/templates/${t.id}/favorite/`); refresh() })}>{t.favorite ? '★' : '☆'}</Button>{canManage && <><Button onClick={() => { setDraft(t); setFile(undefined) }}>Editar</Button><Button onClick={() => run(async () => { await api.patch(`/crm-chat/templates/${t.id}/`, { active: !t.active }); refresh() })}>{t.active ? 'Desactivar' : 'Activar'}</Button></>}</Stack>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{t.text}</Typography>
          <Stack direction="row" sx={{my:1,gap:1,flexWrap:"wrap"}}>{t.channels.map(c=><Chip key={c} size="small" label={channelLabels[c]||c}/>)}<Chip size="small" color={t.active?'success':'default'} label={t.active?'Activa':'Inactiva'}/></Stack>
          {canManage&&<Stack direction="row" spacing={1}><Button disabled={busy} onClick={()=>run(async()=>{const response=await api.post<QuickReply>(`/crm-chat/templates/${t.id}/duplicate/`);await refresh();setDraft(response.data);setFile(undefined)})}>Duplicar</Button><Button color="error" disabled={busy} onClick={()=>setDeleting(t)}>Eliminar</Button></Stack>}
          <Typography variant="caption">{t.author_name} · {new Date(t.updated_at).toLocaleString('es-CO')} · {t.channels.join(', ')}</Typography>
          {t.attachment_url && <Typography variant="caption" sx={{ display: 'block' }}>Adjunto: {t.attachment_metadata.name}</Typography>}
        </Box>)}</Box>
        {!list.isLoading && !items.length && <Typography>No hay plantillas para estos filtros.</Typography>}
        {selected&&!session&&<Box sx={{mt:2}}><Typography sx={{mb:1,fontWeight:700}}>Vista previa: {selected.name}</Typography><TemplateMessagePreview text={example(selected.text)} channels={selected.channels} channel={previewChannel} onChannelChange={setPreviewChannel} attachment={selected.attachment_url?{url:selected.attachment_url,...selected.attachment_metadata}:undefined} example /></Box>}
        {selected && session && <Stack spacing={1} sx={{ mt: 2 }}>
          <Typography sx={{ fontWeight: 700 }}>Completar: {selected.name}</Typography>
          {selected.variables.map(v => <TextField key={v} size="small" label={v} value={values[v] || ''} onChange={e => { setValues({ ...values, [v]: e.target.value }); setPreview('') }} />)}
          <TemplateMessagePreview text={preview || selected.text.replace(/{{\s*([a-z_]+)\s*}}/g,(token,key)=>values[key]?.trim() || token)} channels={[session.channel]} channel={session.channel} attachment={selected.attachment_url?{url:selected.attachment_url,...selected.attachment_metadata}:undefined} />
          <Button disabled={busy} onClick={insert}>{preview ? 'Insertar y revisar en el chat' : 'Vista previa final'}</Button>
        </Stack>}
      </>}
      <Button disabled={busy} sx={{ mt: 2 }} onClick={onClose}>Cerrar</Button>
      <Dialog open={!!deleting} onClose={busy?undefined:()=>setDeleting(null)} aria-labelledby="delete-template-title"><DialogTitle id="delete-template-title">Eliminar plantilla</DialogTitle><DialogContent><Typography>¿Eliminar «{deleting?.name}»? Los mensajes enviados se conservarán.</Typography><Stack direction="row" sx={{mt:2,gap:1}}><Button disabled={busy} onClick={()=>setDeleting(null)}>Cancelar</Button><Button color="error" variant="contained" disabled={busy} onClick={()=>run(async()=>{await api.delete(`/crm-chat/templates/${deleting!.id}/`);setDeleting(null);setSelected(null);await refresh()})}>Eliminar plantilla</Button></Stack></DialogContent></Dialog>
    </DialogContent>
  </Dialog>
}
