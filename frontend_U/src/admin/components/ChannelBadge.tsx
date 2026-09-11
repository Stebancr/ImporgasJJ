/** Identificador visual de canal, encapsulado para no repetir colores o etiquetas. */
import { Chip } from '@mui/material'
import { Facebook, Instagram, MessageCircle, ShoppingBag } from 'lucide-react'
import type { Channel } from '../services/admin_chat'

const channelConfig = {
  ecommerce: { label: 'Ecommerce', color: '#c2410c', Icon: ShoppingBag },
  whatsapp: { label: 'WhatsApp', color: '#16a34a', Icon: MessageCircle },
  facebook: { label: 'Facebook', color: '#2563eb', Icon: Facebook },
  instagram: { label: 'Instagram', color: '#a21caf', Icon: Instagram },
} satisfies Record<Channel, { label: string; color: string; Icon: typeof MessageCircle }>

export function ChannelBadge({ channel, compact = false }: { channel: Channel; compact?: boolean }) {
  const config = channelConfig[channel] ?? channelConfig.ecommerce
  return (
    <Chip
      size="small"
      label={compact ? undefined : config.label}
      icon={<config.Icon size={14} color={config.color} />}
      title={config.label}
      sx={{
        color: config.color,
        borderColor: `${config.color}55`,
        backgroundColor: `${config.color}12`,
        fontWeight: 600,
        '& .MuiChip-icon': { marginLeft: compact ? '7px' : undefined },
      }}
      variant="outlined"
    />
  )
}
