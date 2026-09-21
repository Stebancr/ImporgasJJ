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
  VisitaItem, VisitaDetalle, CreateVisitaData, Tecnico, CalendarioData,
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

const TIPO_TAREA_OPTS = [
  { value: 'visita_urbana', label: 'VISITA TECNICA PERIMETRO URBANO' },
  { value: 'instalacion_calentador', label: '2025 INSTALACION DE CALENTADOR' },
  { value: 'mantenimiento_calentador', label: '2025 MANTENIMIENTO O REPARACION DE CALENTADOR' },
  { value: 'instalacion_secadora', label: '2025 INSTALACION DE SECADORA' },
  { value: 'servicio_cancelado', label: 'SERVICIO CANCELADO' },
  { value: 'visita_afueras', label: 'VISITA TECNICA PERIMETRO URBANO AFUERAS' },
  { value: 'mantenimiento_estufa', label: '2025 MANTENIMIENTO O REPARACION DE ESTUFA' },
  { value: 'revision_periodica', label: 'REVISION PERIODICA' },
  { value: 'mantenimiento_acumulacion', label: '2025 MANTENIMIENTO O REPARACION CALENTADOR DE ACUMULACION A GAS' },
  { value: 'programacion_doble', label: 'PROGRAMACION DOBLE' },
  { value: 'mantenimiento_turco', label: '2025 MANTENIMIENTO O REPARACION CALENTADOR DE TURCO DE PASO' },
]

const DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

const blankForm = (): CreateVisitaData => ({
  cliente_nombre: '',
  cliente_identificacion: '',
  cliente_telefono: '',
  cliente_correo: '',
  cliente_direccion: '',
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
    required('cliente_identificacion', data.cliente_identificacion)
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
  if (data.valor_visita == null || !Number.isFinite(data.valor_visita)) errors.valor_visita = 'Este campo es obligatorio.'
  else if (data.valor_visita < 0) errors.valor_visita = 'El valor de la visita no puede ser negativo.'
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
    if (Object.keys(errors).length) {
      setFormErrors(errors)
      return
    }
    setSaving(true)
    try {
      await visitsService.create(form)
      setCreateOpen(false)
      setForm(blankForm())
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
  const openEdit = (visit: VisitaItem) => {
    if (visit.estado === 'finalizada') return
    setEditVisit(visit)
    setForm({
      cliente_nombre: visit.cliente_nombre,
      cliente_telefono: visit.cliente_telefono || '',
      cliente_correo: '',
      cliente_identificacion: '',
      cliente_direccion: visit.cliente_direccion,
      tipo_tarea: visit.tipo_tarea,
      fecha: visit.fecha,
      hora: visit.hora,
      descripcion: '',
      observaciones_iniciales: '',
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
    setSaving(true)
    try {
      await visitsService.update(editVisit.id, {
        ...(TIPO_TAREA_OPTS.some((option) => option.value === form.tipo_tarea) ? { tipo_tarea: form.tipo_tarea } : {}),
        fecha: form.fecha,
        hora: form.hora,
        descripcion: form.descripcion,
        observaciones_iniciales: form.observaciones_iniciales,
        valor_visita: form.valor_visita,
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
        <Button className="w-full sm:w-auto" onClick={() => { setForm(blankForm()); setFormErrors({}); setCreateOpen(true) }}>
          <Plus className="h-4 w-4 mr-2" /> Nueva Visita
        </Button>
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
                          {v.valor_visita == null ? '—' : `$${v.valor_visita.toLocaleString('es-CO')}`}
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
                  <Label>Identificación *</Label>
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

            {/* ── Visit section ── */}
            <div className="col-span-2">
              <p className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Datos de la Visita</p>
            </div>
            <div>
              <Label>Tipo de servicio *</Label>
              <Select value={TIPO_TAREA_OPTS.some((option) => option.value === form.tipo_tarea) ? form.tipo_tarea : undefined} onValueChange={(v) => setField('tipo_tarea', v)}>
                <SelectTrigger className="min-w-0"><SelectValue placeholder="Selecciona un servicio" /></SelectTrigger>
                <SelectContent className="max-w-[calc(100vw-2rem)]">
                  {TIPO_TAREA_OPTS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {editOpen && form.tipo_tarea && !TIPO_TAREA_OPTS.some((option) => option.value === form.tipo_tarea) && <p className="mt-1 text-xs text-muted-foreground">Valor anterior: {editVisit?.tipo_tarea_display}. Se conserva si no eliges uno nuevo.</p>}
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
              <Label>Valor de la visita *</Label>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setCreateOpen(false); setEditOpen(false) }}>Cancelar</Button>
            <Button onClick={editOpen ? handleEdit : handleCreate} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editOpen ? 'Guardar cambios' : 'Crear visita'}
            </Button>
          </DialogFooter>
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
                </CardContent></Card>

                <Card><CardContent className="pt-3 pb-3 space-y-1">
                  <p className="text-xs text-muted-foreground font-semibold">VISITA</p>
                  <p className="text-sm"><CalendarDays className="inline h-3 w-3 mr-1" />{selectedVisit.fecha} a las {selectedVisit.hora?.slice(0, 5)}</p>
                  <p className="text-sm">
                    Valor: {selectedVisit.valor_visita == null ? 'No informado' : `$${selectedVisit.valor_visita.toLocaleString('es-CO')}`}
                  </p>
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
                      {selectedVisit.reporte.valor_servicio && (
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

              {/* Photos */}
              {selectedVisit.evidencias.length > 0 && (
                <Card>
                  <CardHeader className="py-3"><CardTitle className="text-sm">Evidencias ({selectedVisit.evidencias.length})</CardTitle></CardHeader>
                  <CardContent className="pt-0">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      {selectedVisit.evidencias.map((e) => (
                        <a key={e.id} href={e.imagen} target="_blank" rel="noopener noreferrer">
                          <img src={e.imagen} alt="" className="w-full h-28 object-cover rounded border hover:opacity-90 transition-opacity" />
                        </a>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : null}
          <DialogFooter>
            {selectedVisit?.tiene_reporte && (
              <Button
                variant="outline"
                disabled={downloading}
                onClick={async () => {
                  setDownloading(true)
                  try {
                    await visitsService.downloadPDF(selectedVisit.id)
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
