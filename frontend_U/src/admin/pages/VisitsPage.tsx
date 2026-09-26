import { useState, useEffect, useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  CalendarDays, Plus, Search, RefreshCw, Eye, Pencil, Trash2,
  ChevronLeft, ChevronRight, Loader2, FileDown, ClipboardCheck,
  Clock, MapPin, User, Phone,
} from 'lucide-react'
import { visitsService } from '@/admin/services/admin_visits'
import type {
  VisitaItem, VisitaDetalle, CreateVisitaData, Tecnico, CalendarioData, TipoVisita,
} from '@/admin/services/admin_visits'
import { format, startOfMonth, endOfMonth, eachDayOfInterval, getDay, isSameDay, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

// ─── Constants ────────────────────────────────────────────────────────────────

const ESTADO_CONFIG: Record<string, { label: string; color: string }> = {
  pendiente:   { label: 'Pendiente',  color: 'bg-yellow-100 text-yellow-800' },
  en_proceso:  { label: 'En Proceso', color: 'bg-blue-100 text-blue-800' },
  finalizada:  { label: 'Finalizada', color: 'bg-green-100 text-green-800' },
  cancelada:   { label: 'Cancelada',  color: 'bg-red-100 text-red-800' },
}

const DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

const blankForm = (): CreateVisitaData => ({
  cliente_nombre: '',
  cliente_identificacion: '',
  cliente_telefono: '',
  cliente_correo: '',
  cliente_direccion: '',
  cliente_indicaciones_llegada: '',
  tipo_tarea: '',
  fecha: format(new Date(), 'yyyy-MM-dd'),
  hora: '08:00',
  descripcion: '',
  observaciones_iniciales: '',
  valor_visita: null,
  tecnico_id: null,
})

type VisitFormErrors = Record<string, string>

const validateVisitForm = (data: CreateVisitaData, editing: boolean): VisitFormErrors => {
  const errors: VisitFormErrors = {}
  const required = (key: keyof CreateVisitaData, value: unknown) => {
    if (value == null || (typeof value === 'string' && !value.trim())) errors[key] = 'Este campo es obligatorio.'
  }

  if (!editing) {
    required('cliente_nombre', data.cliente_nombre)
    required('cliente_telefono', data.cliente_telefono)
    required('cliente_correo', data.cliente_correo)
    required('cliente_direccion', data.cliente_direccion)

    const document = data.cliente_identificacion?.trim() ?? ''
    if (document && !/^\d+$/.test(document)) errors.cliente_identificacion = 'La cédula solo puede contener números.'
    else if (document && (document.length < 6 || document.length > 15)) errors.cliente_identificacion = 'La cédula debe contener entre 6 y 15 números.'

    const phone = data.cliente_telefono?.trim() ?? ''
    if (phone && !/^\d+$/.test(phone)) errors.cliente_telefono = 'El número de celular solo puede contener números.'
    else if (phone && (phone.length < 7 || phone.length > 15)) errors.cliente_telefono = 'El número de celular debe contener entre 7 y 15 números.'

    const email = data.cliente_correo?.trim() ?? ''
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errors.cliente_correo = 'Ingrese un correo electrónico válido.'
  }

  required('tipo_tarea', data.tipo_tarea)
  required('fecha', data.fecha)
  required('hora', data.hora)
  if (!data.tecnico_id) errors.tecnico_id = 'Debe seleccionar un técnico.'
  if (data.valor_visita != null && !Number.isFinite(data.valor_visita)) errors.valor_visita = 'Valor inválido.'
  else if (data.valor_visita != null && data.valor_visita < 0) errors.valor_visita = 'El valor de la visita no puede ser negativo.'
  if (data.fecha && data.fecha < format(new Date(), 'yyyy-MM-dd')) {
    errors.fecha = 'La fecha de la visita no puede ser anterior al día actual.'
  }
  return errors
}

const apiValidationErrors = (error: unknown): VisitFormErrors => {
  const data = (error as { response?: { data?: unknown } })?.response?.data
  if (!data || typeof data !== 'object') return { form: 'No fue posible guardar la visita.' }
  const errors: VisitFormErrors = {}
  Object.entries(data as Record<string, unknown>).forEach(([key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      errors.form = Object.entries(value as Record<string, unknown>)
        .map(([field, message]) => `${field}: ${Array.isArray(message) ? message.map(String).join(' ') : String(message)}`)
        .join(' · ')
      return
    }
    errors[key === 'detail' || key === 'non_field_errors' ? 'form' : key] = Array.isArray(value)
      ? value.map(String).join(' ')
      : String(value)
  })
  return errors
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function VisitsPage() {
  const [tab, setTab] = useState<'lista' | 'calendario'>('lista')
  const [visits, setVisits] = useState<VisitaItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tecnicos, setTecnicos] = useState<Tecnico[]>([])
  const [tipos, setTipos] = useState<TipoVisita[]>([])
  const [typesOpen, setTypesOpen] = useState(false)
  const [typeCode, setTypeCode] = useState('')
  const [typeName, setTypeName] = useState('')
  const [typeError, setTypeError] = useState('')
  const [exportOpen, setExportOpen] = useState(false)
  const [exportFrom, setExportFrom] = useState(format(startOfMonth(new Date()), 'yyyy-MM-dd'))
  const [exportTo, setExportTo] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [exportTechnician, setExportTechnician] = useState('all')
  const [exportType, setExportType] = useState('all')
  const [exportStatus, setExportStatus] = useState('all')
  const [exportError, setExportError] = useState('')
  const [creationFlow, setCreationFlow] = useState<'complete' | 'pending' | null>(null)
  const completeNow = creationFlow === 'complete'
  const [photos, setPhotos] = useState<File[]>([])
  const [photosInputKey, setPhotosInputKey] = useState(0)
  const [signature, setSignature] = useState<File | null>(null)
  const [report, setReport] = useState({ persona_atiende: '', equipo: 'estufa', equipo_otro: '', ubicacion_equipo: 'cocina', ubicacion_otro: '', motivo_servicio: '', solucion_realizada: '', observaciones: '', recomendaciones: '', metodo_pago: '' })

  // Filters
  const [search, setSearch] = useState('')
  const [searchField, setSearchField] = useState<'all' | 'document' | 'phone'>('all')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const requestSequence = useRef(0)
  const [estadoFilter, setEstadoFilter] = useState('all')
  const [tecnicoFilter, setTecnicoFilter] = useState('all')

  // Modals
  const [createOpen, setCreateOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const [form, setForm] = useState<CreateVisitaData>(blankForm())
  const [selectedVisit, setSelectedVisit] = useState<VisitaDetalle | null>(null)
  const [editVisit, setEditVisit] = useState<VisitaItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState<VisitFormErrors>({})
  const [detailLoading, setDetailLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // Calendar
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [calendarioData, setCalendarioData] = useState<CalendarioData>({})
  const [calendarLoading, setCalendarLoading] = useState(false)
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)

  // Load data
  const loadVisits = useCallback(async () => {
    const sequence = ++requestSequence.current
    setLoading(true)
    const params: Record<string, string> = {}
    if (estadoFilter !== 'all') params.estado = estadoFilter
    if (tecnicoFilter !== 'all') params.tecnico_id = tecnicoFilter
    if (debouncedSearch) params.search = debouncedSearch
    if (searchField !== 'all') params.search_field = searchField
    try {
      const data = await visitsService.getAll(params)
      if (sequence === requestSequence.current) setVisits(Array.isArray(data) ? data : [])
    } catch {
      if (sequence === requestSequence.current) setVisits([])
    } finally {
      if (sequence === requestSequence.current) setLoading(false)
    }
  }, [estadoFilter, tecnicoFilter, debouncedSearch, searchField])

  const loadCalendar = useCallback(async () => {
    setCalendarLoading(true)
    const mes = format(currentMonth, 'yyyy-MM')
    try {
      const data = await visitsService.getCalendario(mes)
      setCalendarioData(data)
    } catch {
      setCalendarioData({})
    } finally {
      setCalendarLoading(false)
    }
  }, [currentMonth])

  useEffect(() => {
    visitsService.getTecnicos()
      .then(setTecnicos)
      .catch(() => setTecnicos([]))
    visitsService.getTipos().then(setTipos).catch(() => setTipos([]))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300)
    return () => window.clearTimeout(timer)
  }, [search])
  useEffect(() => { loadVisits() }, [loadVisits])
  useEffect(() => { if (tab === 'calendario') loadCalendar() }, [tab, loadCalendar])

  // ── Create ──
  const handleCreate = async () => {
    const errors = validateVisitForm(form, false)
    if (!creationFlow) errors.form = 'Selecciona el flujo de creación.'
    if (completeNow) {
      for (const key of ['persona_atiende', 'motivo_servicio', 'solucion_realizada'] as const) {
        if (!report[key].trim()) errors[key] = 'Este campo es obligatorio.'
      }
      if (report.equipo === 'otro' && !report.equipo_otro.trim()) errors.equipo_otro = 'Especifica el equipo.'
      if (report.ubicacion_equipo === 'otro' && !report.ubicacion_otro.trim()) errors.ubicacion_otro = 'Especifica la ubicación.'
    }
    if (Object.keys(errors).length) {
      setFormErrors(errors)
      return
    }
    setSaving(true)
    try {
      await visitsService.create(form, photos, completeNow, report, signature)
      setCreateOpen(false)
      setForm(blankForm())
      setPhotos([])
      setSignature(null)
      setCreationFlow(null)
      setReport({ persona_atiende: '', equipo: 'estufa', equipo_otro: '', ubicacion_equipo: 'cocina', ubicacion_otro: '', motivo_servicio: '', solucion_realizada: '', observaciones: '', recomendaciones: '', metodo_pago: '' })
      setFormErrors({})
      loadVisits()
      if (tab === 'calendario') loadCalendar()
    } catch (error) {
      setFormErrors(apiValidationErrors(error))
    } finally {
      setSaving(false)
    }
  }

  // ── Detail ──
  const openDetail = async (id: number) => {
    setDetailLoading(true)
    setDetailOpen(true)
    try {
      const v = await visitsService.getById(id)
      setSelectedVisit(v)
    } finally {
      setDetailLoading(false)
    }
  }

  // ── Edit ──
  const openEdit = async (visit: VisitaItem) => {
    if (visit.estado === 'finalizada') return
    const full = await visitsService.getById(visit.id)
    setEditVisit(visit)
    setForm({
      cliente_nombre: visit.cliente_nombre,
      cliente_telefono: visit.cliente_telefono || '',
      cliente_correo: '',
      cliente_identificacion: '',
      cliente_direccion: visit.cliente_direccion,
      cliente_indicaciones_llegada: full.cliente.indicaciones_llegada || '',
      tipo_tarea: visit.tipo_tarea,
      fecha: visit.fecha,
      hora: visit.hora,
      descripcion: full.descripcion,
      observaciones_iniciales: full.observaciones_iniciales,
      valor_visita: visit.valor_visita,
      tecnico_id: visit.tecnico_id,
    })
    setFormErrors({})
    setEditOpen(true)
  }

  const handleEdit = async () => {
    if (!editVisit) return
    if (editVisit.estado === 'finalizada') {
      setFormErrors({ form: 'No se puede modificar una visita que ya está finalizada.' })
      return
    }
    const errors = validateVisitForm(form, true)
    if (Object.keys(errors).length) {
      setFormErrors(errors)
      return
    }
    let motivoCosto = ''
    if (form.valor_visita !== editVisit.valor_visita && editVisit.costo_inicial != null && form.valor_visita !== editVisit.costo_inicial) {
      const reason = window.prompt('Motivo del cambio respecto al costo inicial')
      if (reason === null) return
      if (!reason.trim()) { setFormErrors({ valor_visita: 'Indica el motivo del cambio de costo.' }); return }
      motivoCosto = reason.trim()
    }
    setSaving(true)
    try {
      await visitsService.update(editVisit.id, {
        ...(tipos.some((option) => option.codigo === form.tipo_tarea && option.activo) ? { tipo_tarea: form.tipo_tarea } : {}),
        cliente_indicaciones_llegada: form.cliente_indicaciones_llegada,
        fecha: form.fecha,
        hora: form.hora,
        descripcion: form.descripcion,
        observaciones_iniciales: form.observaciones_iniciales,
        valor_visita: form.valor_visita,
        motivo_cambio_costo: motivoCosto,
        tecnico: form.tecnico_id ?? null,
      })
      setEditOpen(false)
      setFormErrors({})
      loadVisits()
      if (tab === 'calendario') loadCalendar()
    } catch (error) {
      setFormErrors(apiValidationErrors(error))
    } finally {
      setSaving(false)
    }
  }

  // ── Delete ──
  const handleDelete = async () => {
    if (!editVisit) return
    setSaving(true)
    try {
      await visitsService.remove(editVisit.id)
      setDeleteOpen(false)
      loadVisits()
      if (tab === 'calendario') loadCalendar()
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  // ── Calendar helpers ──
  const calendarDays = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth),
  })
  const firstDayOffset = getDay(startOfMonth(currentMonth))
  const dayVisits = (day: Date) => {
    const key = format(day, 'yyyy-MM-dd')
    return calendarioData[key] || []
  }

  // ── Form field helper ──
  const setField = (key: keyof CreateVisitaData, value: string | number | null) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFormErrors((previous) => {
      if (!previous[key] && !previous.form) return previous
      const next = { ...previous }
      delete next[key]
      delete next.form
      return next
    })
  }

  const setDigitsOnly = (
    key: 'cliente_identificacion' | 'cliente_telefono',
    value: string,
    message: string,
  ) => {
    if (/^\d*$/.test(value)) {
      setField(key, value)
      return
    }
    setFormErrors((previous) => ({ ...previous, [key]: message }))
  }

  const fieldError = (key: keyof CreateVisitaData) => formErrors[key]
    ? <p className="mt-1 text-xs text-destructive">{formErrors[key]}</p>
    : null

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Visitas Técnicas</h1>
          <p className="text-muted-foreground text-sm">Agenda y gestiona las visitas de los técnicos</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setTypesOpen(true)}>Tipos de visita</Button>
          <Button variant="outline" onClick={() => setExportOpen(true)}>Generar Excel</Button>
          <Button onClick={() => { setForm(blankForm()); setFormErrors({}); setCreationFlow(null); setPhotos([]); setSignature(null); setReport({ persona_atiende: '', equipo: 'estufa', equipo_otro: '', ubicacion_equipo: 'cocina', ubicacion_otro: '', motivo_servicio: '', solucion_realizada: '', observaciones: '', recomendaciones: '', metodo_pago: '' }); setPhotosInputKey((key) => key + 1); setCreateOpen(true) }}>
            <Plus className="h-4 w-4 mr-2" /> Nueva Visita
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b gap-1">
        {(['lista', 'calendario'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {t === 'lista' ? '📋 Lista' : '📅 Calendario'}
          </button>
        ))}
      </div>

      {/* ── LIST TAB ──────────────────────────────────────────────────────── */}
      {tab === 'lista' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            <Select value={searchField} onValueChange={(value: 'all' | 'document' | 'phone') => { setSearchField(value); setSearch('') }}>
              <SelectTrigger className="w-full sm:w-44"><SelectValue placeholder="Buscar por" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los campos</SelectItem>
                <SelectItem value="document">Documento</SelectItem>
                <SelectItem value="phone">Teléfono</SelectItem>
              </SelectContent>
            </Select>
            <div className="relative flex-1 min-w-0 w-full sm:w-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Cliente, documento, teléfono, tarea o dirección..."
                value={search}
                inputMode={searchField === 'all' ? 'search' : 'numeric'}
                maxLength={searchField === 'all' ? undefined : 15}
                onChange={(e) => setSearch(searchField === 'all' ? e.target.value : e.target.value.replace(/\D/g, ''))}
                className="pl-9"
               aria-label="Buscar por cliente, documento, teléfono, tarea o dirección" />
            </div>
            <Select value={estadoFilter} onValueChange={setEstadoFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="pendiente">Pendiente</SelectItem>
                <SelectItem value="en_proceso">En Proceso</SelectItem>
                <SelectItem value="finalizada">Finalizada</SelectItem>
                <SelectItem value="cancelada">Cancelada</SelectItem>
              </SelectContent>
            </Select>
            <Select value={tecnicoFilter} onValueChange={setTecnicoFilter}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Técnico" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los técnicos</SelectItem>
                {tecnicos.map((t) => (
                  <SelectItem key={t.id} value={String(t.id)}>{t.nombre_completo || t.usuario}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon" onClick={loadVisits} aria-label="Actualizar">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Table */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tarea</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Dirección</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Fecha / Hora</TableHead>
                    <TableHead>Valor</TableHead>
                    <TableHead>Técnico</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Reporte</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={10} className="text-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : visits.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                        No hay visitas que mostrar
                      </TableCell>
                    </TableRow>
                  ) : (
                    visits.map((v) => (
                      <TableRow key={v.id}>
                        <TableCell className="font-mono text-xs">#{v.numero_tarea}</TableCell>
                        <TableCell className="font-medium">{v.cliente_nombre}</TableCell>
                        <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">
                          <MapPin className="inline h-3 w-3 mr-1" />{v.cliente_direccion}
                        </TableCell>
                        <TableCell className="text-xs">{v.tipo_tarea_display}</TableCell>
                        <TableCell className="text-xs whitespace-nowrap">
                          <CalendarDays className="inline h-3 w-3 mr-1" />
                          {v.fecha}<br />
                          <Clock className="inline h-3 w-3 mr-1" />{v.hora?.slice(0, 5)}
                        </TableCell>
                        <TableCell className="text-xs whitespace-nowrap">
                          {v.costo_final == null ? '—' : `$${v.costo_final.toLocaleString('es-CO')}`}
                        </TableCell>
                        <TableCell className="text-xs">
                          {v.tecnico_nombre ?? <span className="text-muted-foreground italic">Sin asignar</span>}
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${ESTADO_CONFIG[v.estado]?.color}`}>
                            {v.estado_display}
                          </span>
                        </TableCell>
                        <TableCell>
                          {v.tiene_reporte ? (
                            <ClipboardCheck className="h-4 w-4 text-green-600" />
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                          {v.evidencias_count > 0 && (
                            <span className="ml-1 text-xs text-muted-foreground">{v.evidencias_count}📷</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openDetail(v.id)} aria-label="Ver detalle">
                              <Eye className="h-3 w-3" />
                            </Button>
                            {v.estado !== 'finalizada' && (
                              <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(v)} aria-label="Editar visita">
                                <Pencil className="h-3 w-3" />
                              </Button>
                            )}
                            {v.tiene_reporte && (
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-7 w-7"
                                disabled={downloading}
                                onClick={async () => {
                                  setDownloading(true)
                                  try {
                                    await visitsService.downloadPDF(v.id)
                                  } catch (err) {
                                    console.error('Error descargando PDF:', err)
                                  } finally {
                                    setDownloading(false)
                                  }
                                }}
                              >
                                <FileDown className="h-3 w-3 text-blue-600" />
                              </Button>
                            )}
                            <Button
                              size="icon" variant="ghost" className="h-7 w-7"
                              onClick={() => { setEditVisit(v); setDeleteOpen(true) }}
                             aria-label="Eliminar">
                              <Trash2 className="h-3 w-3 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── CALENDAR TAB ─────────────────────────────────────────────────── */}
      {tab === 'calendario' && (
        <div className="space-y-4">
          {/* Month nav */}
          <div className="flex items-center justify-between">
            <Button variant="outline" size="icon" onClick={() => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))} aria-label="Anterior">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="font-semibold text-lg capitalize">
              {format(currentMonth, 'MMMM yyyy', { locale: es })}
            </h2>
            <Button variant="outline" size="icon" onClick={() => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))} aria-label="Siguiente">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {calendarLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-1 min-w-0">
              {/* Day headers */}
              {DIAS_SEMANA.map((d) => (
                <div key={d} className="text-center text-xs font-semibold text-muted-foreground py-2">
                  {d}
                </div>
              ))}

              {/* Empty cells before first day */}
              {Array.from({ length: firstDayOffset }).map((_, i) => (
                <div key={`empty-${i}`} />
              ))}

              {/* Days */}
              {calendarDays.map((day) => {
                const visits = dayVisits(day)
                const isSelected = selectedDay && isSameDay(day, selectedDay)
                const isToday = isSameDay(day, new Date())
                return (
                  <div
                    key={day.toISOString()}
                    role="button" tabIndex={0} aria-pressed={Boolean(isSelected)} aria-label={format(day, 'dd MMMM yyyy', { locale: es })}
                    onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedDay(isSelected ? null : day) } }}
                    onClick={() => setSelectedDay(isSelected ? null : day)}
                    className={`min-w-0 min-h-[80px] p-1 rounded border cursor-pointer transition-colors ${
                      isSelected ? 'bg-primary/10 border-primary' :
                      isToday ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/30' :
                      'border-border hover:bg-muted/50'
                    }`}
                  >
                    <div className={`text-xs font-semibold mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                      isToday ? 'bg-blue-500 text-white' : ''
                    }`}>
                      {format(day, 'd')}
                    </div>
                    <div className="space-y-0.5">
                      {visits.slice(0, 3).map((v) => (
                        <div
                          key={v.id}
                          className={`text-[10px] px-1 py-0.5 rounded truncate ${
                            v.estado === 'finalizada' ? 'bg-green-100 text-green-800' :
                            v.estado === 'en_proceso' ? 'bg-blue-100 text-blue-800' :
                            v.estado === 'cancelada' ? 'bg-red-100 text-red-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {v.hora.slice(0, 5)} {v.cliente_nombre}
                        </div>
                      ))}
                      {visits.length > 3 && (
                        <div className="text-[10px] text-muted-foreground pl-1">+{visits.length - 3} más</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Selected day detail */}
          {selectedDay && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">
                  Visitas del {format(selectedDay, "d 'de' MMMM yyyy", { locale: es })}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {dayVisits(selectedDay).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No hay visitas este día.</p>
                ) : (
                  dayVisits(selectedDay).map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between p-3 rounded border hover:bg-muted/50 cursor-pointer"
                      onClick={() => openDetail(v.id)}
                    >
                      <div className="space-y-0.5">
                        <p className="font-medium text-sm">{v.cliente_nombre}</p>
                        <p className="text-xs text-muted-foreground">
                          <Clock className="inline h-3 w-3 mr-1" />{v.hora.slice(0, 5)}
                          {' · '}{v.tipo_tarea}
                          {v.tecnico_nombre && <><User className="inline h-3 w-3 ml-2 mr-1" />{v.tecnico_nombre}</>}
                        </p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${ESTADO_CONFIG[v.estado]?.color}`}>
                        {ESTADO_CONFIG[v.estado]?.label}
                      </span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── CREATE / EDIT FORM MODAL ──────────────────────────────────────── */}
      <Dialog open={createOpen || editOpen} onOpenChange={(o) => { if (!o) { setCreateOpen(false); setEditOpen(false); setFormErrors({}) } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editOpen ? 'Editar Visita' : 'Nueva Visita Técnica'}</DialogTitle>
          </DialogHeader>
          {formErrors.form && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {formErrors.form}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-2">

            {/* ── Client section (create only) ── */}
            {!editOpen && (
              <>
                <div className="col-span-2">
                  <p className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Datos del Cliente</p>
                </div>
                <div>
                  <Label>Nombre completo *</Label>
                  <Input value={form.cliente_nombre} onChange={(e) => setField('cliente_nombre', e.target.value)} />
                  {fieldError('cliente_nombre')}
                </div>
                <div>
                  <Label>Identificación (opcional)</Label>
                  <Input
                    inputMode="numeric"
                    maxLength={15}
                    value={form.cliente_identificacion || ''}
                    onChange={(e) => setDigitsOnly('cliente_identificacion', e.target.value, 'La cédula solo puede contener números.')}
                  />
                  {fieldError('cliente_identificacion')}
                </div>
                <div>
                  <Label>Teléfono *</Label>
                  <Input
                    inputMode="numeric"
                    maxLength={15}
                    value={form.cliente_telefono || ''}
                    onChange={(e) => setDigitsOnly('cliente_telefono', e.target.value, 'El número de celular solo puede contener números.')}
                  />
                  {fieldError('cliente_telefono')}
                </div>
                <div>
                  <Label>Correo *</Label>
                  <Input type="email" value={form.cliente_correo || ''} onChange={(e) => setField('cliente_correo', e.target.value)} />
                  {fieldError('cliente_correo')}
                </div>
                <div className="col-span-2">
                  <Label>Dirección *</Label>
                  <Textarea rows={2} value={form.cliente_direccion} onChange={(e) => setField('cliente_direccion', e.target.value)} />
                  {fieldError('cliente_direccion')}
                </div>
              </>
            )}
            {editOpen && <div className="col-span-2">
              <Label>Dirección</Label>
              <Textarea rows={2} value={form.cliente_direccion} readOnly />
            </div>}
            <div className="col-span-2">
              <Label>Indicaciones para llegar</Label>
              <Textarea rows={2} value={form.cliente_indicaciones_llegada || ''} onChange={(e) => setField('cliente_indicaciones_llegada', e.target.value)} />
            </div>

            {/* ── Visit section ── */}
            <div className="col-span-2">
              <p className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Datos de la Visita</p>
            </div>
            <div>
              <Label>Tipo de servicio *</Label>
              <Select value={tipos.some((option) => option.codigo === form.tipo_tarea && option.activo) ? form.tipo_tarea : undefined} onValueChange={(v) => setField('tipo_tarea', v)}>
                <SelectTrigger className="min-w-0"><SelectValue placeholder="Selecciona un servicio" /></SelectTrigger>
                <SelectContent className="max-w-[calc(100vw-2rem)]">
                  {tipos.filter((o) => o.activo).map((o) => (
                    <SelectItem key={o.codigo} value={o.codigo}>{o.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {editOpen && form.tipo_tarea && !tipos.some((option) => option.codigo === form.tipo_tarea && option.activo) && <p className="mt-1 text-xs text-muted-foreground">Valor anterior: {editVisit?.tipo_tarea_display}. Se conserva si no eliges uno nuevo.</p>}
              {fieldError('tipo_tarea')}
            </div>
            <div>
              <Label>Técnico asignado *</Label>
              <Select
                value={form.tecnico_id != null ? String(form.tecnico_id) : undefined}
                onValueChange={(v) => setField('tecnico_id', Number(v))}
              >
                <SelectTrigger><SelectValue placeholder="Seleccione un técnico" /></SelectTrigger>
                <SelectContent>
                  {tecnicos.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>{t.nombre_completo || t.usuario}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {fieldError('tecnico_id')}
            </div>
            <div>
              <Label>Fecha *</Label>
              <Input type="date" min={format(new Date(), 'yyyy-MM-dd')} value={form.fecha} onChange={(e) => setField('fecha', e.target.value)} />
              {fieldError('fecha')}
            </div>
            <div>
              <Label>Hora *</Label>
              <Input type="time" value={form.hora} onChange={(e) => setField('hora', e.target.value)} />
              {fieldError('hora')}
            </div>
            <div>
              <Label>{editOpen ? 'Costo final (opcional)' : 'Costo inicial (opcional)'}</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                inputMode="decimal"
                value={form.valor_visita ?? ''}
                onChange={(e) => setField('valor_visita', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="Ej: 150000"
               aria-label="Ej: 150000" />
              {fieldError('valor_visita')}
            </div>
            <div className="col-span-2">
              <Label>Descripción de la tarea</Label>
              <Textarea rows={2} value={form.descripcion || ''} onChange={(e) => setField('descripcion', e.target.value)} />
            </div>
            <div className="col-span-2">
              <Label>Observaciones iniciales</Label>
              <Textarea rows={2} value={form.observaciones_iniciales || ''} onChange={(e) => setField('observaciones_iniciales', e.target.value)} />
            </div>
            {!editOpen && <>
              <div className="col-span-2">
                <Label>Flujo de creación</Label>
                <Select value={creationFlow ?? undefined} onValueChange={(value) => {
                  if (value === 'pending' && (photos.length > 0 || signature)) {
                    if (!window.confirm('Al asignar la visita para completar después se descartarán las imágenes y la firma seleccionadas. ¿Continuar?')) return
                    setPhotos([])
                    setSignature(null)
                    setPhotosInputKey((key) => key + 1)
                  }
                  setCreationFlow(value as 'complete' | 'pending')
                }}>
                  <SelectTrigger><SelectValue placeholder="Selecciona cómo crear la visita" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Dejar pendiente para el técnico</SelectItem>
                    <SelectItem value="complete">Completar ahora</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {completeNow && <>
                <div className="col-span-2">
                  <Label>Imágenes de la visita</Label>
                  <Input key={photosInputKey} type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={(e) => setPhotos(Array.from(e.target.files || []))} />
                  <p className="text-xs text-muted-foreground">{photos.length} imagen(es) seleccionada(s)</p>
                </div>
                <div className="col-span-2"><Label>Persona que atiende *</Label><Input value={report.persona_atiende} onChange={(e) => setReport((prev) => ({ ...prev, persona_atiende: e.target.value }))} />{formErrors.persona_atiende && <p className="text-xs text-destructive">{formErrors.persona_atiende}</p>}</div>
                <div><Label>Equipo *</Label><Select value={report.equipo} onValueChange={(value) => setReport((prev) => ({ ...prev, equipo: value }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{['estufa', 'horno', 'calentador', 'parrilla', 'caldera', 'calefactor', 'otro'].map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
                <div><Label>Ubicación del equipo *</Label><Select value={report.ubicacion_equipo} onValueChange={(value) => setReport((prev) => ({ ...prev, ubicacion_equipo: value }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{['cocina', 'patio', 'balcon', 'exterior', 'sotano', 'otro'].map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
                {report.equipo === 'otro' && <div className="col-span-2"><Label>Especifica el equipo *</Label><Input value={report.equipo_otro} onChange={(e) => setReport((prev) => ({ ...prev, equipo_otro: e.target.value }))} />{formErrors.equipo_otro && <p className="text-xs text-destructive">{formErrors.equipo_otro}</p>}</div>}
                {report.ubicacion_equipo === 'otro' && <div className="col-span-2"><Label>Especifica la ubicación *</Label><Input value={report.ubicacion_otro} onChange={(e) => setReport((prev) => ({ ...prev, ubicacion_otro: e.target.value }))} />{formErrors.ubicacion_otro && <p className="text-xs text-destructive">{formErrors.ubicacion_otro}</p>}</div>}
                <div className="col-span-2"><Label>Motivo del servicio *</Label><Textarea value={report.motivo_servicio} onChange={(e) => setReport((prev) => ({ ...prev, motivo_servicio: e.target.value }))} />{formErrors.motivo_servicio && <p className="text-xs text-destructive">{formErrors.motivo_servicio}</p>}</div>
                <div className="col-span-2"><Label>Solución realizada *</Label><Textarea value={report.solucion_realizada} onChange={(e) => setReport((prev) => ({ ...prev, solucion_realizada: e.target.value }))} />{formErrors.solucion_realizada && <p className="text-xs text-destructive">{formErrors.solucion_realizada}</p>}</div>
                <div className="col-span-2"><Label>Observaciones</Label><Textarea value={report.observaciones} onChange={(e) => setReport((prev) => ({ ...prev, observaciones: e.target.value }))} /></div>
                <div className="col-span-2"><Label>Recomendaciones</Label><Textarea value={report.recomendaciones} onChange={(e) => setReport((prev) => ({ ...prev, recomendaciones: e.target.value }))} /></div>
                <div className="col-span-2"><Label>Método de pago</Label><Select value={report.metodo_pago || 'none'} onValueChange={(value) => setReport((prev) => ({ ...prev, metodo_pago: value === 'none' ? '' : value }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Sin informar</SelectItem>{['efectivo', 'transferencia', 'tarjeta', 'credito', 'otro'].map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
                <div className="col-span-2"><Label>Firma del cliente (opcional)</Label><Input type="file" accept="image/png,image/jpeg" onChange={(e) => setSignature(e.target.files?.[0] || null)} /></div>
              </>}
            </>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setCreateOpen(false); setEditOpen(false) }}>Cancelar</Button>
            <Button onClick={editOpen ? handleEdit : handleCreate} disabled={saving || (!editOpen && !creationFlow)}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editOpen ? 'Guardar cambios' : !creationFlow ? 'Selecciona un flujo' : completeNow ? 'Crear y finalizar visita' : 'Crear visita pendiente'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={exportOpen} onOpenChange={setExportOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Generar Excel de visitas</DialogTitle></DialogHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><Label>Desde</Label><Input type="date" value={exportFrom} onChange={(e) => setExportFrom(e.target.value)} /></div>
            <div><Label>Hasta</Label><Input type="date" value={exportTo} onChange={(e) => setExportTo(e.target.value)} /></div>
            <div><Label>Técnico</Label><Select value={exportTechnician} onValueChange={setExportTechnician}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Todos</SelectItem>{tecnicos.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.nombre_completo}</SelectItem>)}</SelectContent></Select></div>
            <div><Label>Tipo de servicio</Label><Select value={exportType} onValueChange={setExportType}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Todos</SelectItem>{tipos.map((item) => <SelectItem key={item.id} value={item.codigo}>{item.nombre}</SelectItem>)}</SelectContent></Select></div>
            <div><Label>Estado</Label><Select value={exportStatus} onValueChange={setExportStatus}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Todos</SelectItem><SelectItem value="pendiente">Pendiente</SelectItem><SelectItem value="en_proceso">En proceso</SelectItem><SelectItem value="finalizada">Finalizada</SelectItem><SelectItem value="cancelada">Cancelada</SelectItem></SelectContent></Select></div>
          </div>
          {exportError && <p className="text-sm text-destructive">{exportError}</p>}
          <DialogFooter><Button onClick={async () => {
            if (!exportFrom || !exportTo || exportFrom > exportTo) { setExportError('Selecciona un rango de fechas válido.'); return }
            try {
              await visitsService.exportExcel({ fecha_desde: exportFrom, fecha_hasta: exportTo, tecnico_id: exportTechnician, tipo_tarea: exportType, estado: exportStatus })
              setExportOpen(false)
              setExportError('')
            } catch { setExportError('No fue posible generar el Excel.') }
          }}>Descargar Excel</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={typesOpen} onOpenChange={setTypesOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Tipos de visita</DialogTitle></DialogHeader>
          <div className="space-y-2">{tipos.map((item) => <div key={item.id} className="flex items-center gap-2 justify-between border-b py-2"><Input defaultValue={item.nombre} aria-label={`Nombre de ${item.codigo}`} onBlur={async (e) => { const nombre = e.target.value.trim(); if (nombre && nombre !== item.nombre) { try { await visitsService.updateTipo(item.id, { nombre }); setTipos(await visitsService.getTipos()) } catch { setTypeError('No fue posible editar el tipo.') } } }} /><Button variant="outline" onClick={async () => { try { await visitsService.updateTipo(item.id, { activo: !item.activo }); setTipos(await visitsService.getTipos()) } catch { setTypeError('No fue posible cambiar el estado.') } }}>{item.activo ? 'Desactivar' : 'Activar'}</Button></div>)}</div>
          <div className="grid gap-2"><Label>Nuevo tipo</Label><Input placeholder="Código (sin espacios)" value={typeCode} onChange={(e) => setTypeCode(e.target.value)} /><Input placeholder="Nombre" value={typeName} onChange={(e) => setTypeName(e.target.value)} />{typeError && <p className="text-sm text-destructive">{typeError}</p>}<Button onClick={async () => { try { await visitsService.createTipo({ codigo: typeCode.trim(), nombre: typeName.trim() }); setTipos(await visitsService.getTipos()); setTypeCode(''); setTypeName(''); setTypeError('') } catch { setTypeError('Código o nombre inválido o duplicado.') } }}>Crear tipo</Button></div>
        </DialogContent>
      </Dialog>

      {/* ── DETAIL MODAL ─────────────────────────────────────────────────── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalle de Visita {selectedVisit && `#${selectedVisit.numero_tarea}`}</DialogTitle>
          </DialogHeader>
          {detailLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : selectedVisit ? (
            <div className="space-y-4">
              {/* Status */}
              <div className="flex gap-2 flex-wrap">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${ESTADO_CONFIG[selectedVisit.estado]?.color}`}>
                  {selectedVisit.estado_display}
                </span>
                <span className="px-3 py-1 rounded-full text-sm bg-secondary text-secondary-foreground">
                  {selectedVisit.tipo_tarea_display}
                </span>
              </div>

              {/* Client */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Card><CardContent className="pt-3 pb-3 space-y-1">
                  <p className="text-xs text-muted-foreground font-semibold">CLIENTE</p>
                  <p className="font-medium">{selectedVisit.cliente.nombre}</p>
                  {selectedVisit.cliente.identificacion && <p className="text-sm">ID: {selectedVisit.cliente.identificacion}</p>}
                  {selectedVisit.cliente.telefono && <p className="text-sm flex items-center gap-1"><Phone className="h-3 w-3" />{selectedVisit.cliente.telefono}</p>}
                  {selectedVisit.cliente.correo && <p className="text-sm">{selectedVisit.cliente.correo}</p>}
                  <p className="text-sm flex items-start gap-1"><MapPin className="h-3 w-3 mt-0.5 shrink-0" />{selectedVisit.cliente.direccion}</p>
                  {selectedVisit.cliente.indicaciones_llegada && <p className="text-sm">Indicaciones para llegar: {selectedVisit.cliente.indicaciones_llegada}</p>}
                </CardContent></Card>

                <Card><CardContent className="pt-3 pb-3 space-y-1">
                  <p className="text-xs text-muted-foreground font-semibold">VISITA</p>
                  <p className="text-sm"><CalendarDays className="inline h-3 w-3 mr-1" />{selectedVisit.fecha} a las {selectedVisit.hora?.slice(0, 5)}</p>
                  <p className="text-sm">Costo inicial: {selectedVisit.costo_inicial == null ? 'No informado' : `$${selectedVisit.costo_inicial.toLocaleString('es-CO')}`}</p>
                  <p className="text-sm">Costo final: {selectedVisit.costo_final == null ? 'No informado' : `$${selectedVisit.costo_final.toLocaleString('es-CO')}`}</p>
                  <p className="text-sm">Creada por: {selectedVisit.creado_por_nombre || 'No registrado'}</p>
                  {selectedVisit.pdf_generado_en && selectedVisit.pdf_disponible && <p className="text-xs text-muted-foreground">PDF definitivo: {selectedVisit.pdf_nombre} · {new Date(selectedVisit.pdf_generado_en).toLocaleString('es-CO')}</p>}
                  {['error', 'fallido'].includes(selectedVisit.pdf_estado || '') && <p className="text-sm text-destructive">PDF fallido: {selectedVisit.pdf_error || 'No se pudo generar.'}</p>}
                  {['pendiente', 'procesando'].includes(selectedVisit.pdf_estado || '') && <p className="text-sm text-muted-foreground">PDF: {selectedVisit.pdf_estado}</p>}
                  {selectedVisit.cambios_costo?.map((change, index) => <p key={index} className="text-xs text-muted-foreground">{change.usuario_nombre}, {new Date(change.cambiado_en).toLocaleString('es-CO')}: {change.valor_anterior ?? 'Sin valor'} → {change.valor_nuevo ?? 'Sin valor'}{change.motivo ? ` — ${change.motivo}` : ''}</p>)}
                  {selectedVisit.estado === 'finalizada' && <p className="text-sm">WhatsApp: {selectedVisit.whatsapp_notificacion_estado === 'enviada' ? 'Enviado' : selectedVisit.whatsapp_notificacion_error || 'Comparte el PDF manualmente desde el CRM.'}</p>}
                  {selectedVisit.costo_editable === false ? (
                    <p className="text-xs text-muted-foreground">El costo quedó fijado en el PDF definitivo. Para estas visitas se eliminaron las imágenes temporales después de guardarlo.</p>
                  ) : <Button variant="outline" size="sm" onClick={async () => {
                    const value = window.prompt('Nuevo costo (vacío para dejar sin valor)', selectedVisit.valor_visita == null ? '' : String(selectedVisit.valor_visita))
                    if (value === null) return
                    const amount = value.trim() === '' ? null : Number(value)
                    if (amount != null && (!Number.isFinite(amount) || amount < 0)) return
                    const reason = selectedVisit.costo_inicial != null && amount !== selectedVisit.costo_inicial && amount !== selectedVisit.costo_final
                      ? window.prompt('Motivo del cambio respecto al costo inicial') : ''
                    if (reason === null) return
                    if (selectedVisit.costo_inicial != null && amount !== selectedVisit.costo_inicial && amount !== selectedVisit.costo_final && !reason?.trim()) { window.alert('Indica el motivo del cambio.'); return }
                    try { setSelectedVisit(await visitsService.updateCost(selectedVisit.id, amount, reason || '')); loadVisits() } catch { window.alert('No fue posible actualizar el costo.') }
                  }}>Editar costo</Button>}
                  {selectedVisit.tecnico ? (
                    <p className="text-sm"><User className="inline h-3 w-3 mr-1" />{selectedVisit.tecnico.nombre_completo}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">Sin técnico asignado</p>
                  )}
                  {selectedVisit.descripcion && <p className="text-sm text-muted-foreground">{selectedVisit.descripcion}</p>}
                </CardContent></Card>
              </div>

              {/* Report */}
              {selectedVisit.reporte && (
                <Card>
                  <CardHeader className="py-3"><CardTitle className="text-sm">Reporte Técnico</CardTitle></CardHeader>
                  <CardContent className="pt-0 space-y-2 text-sm">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div><span className="text-muted-foreground">Persona que atendió:</span> {selectedVisit.reporte.persona_atiende}</div>
                      <div><span className="text-muted-foreground">Equipo:</span> {selectedVisit.reporte.equipo_display}</div>
                      <div><span className="text-muted-foreground">Ubicación:</span> {selectedVisit.reporte.ubicacion_display}</div>
                      <div><span className="text-muted-foreground">Método de pago:</span> {selectedVisit.reporte.metodo_pago_display}</div>
                      {selectedVisit.reporte.valor_servicio !== null && (
                        <div><span className="text-muted-foreground">Valor:</span> ${Number(selectedVisit.reporte.valor_servicio).toLocaleString('es-CO')}</div>
                      )}
                    </div>
                    <div><span className="text-muted-foreground font-medium">Motivo:</span> {selectedVisit.reporte.motivo_servicio}</div>
                    <div><span className="text-muted-foreground font-medium">Solución:</span> {selectedVisit.reporte.solucion_realizada}</div>
                    {selectedVisit.reporte.observaciones && <div><span className="text-muted-foreground font-medium">Observaciones:</span> {selectedVisit.reporte.observaciones}</div>}
                    {selectedVisit.reporte.recomendaciones && <div><span className="text-muted-foreground font-medium">Recomendaciones:</span> {selectedVisit.reporte.recomendaciones}</div>}
                    {selectedVisit.reporte.firma_cliente && (
                      <div>
                        <p className="text-muted-foreground font-medium mb-1">Firma del cliente:</p>
                        <img src={selectedVisit.reporte.firma_cliente} alt="Firma" className="h-20 border rounded" />
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

            </div>
          ) : null}
          <DialogFooter>
            {selectedVisit?.pdf_disponible && (
              <Button variant="outline" onClick={async () => {
                try { await visitsService.openPDF(selectedVisit.id) }
                catch { window.alert('No fue posible abrir el PDF.') }
              }}>Abrir PDF</Button>
            )}
            {selectedVisit?.pdf_disponible && (
              <Button
                variant="outline"
                disabled={downloading}
                onClick={async () => {
                  setDownloading(true)
                  try {
                    await visitsService.downloadPDF(selectedVisit.id, selectedVisit.pdf_nombre)
                  } catch (err) {
                    console.error('Error descargando PDF:', err)
                  } finally {
                    setDownloading(false)
                  }
                }}
              >
                {downloading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Descargando...
                  </>
                ) : (
                  <>
                    <FileDown className="h-4 w-4 mr-2" />
                    Descargar PDF
                  </>
                )}
              </Button>
            )}
            {selectedVisit && ['error', 'fallido'].includes(selectedVisit.pdf_estado || '') && !selectedVisit.pdf_disponible && (
              <Button variant="outline" onClick={async () => {
                try { await visitsService.retryPDF(selectedVisit.id); setSelectedVisit(await visitsService.getById(selectedVisit.id)) }
                catch { window.alert('No fue posible generar el PDF. Las imágenes se conservaron.') }
              }}>Reintentar PDF</Button>
            )}
            {selectedVisit?.pdf_disponible && (
              <Button variant="outline" onClick={async () => {
                try { await visitsService.revokeLinks(selectedVisit.id); setSelectedVisit(await visitsService.getById(selectedVisit.id)) }
                catch { window.alert('No fue posible revocar los enlaces.') }
              }}>Revocar enlaces</Button>
            )}
            <Button onClick={() => setDetailOpen(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── DELETE CONFIRM ───────────────────────────────────────────────── */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar Visita</DialogTitle>
          </DialogHeader>
          <p className="text-sm">¿Está seguro de eliminar la visita <b>#{editVisit?.numero_tarea}</b> de <b>{editVisit?.cliente_nombre}</b>?</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
