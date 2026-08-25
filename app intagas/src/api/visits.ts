import client from './client'
import type {
  AuthUser, AuthTokens,
  VisitaItem, VisitaDetalle,
  CalendarioData, ReporteFormData,
  EvidenciaFoto,
} from '../types'
import * as SecureStore from 'expo-secure-store'
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from './client'

// ─── Auth ─────────────────────────────────────────────────────────────────────

interface LoginResponse {
  access: string
  refresh: string
  is_admin: number
  location_id: number | null
  location_name: string | null
}

interface PerfilResponse {
  id: number
  cedula: string
  nombre_completo: string
  correo: string | null
  telefono: string | null
  sede: string | null
  estado: number
}

export const authApi = {
  login: async (usuario: string, password: string): Promise<{ user: AuthUser; tokens: AuthTokens }> => {
    const { data: tokens } = await client.post<LoginResponse>('/auth/token/', { usuario, password })
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.access)
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refresh)

    const { data: perfil } = await client.get<PerfilResponse>('/user/perfil')

    const user: AuthUser = {
      id: perfil.id,
      usuario,
      nombre_completo: perfil.nombre_completo,
      correo: perfil.correo,
      telefono: perfil.telefono,
      tipo_usuario: tokens.is_admin,
      location_id: tokens.location_id,
      location_name: tokens.location_name,
    }
    return { user, tokens: { access: tokens.access, refresh: tokens.refresh } }
  },

  logout: async () => {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY)
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY)
  },

  getStoredTokens: async (): Promise<AuthTokens | null> => {
    const access = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY)
    const refresh = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY)
    if (!access || !refresh) return null
    return { access, refresh }
  },

  refreshProfile: async (): Promise<PerfilResponse> => {
    const { data } = await client.get<PerfilResponse>('/user/perfil')
    return data
  },
}

// ─── Visits ───────────────────────────────────────────────────────────────────

export const visitsApi = {
  getAll: async (params?: Record<string, string>): Promise<VisitaItem[]> => {
    const { data } = await client.get<VisitaItem[]>('/visits/', { params })
    return data
  },

  getById: async (id: number): Promise<VisitaDetalle> => {
    const { data } = await client.get<VisitaDetalle>(`/visits/${id}/`)
    return data
  },

  getCalendario: async (mes: string): Promise<CalendarioData> => {
    const { data } = await client.get<CalendarioData>('/visits/calendario/', { params: { mes } })
    return data
  },

  iniciar: async (id: number): Promise<VisitaDetalle> => {
    const { data } = await client.post<VisitaDetalle>(`/visits/${id}/iniciar/`)
    return data
  },

  finalizar: async (id: number, reporte: ReporteFormData, firmaBase64?: string): Promise<VisitaDetalle> => {
    const body: Record<string, string> = {
      persona_atiende: reporte.persona_atiende,
      equipo: reporte.equipo,
      equipo_otro: reporte.equipo_otro ?? '',
      ubicacion_equipo: reporte.ubicacion_equipo,
      ubicacion_otro: reporte.ubicacion_otro ?? '',
      motivo_servicio: reporte.motivo_servicio,
      solucion_realizada: reporte.solucion_realizada,
      observaciones: reporte.observaciones ?? '',
      recomendaciones: reporte.recomendaciones ?? '',
      valor_servicio: reporte.valor_servicio ?? '',
      metodo_pago: reporte.metodo_pago ?? '',
    }
    if (firmaBase64) {
      body.firma_base64 = firmaBase64
    }
    const { data } = await client.post<VisitaDetalle>(`/visits/${id}/finalizar/`, body)
    return data
  },

  uploadPhotos: async (id: number, uris: string[]): Promise<EvidenciaFoto[]> => {
    const formData = new FormData()
    for (const uri of uris) {
      const filename = uri.split('/').pop() ?? 'photo.jpg'
      const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg'
      const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
      formData.append('fotos', {
        uri,
        name: filename,
        type: mimeType,
      } as unknown as Blob)
    }
    const { data } = await client.post<EvidenciaFoto[]>(`/visits/${id}/fotos/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  deletePhoto: async (visitaId: number, fotoId: number): Promise<void> => {
    await client.delete(`/visits/${visitaId}/fotos/${fotoId}/`)
  },
}
