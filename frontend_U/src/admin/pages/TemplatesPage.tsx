import { useState } from 'react'
import { Button, Typography, Stack } from '@mui/material'
import TemplateDialog from '../components/TemplateDialog'
export default function TemplatesPage() {
  const [open, setOpen] = useState(true)
  return <Stack spacing={2}><Typography variant="h5">Plantillas de mensajes</Typography><Button onClick={() => setOpen(true)}>Administrar plantillas internas</Button><TemplateDialog open={open} onClose={() => setOpen(false)} /></Stack>
}
