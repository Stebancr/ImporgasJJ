import { useEffect, useState } from 'react'
import { Alert, Avatar, Box, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { ArrowLeft, FileText, ImageIcon, Instagram, MessageCircle, MoreVertical, Phone, Video } from 'lucide-react'
import MessageText from '../../components/chat/MessageText'
import { channelText, channelTextLimits } from '../../components/chat/messageFormat'
import { adminChatService } from '../services/admin_chat'

const labels: Record<string, string> = {
  whatsapp_web: 'WhatsApp Web', whatsapp: 'WhatsApp', facebook: 'Facebook Messenger',
  instagram: 'Instagram', ecommerce: 'Chat de la tienda',
}
type Attachment = { url: string; name?: string; mime_type?: string }

export default function TemplateMessagePreview({ text, channels, channel, onChannelChange, file, attachment, example = false }: {
  text: string; channels: string[]; channel: string; onChannelChange?: (value: string) => void
  file?: File; attachment?: Attachment; example?: boolean
}) {
  const available = channels.length ? channels : ['whatsapp_web', 'facebook', 'instagram']
  const active = available.includes(channel) ? channel : available[0]
  const whatsapp = active === 'whatsapp_web' || active === 'whatsapp'
  const instagram = active === 'instagram'
  const [media, setMedia] = useState<{ url: string; type: string } | null>(null)
  const [mediaState, setMediaState] = useState('')
  const attachmentUrl = attachment?.url || ''
  useEffect(() => {
    let disposed = false, objectUrl = ''
    setMedia(null); setMediaState('')
    if (!file && !attachmentUrl) return
    setMediaState('Cargando vista previa del adjunto…')
    const load = async () => {
      try {
        const blob = file || await adminChatService.getAttachmentBlob(attachmentUrl)
        if (disposed) return
        objectUrl = URL.createObjectURL(blob)
        setMedia({ url: objectUrl, type: blob.type || attachment?.mime_type || '' }); setMediaState('')
      } catch {
        if (!disposed) setMediaState('No se pudo mostrar el adjunto. El archivo sigue asociado a la plantilla.')
      }
    }
    void load()
    return () => { disposed = true; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [file, attachmentUrl, attachment?.mime_type])
  const name = file?.name || attachment?.name || 'Archivo adjunto'
  const type = file?.type || attachment?.mime_type || media?.type || ''
  const image = type.startsWith('image/') && type !== 'image/svg+xml'
  const hasAttachment = !!(file || attachmentUrl)
  const incompatible = hasAttachment && (active === 'whatsapp' || (instagram && !!type && !image))
  const separate = hasAttachment && !!text.trim() && !incompatible && (active === 'facebook' || instagram || type.startsWith('audio/'))
  const bubble = { maxWidth: '92%', minWidth: 0, borderRadius: whatsapp ? '0 10px 10px 10px' : '18px 18px 18px 4px', bgcolor: whatsapp ? '#fff' : '#f0f0f0', p: 1.5, boxShadow: whatsapp ? '0 1px 1px #0002' : 'none' }
  const body = <Box data-testid="template-message-body" sx={{ fontSize: 14, lineHeight: 1.55, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', '& code': { fontSize: '0.94em' } }}>{text ? <MessageText text={text} channel={active} /> : <Typography sx={{ fontSize:13,color: '#667781' }}>Escribe el contenido para verlo aquí.</Typography>}</Box>
  return <Box component="section" aria-label="Vista previa del mensaje para el cliente" sx={{ minWidth: 0, border: '1px solid', borderColor: 'divider', borderRadius: 3, overflow: 'hidden', bgcolor: '#f8fafc', color: '#17212b' }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ p: 2, gap: 1.5, justifyContent: 'space-between', alignItems: { sm: 'center' } }}>
      <Box><Typography sx={{fontWeight:700}}>Así lo verá el cliente</Typography><Typography variant="caption" color="text.secondary">{example ? 'Variables completadas con datos de ejemplo' : 'Contenido preparado para esta conversación'}</Typography></Box>
      {onChannelChange ? <TextField select size="small" label="Canal de la vista previa" value={active} onChange={e => onChannelChange(e.target.value)} sx={{ minWidth: 180 }}>{available.map(c => <MenuItem key={c} value={c}>{labels[c] || c}</MenuItem>)}</TextField>
        : <Chip size="small" label={labels[active] || active} />}
    </Stack>
    {['facebook','instagram'].includes(active) && /\*|_|~/.test(text) && <Alert severity="info" sx={{mx:2,mb:2}}>Este canal se enviará como texto plano, sin negrilla ni cursiva.</Alert>}
    <Typography variant="caption" sx={{px:2,pb:1}}>{channelText(text, active).length}/{channelTextLimits[active] || 4000} caracteres</Typography>
    {incompatible && <Alert severity="warning" sx={{mx:2,mb:2}}>{instagram ? 'Instagram solo tiene habilitadas imágenes en esta integración. Cambia el adjunto o el canal antes de enviar.' : 'Esta integración de WhatsApp no tiene habilitado el envío de adjuntos.'}</Alert>}
    {separate && <Alert severity="info" sx={{mx:2,mb:2}}>Este canal requiere enviar el texto y este archivo por separado. La vista los muestra en dos mensajes; separa el borrador antes de enviarlo.</Alert>}
    <Box sx={{ px: { xs: 1, sm: 3 }, pb: 2 }}>
      <Box data-preview-channel={active} sx={{ width: '100%', maxWidth: 390, mx: 'auto', borderRadius: 3, overflow: 'hidden', border: '1px solid #dce1e7', boxShadow: '0 8px 24px #17212b0d', bgcolor: '#fff' }}>
        <Stack direction="row" sx={{ alignItems: 'center', gap: 1, px: 1.5, py: 1.75, bgcolor: whatsapp ? '#075e54' : '#fff', color: whatsapp ? '#fff' : '#17212b', borderBottom: '1px solid #e8e8e8' }}>
          <ArrowLeft size={19} aria-hidden="true" />
          <Avatar sx={{ width: 34, height: 34, fontSize: 12, fontWeight: 800, bgcolor: instagram ? '#b52aad' : whatsapp ? '#d9fdd3' : '#e7f1ff', color: whatsapp ? '#075e54' : instagram ? '#fff' : '#0866ff' }}>JJ</Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}><Typography sx={{fontSize:14,fontWeight:700}}>ImporGas JJ</Typography><Typography sx={{ fontSize:10,opacity: .8 }}>{labels[active] || active}</Typography></Box>
          <Phone size={17} aria-hidden="true" /><Video size={19} aria-hidden="true" /><MoreVertical size={18} aria-hidden="true" />
        </Stack>
        <Box sx={{ minHeight: 210, p: 2, bgcolor: whatsapp ? '#efeae2' : '#fff', backgroundImage: whatsapp ? 'radial-gradient(#d7d1c9 1px, transparent 1px)' : 'none', backgroundSize: '18px 18px' }}>
          <Typography sx={{ textAlign: 'center', fontSize: 10, color: '#667781', mb: 2 }}>VISTA DEL CLIENTE</Typography>
          <Box sx={bubble}>
            {(file || attachmentUrl) && <Box sx={{ mb: text ? 1 : 0 }}>
              {media && image ? <Box component="img" src={media.url} alt={`Adjunto: ${name}`} onError={() => { setMedia(null); setMediaState('Imagen no disponible en la vista previa.') }} sx={{ display: 'block', maxWidth: '100%', maxHeight: 220, borderRadius: 1.5, objectFit: 'contain' }} />
                : media && type.startsWith('video/') ? <Box component="video" src={media.url} controls preload="metadata" aria-label={name} sx={{ display: 'block', width: '100%', maxHeight: 220, borderRadius: 1.5 }} />
                : media && type.startsWith('audio/') ? <Box component="audio" src={media.url} controls preload="metadata" aria-label={name} sx={{ width: '100%', maxWidth: '100%' }} />
                : <Stack direction="row" sx={{ gap: 1, alignItems: 'center', p: 1.25, borderRadius: 1.5, bgcolor: '#00000006' }}>{image ? <ImageIcon size={23} /> : <FileText size={23} />}<Typography sx={{ fontSize:12,overflowWrap: 'anywhere', minWidth: 0 }}>{name}</Typography></Stack>}
              {mediaState && <Typography role="status" sx={{ fontSize:11,mt: .5, color: '#52606d' }}>{mediaState}</Typography>}
            </Box>}
{incompatible && <Chip size="small" label="Adjunto no compatible" sx={{mb:1}} />}
            {!separate && body}
            <Typography sx={{ mt: .75, fontSize: 10, textAlign: 'right', color: '#667781' }}>Ahora</Typography>
          </Box>
          {separate && <Box sx={{...bubble,mt:1}}>{body}<Typography sx={{mt:.75,fontSize:10,textAlign:'right',color:'#667781'}}>Ahora</Typography></Box>}
        </Box>
        <Stack direction="row" sx={{ p: 1.5, gap: 1, alignItems: 'center', borderTop: '1px solid #e8e8e8', color: '#83909b' }}>{instagram ? <Instagram size={19} /> : <MessageCircle size={19} />}<Typography sx={{fontSize:12}}>Mensaje…</Typography></Stack>
      </Box>
    </Box>
    <Typography variant="caption" component="p" sx={{ m: 0, px: 2, pb: 2, color: '#637282' }}>Vista orientativa. La apariencia puede variar según el dispositivo. No se envía ningún mensaje.</Typography>
  </Box>
}
