/**
 * Tema visual aislado para las pantallas MUI del CRM.
 *
 * Mantiene la identidad naranja original del panel administrativo y evita que
 * el tema predeterminado azul de MUI o los estilos globales del ecommerce
 * cambien los colores de estas páginas.
 */
import { createTheme } from '@mui/material/styles'

export const crmTheme = createTheme({
  palette: {
    primary: { main: '#b45309' },
    secondary: { main: '#475569' },
    background: { default: '#f8fafc', paper: '#ffffff' },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: 'Inter, system-ui, sans-serif' },
})
