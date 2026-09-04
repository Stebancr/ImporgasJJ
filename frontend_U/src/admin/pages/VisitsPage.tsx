import { useState, useEffect, useCallback } from 'react'
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

// â”€â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const ESTADO_CONFIG: Record<string, { label: string; color: string }> = {
  pendiente:   { label: 'Pendiente',  color: 'bg-yellow-100 text-yellow-800' },
  en_proceso:  { label: 'En Proceso', color: 'bg-blue-100 text-blue-800' },
  finalizada:  { label: 'Finalizada', color: 'bg-green-100 text-green-800' },
  cancelada:   { label: 'Cancelada',  color: 'bg-red-100 text-red-800' },
}

const TIPO_TAREA_OPTS = [
  { value: 'mantenimiento', label: 'Mantenimiento Preventivo' },
  { value: 'instalacion',   label: 'InstalaciÃ³n' },
  { value: 'reparacion',    label: 'ReparaciÃ³n' },
  { value: 'revision',      label: 'RevisiÃ³n TÃ©cnica' },
  { value: 'visita_tecnica',label: 'Visita TÃ©cnica PerÃ­metro Urbano' },
  { value: 'garantia',      label: 'GarantÃ­a' },
]

const DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'MiÃ©', 'Jue', 'Vie', 'SÃ¡b']

const blankForm = (): CreateVisitaData => ({
  cliente_nombre: '',
  cliente_identificacion: '',
  cliente_telefono: '',
  cliente_correo: '',
  cliente_direccion: '',
  tipo_tarea: 'revision',
  fecha: format(new Date(), 'yyyy-MM-dd'),
  hora: '08:00',
  descripcion: '',
  observaciones_iniciales: '',
  tecnico_id: null,
})

// â”€â”€â”€ Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function VisitsPage() {
  const [tab, setTab] = useState<'lista' | 'calendario'>('lista')
  const [visits, setVisits] = useState<VisitaItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tecnicos, setTecnicos] = useState<Tecnico[]>([])

  // Filters
  const [search, setSearch] = useState('')
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
  const [detailLoading, setDetailLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // Calendar
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [calendarioData, setCalendarioData] = useState<CalendarioData>({})
  const [calendarLoading, setCalendarLoading] = useState(false)
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)

  // Load data
  const loadVisits = useCallback(async () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (estadoFilter !== 'all') params.estado = estadoFilter
    if (tecnicoFilter !== 'all') params.tecnico_id = tecnicoFilter
    if (search) params.search = search
    try {
      const data = await visitsService.getAll(params)
      setVisits(Array.isArray(data) ? data : [])
    } catch {
      setVisits([])
    } finally {
      setLoading(false)
    }
  }, [estadoFilter, tecnicoFilter, search])

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

  useEffect(() => { loadVisits() }, [loadVisits])
  useEffect(() => { if (tab === 'calendario') loadCalendar() }, [tab, loadCalendar])

  // â”€â”€ Create â”€â”€
  const handleCreate = async () => {
    if (!form.cliente_nombre || !form.cliente_direccion || !form.fecha || !form.hora) return
    setSaving(true)
    try {
      await visitsService.create(form)
      setCreateOpen(false)
      setForm(blankForm())
      loadVisits()
      if (tab === 'calendario') loadCalendar()
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  // â”€â”€ Detail â”€â”€
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

  // â”€â”€ Edit â”€â”€
  const openEdit = (visit: VisitaItem) => {
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
      tecnico_id: visit.tecnico_id,
    })
    setEditOpen(true)
  }

  const handleEdit = async () => {
    if (!editVisit) return
    setSaving(true)
    try {
      await visitsService.update(editVisit.id, {
        tipo_tarea: form.tipo_tarea,
        fecha: form.fecha,
        hora: form.hora,
        descripcion: form.descripcion,
        observaciones_iniciales: form.observaciones_iniciales,
        tecnico: form.tecnico_id ?? null,
      })
      setEditOpen(false)
      loadVisits()
      if (tab === 'calendario') loadCalendar()
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  // â”€â”€ Delete â”€â”€
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

  // â”€â”€ Calendar helpers â”€â”€
  const calendarDays = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth),
  })
  const firstDayOffset = getDay(startOfMonth(currentMonth))
  const dayVisits = (day: Date) => {
    const key = format(day, 'yyyy-MM-dd')
    return calendarioData[key] || []
  }

  // â”€â”€ Form field helper â”€â”€
  const setField = (key: keyof CreateVisitaData, value: string | number | null) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Visitas TÃ©cnicas</h1>
          <p className="text-muted-foreground text-sm">Agenda y gestiona las visitas de los tÃ©cnicos</p>
        </div>
        <Button onClick={() => { setForm(blankForm()); setCreateOpen(true) }}>
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
            {t === 'lista' ? 'ðŸ“‹ Lista' : 'ðŸ“… Calendario'}
          </button>
        ))}
      </div>

      {/* â”€â”€ LIST TAB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {tab === 'lista' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por cliente, tarea o direcciÃ³n..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
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
                <SelectValue placeholder="TÃ©cnico" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los tÃ©cnicos</SelectItem>
                {tecnicos.map((t) => (
                  <SelectItem key={t.id} value={String(t.id)}>{t.nombre_completo || t.usuario}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon" onClick={loadVisits}>
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
                    <TableHead>DirecciÃ³n</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Fecha / Hora</TableHead>
                    <TableHead>TÃ©cnico</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Reporte</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : visits.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
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
                            <span className="text-xs text-muted-foreground">â€”</span>
                          )}
                          {v.evidencias_count > 0 && (
                            <span className="ml-1 text-xs text-muted-foreground">{v.evidencias_count}ðŸ“·</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openDetail(v.id)}>
                              <Eye className="h-3 w-3" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(v)}>
                              <Pencil className="h-3 w-3" />
                            </Button>
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
                            >
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

      {/* â”€â”€ CALENDAR TAB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {tab === 'calendario' && (
        <div className="space-y-4">
          {/* Month nav */}
          <div className="flex items-center justify-between">
            <Button variant="outline" size="icon" onClick={() => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="font-semibold text-lg capitalize">
              {format(currentMonth, 'MMMM yyyy', { locale: es })}
            </h2>
            <Button variant="outline" size="icon" onClick={() => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {calendarLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-1">
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
                    onClick={() => setSelectedDay(isSelected ? null : day)}
                    className={`min-h-[80px] p-1 rounded border cursor-pointer transition-colors ${
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
                        <div className="text-[10px] text-muted-foreground pl-1">+{visits.length - 3} mÃ¡s</div>
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
                  <p className="text-sm text-muted-foreground">No hay visitas este dÃ­a.</p>
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
                          {' Â· '}{v.tipo_tarea}
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

      {/* â”€â”€ CREATE / EDIT FORM MODAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <Dialog open={createOpen || editOpen} onOpenChange={(o) => { if (!o) { setCreateOpen(false); setEditOpen(false) } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editOpen ? 'Editar Visita' : 'Nueva Visita TÃ©cnica'}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-2">

            {/* â”€â”€ Client section (create only) â”€â”€ */}
            {!editOpen && (
              <>
                <div className="col-span-2">
                  <p className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Datos del Cliente</p>
                </div>
                <div>
                  <Label>Nombre completo *</Label>
                  <Input value={form.cliente_nombre} onChange={(e) => setField('cliente_nombre', e.target.value)} />
                </div>
                <div>
                  <Label>IdentificaciÃ³n</Label>
                  <Input value={form.cliente_identificacion || ''} onChange={(e) => setField('cliente_identificacion', e.target.value)} />
                </div>
                <div>
                  <Label>TelÃ©fono</Label>
                  <Input value={form.cliente_telefono || ''} onChange={(e) => setField('cliente_telefono', e.target.value)} />
                </div>
                <div>
                  <Label>Correo</Label>
                  <Input type="email" value={form.cliente_correo || ''} onChange={(e) => setField('cliente_correo', e.target.value)} />
                </div>
                <div className="col-span-2">
                  <Label>DirecciÃ³n *</Label>
                  <Textarea rows={2} value={form.cliente_direccion} onChange={(e) => setField('cliente_direccion', e.target.value)} />
                </div>
              </>
            )}

            {/* â”€â”€ Visit section â”€â”€ */}
            <div className="col-span-2">
              <p className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Datos de la Visita</p>
            </div>
            <div>
              <Label>Tipo de tarea *</Label>
              <Select value={form.tipo_tarea} onValueChange={(v) => setField('tipo_tarea', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIPO_TAREA_OPTS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>TÃ©cnico asignado</Label>
              <Select
                value={form.tecnico_id != null ? String(form.tecnico_id) : '__none__'}
                onValueChange={(v) => setField('tecnico_id', v === '__none__' ? null : Number(v))}
              >
                <SelectTrigger><SelectValue placeholder="Sin asignar" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Sin asignar</SelectItem>
                  {tecnicos.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>{t.nombre_completo || t.usuario}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Fecha *</Label>
              <Input type="date" value={form.fecha} onChange={(e) => setField('fecha', e.target.value)} />
            </div>
            <div>
              <Label>Hora *</Label>
              <Input type="time" value={form.hora} onChange={(e) => setField('hora', e.target.value)} />
            </div>
            <div className="col-span-2">
              <Label>DescripciÃ³n de la tarea</Label>
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

      {/* â”€â”€ DETAIL MODAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
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
              <div className="grid grid-cols-2 gap-3">
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
                  {selectedVisit.tecnico ? (
                    <p className="text-sm"><User className="inline h-3 w-3 mr-1" />{selectedVisit.tecnico.nombre_completo}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">Sin tÃ©cnico asignado</p>
                  )}
                  {selectedVisit.descripcion && <p className="text-sm text-muted-foreground">{selectedVisit.descripcion}</p>}
                </CardContent></Card>
              </div>

              {/* Report */}
              {selectedVisit.reporte && (
                <Card>
                  <CardHeader className="py-3"><CardTitle className="text-sm">Reporte TÃ©cnico</CardTitle></CardHeader>
                  <CardContent className="pt-0 space-y-2 text-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div><span className="text-muted-foreground">Persona que atendiÃ³:</span> {selectedVisit.reporte.persona_atiende}</div>
                      <div><span className="text-muted-foreground">Equipo:</span> {selectedVisit.reporte.equipo_display}</div>
                      <div><span className="text-muted-foreground">UbicaciÃ³n:</span> {selectedVisit.reporte.ubicacion_display}</div>
                      <div><span className="text-muted-foreground">MÃ©todo de pago:</span> {selectedVisit.reporte.metodo_pago_display}</div>
                      {selectedVisit.reporte.valor_servicio && (
                        <div><span className="text-muted-foreground">Valor:</span> ${Number(selectedVisit.reporte.valor_servicio).toLocaleString('es-CO')}</div>
                      )}
                    </div>
                    <div><span className="text-muted-foreground font-medium">Motivo:</span> {selectedVisit.reporte.motivo_servicio}</div>
                    <div><span className="text-muted-foreground font-medium">SoluciÃ³n:</span> {selectedVisit.reporte.solucion_realizada}</div>
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
                    <div className="grid grid-cols-3 gap-2">
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

      {/* â”€â”€ DELETE CONFIRM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar Visita</DialogTitle>
          </DialogHeader>
          <p className="text-sm">Â¿EstÃ¡ seguro de eliminar la visita <b>#{editVisit?.numero_tarea}</b> de <b>{editVisit?.cliente_nombre}</b>?</p>
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
