import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import {
  Plus, Search, Edit, Shield, UserCog, User, Users,
  Loader2, RefreshCw, ToggleLeft, ToggleRight, ChevronLeft, ChevronRight,
  Building2, Briefcase, Pencil, Trash2,
} from 'lucide-react'
import { usersService } from '@/services'
import { locationsService } from '@/services/locations'
import type { Location } from '@/types'
import type { ColaboradorData, SelectOption } from '@/services/users'

// ─── constants ────────────────────────────────────────────────────────────────

const TIPO_USUARIO: Record<number, { label: string; icon: typeof Shield }> = {
  0: { label: 'Colaborador',    icon: User },
  1: { label: 'Admin Sede',     icon: UserCog },
  2: { label: 'Lectura Admin',  icon: UserCog },
  3: { label: 'Especial',       icon: Shield },
  4: { label: 'Super Admin',    icon: Shield },
}

// ─── blank form ───────────────────────────────────────────────────────────────

const blankForm = () => ({
  usuario: '',
  password: '',
  cedula: '',
  nombre_completo: '',
  correo: '',
  telefono: '',
  cargo: '',
  tipo_usuario: '0',
  location_id: '',
})

type FormState = ReturnType<typeof blankForm>

// ─── Component ────────────────────────────────────────────────────────────────

export default function UsersPage() {
  // Tab
  const [activeTab, setActiveTab] = useState<'trabajadores' | 'usuarios'>('trabajadores')

  // List state
  const [users, setUsers] = useState<ColaboradorData[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  // Selector data
  const [cargos, setCargos] = useState<SelectOption[]>([])
  const [locations, setLocations] = useState<Location[]>([])

  // Cargos tab state
  const [cargosList, setCargosList] = useState<{ idcargo: number; nombrecargo: string }[]>([])
  const [cargosLoading, setCargosLoading] = useState(false)
  const [cargoDialog, setCargoDialog] = useState(false)
  const [editingCargo, setEditingCargo] = useState<{ idcargo: number; nombrecargo: string } | null>(null)
  const [cargoNameInput, setCargoNameInput] = useState('')
  const [savingCargo, setSavingCargo] = useState(false)

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(blankForm())
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // Role dialog
  const [roleDialogOpen, setRoleDialogOpen] = useState(false)
  const [roleTarget, setRoleTarget] = useState<ColaboradorData | null>(null)
  const [newRole, setNewRole] = useState('0')

  // Load selectors once
  useEffect(() => {
    usersService.getCargoNivelRegional().then((data) => {
      setCargos(data.cargos)
    }).catch(() => {})
    locationsService.getAll({ is_active: true, per_page: 100 }).then((res) => {
      setLocations(res.data ?? [])
    }).catch(() => {})
  }, [])

  // Load users
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await usersService.listarColaboradores({
        search: search || undefined,
        page,
        page_size: pageSize,
        tipo: activeTab === 'trabajadores' ? 'trabajador' : 'normal',
      })
      setUsers(res.results)
      setTotal(res.count)
      setTotalPages(Math.ceil(res.count / pageSize))
    } catch {
      setUsers([])
    } finally {
      setLoading(false)
    }
  }, [search, page, pageSize, activeTab])

  useEffect(() => { if (activeTab !== 'cargos') load() }, [load, activeTab])

  // Load cargos tab
  const loadCargos = useCallback(async () => {
    setCargosLoading(true)
    try {
      const data = await usersService.getCargos()
      setCargosList(data)
    } catch { setCargosList([]) } finally { setCargosLoading(false) }
  }, [])

  useEffect(() => { if (activeTab === 'cargos') loadCargos() }, [activeTab, loadCargos])

  // ── Handlers ────────────────────────────────────────────────────────────────

  const openCreate = () => {
    setEditingId(null)
    setForm({ ...blankForm(), tipo_usuario: activeTab === 'trabajadores' ? '1' : '0' })
    setFormError('')
    setDialogOpen(true)
  }

  const openEdit = (u: ColaboradorData) => {
    setEditingId(u.id)
    setForm({
      usuario: '',
      password: '',
      cedula: u.cedula,
      nombre_completo: u.nombre_completo,
      correo: u.correo ?? '',
      telefono: u.telefono ?? '',
      cargo: u.cargo != null ? String(u.cargo) : '',
      tipo_usuario: String(u.tipo_usuario ?? 0),
      location_id: u.location_id != null ? String(u.location_id) : '',
    })
    setFormError('')
    setDialogOpen(true)
  }

  const handleSave = async () => {
    setFormError('')
    if (!form.nombre_completo.trim()) { setFormError('El nombre completo es requerido'); return }
    if (!form.cedula.trim()) { setFormError('La cedula es requerida'); return }
    if (!editingId && !form.usuario.trim()) { setFormError('El nombre de usuario es requerido'); return }
    if (!editingId && form.password.length < 4) { setFormError('La contrasena debe tener al menos 4 caracteres'); return }

    setSaving(true)
    try {
      if (editingId) {
        await usersService.actualizarColaborador(editingId, {
          nombre_completo: form.nombre_completo.trim(),
          correo: form.correo.trim() || null,
          telefono: form.telefono.trim() || null,
          cargo: isTrabajadores && form.cargo ? Number(form.cargo) : null,
          location_id: isTrabajadores && form.location_id ? Number(form.location_id) : null,
        })
      } else {
        await usersService.crearColaborador({
          usuario: form.usuario.trim(),
          password: form.password,
          cedula: form.cedula.trim(),
          nombre_completo: form.nombre_completo.trim(),
          correo: form.correo.trim() || null,
          telefono: form.telefono.trim() || null,
          cargo: isTrabajadores && form.cargo ? Number(form.cargo) : null,
          tipo_usuario: Number(form.tipo_usuario),
          location_id: isTrabajadores && form.location_id ? Number(form.location_id) : null,
        })
      }
      setDialogOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      setFormError(msg || 'Error al guardar el usuario')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleEstado = async (u: ColaboradorData) => {
    const nuevoEstado: 0 | 1 = u.estado === 1 ? 0 : 1
    try {
      await usersService.cambiarEstado(u.id, nuevoEstado)
      load()
    } catch {
      alert('Error al cambiar el estado')
    }
  }

  const openRoleDialog = (u: ColaboradorData) => {
    setRoleTarget(u)
    setNewRole(String(u.tipo_usuario ?? 0))
    setRoleDialogOpen(true)
  }

  const handleChangeRole = async () => {
    if (!roleTarget) return
    try {
      await usersService.actualizarRol(roleTarget.id, Number(newRole))
      setRoleDialogOpen(false)
      load()
    } catch {
      alert('Error al cambiar el rol')
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const isTrabajadores = activeTab === 'trabajadores'
  const isCargos = activeTab === 'cargos'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {isCargos ? 'Cargos' : isTrabajadores ? 'Trabajadores' : 'Usuarios del sistema'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {isCargos
              ? 'Administra los cargos disponibles para los trabajadores'
              : isTrabajadores
              ? 'Colaboradores con acceso al panel de administración'
              : 'Usuarios registrados en la tienda (tipo 0)'}
          </p>
        </div>
        {!isCargos && (
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            {isTrabajadores ? 'Nuevo trabajador' : 'Nuevo usuario'}
          </Button>
        )}
        {isCargos && (
          <Button onClick={() => { setEditingCargo(null); setCargoNameInput(''); setCargoDialog(true) }}>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo cargo
          </Button>
        )}
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 p-1 bg-muted rounded-lg w-fit">
        <button
          onClick={() => { setActiveTab('trabajadores'); setPage(1); setSearch('') }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            isTrabajadores ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Briefcase className="h-4 w-4" />
          Trabajadores
        </button>
        <button
          onClick={() => { setActiveTab('usuarios'); setPage(1); setSearch('') }}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'usuarios' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <User className="h-4 w-4" />
          Usuarios
        </button>
        <button
          onClick={() => setActiveTab('cargos')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            isCargos ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Briefcase className="h-4 w-4" />
          Cargos
        </button>
      </div>

      {/* ── Cargos tab content ────────────────────────────────────────────── */}
      {isCargos && (
        <Card>
          <CardContent className="p-0">
            {cargosLoading ? (
              <div className="py-12 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>
            ) : cargosList.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground text-sm">No hay cargos registrados</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre del cargo</TableHead>
                    <TableHead className="text-right w-24">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cargosList.map((c) => (
                    <TableRow key={c.idcargo}>
                      <TableCell className="font-medium">{c.nombrecargo}</TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="icon" title="Editar"
                            onClick={() => { setEditingCargo(c); setCargoNameInput(c.nombrecargo); setCargoDialog(true) }}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" title="Eliminar"
                            onClick={async () => {
                              if (!confirm(`\u00bfEliminar el cargo "${c.nombrecargo}"?`)) return
                              try { await usersService.deleteCargo(c.idcargo); loadCargos() } catch { alert('Error al eliminar') }
                            }}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Cargo dialog ──────────────────────────────────────────────────── */}
      <Dialog open={cargoDialog} onOpenChange={setCargoDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editingCargo ? 'Editar cargo' : 'Nuevo cargo'}</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Label className="text-xs">Nombre del cargo *</Label>
            <Input className="mt-1" placeholder="Ej: Asesor comercial"
              value={cargoNameInput} onChange={(e) => setCargoNameInput(e.target.value)}
              onKeyDown={async (e) => { if (e.key === 'Enter') { /* handled by button */ } }} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCargoDialog(false)}>Cancelar</Button>
            <Button disabled={savingCargo} onClick={async () => {
              const nombre = cargoNameInput.trim()
              if (!nombre) return
              setSavingCargo(true)
              try {
                if (editingCargo) {
                  await usersService.updateCargo(editingCargo.idcargo, nombre)
                } else {
                  await usersService.createCargo(nombre)
                }
                setCargoDialog(false)
                loadCargos()
                // Refresh cargos selector too
                usersService.getCargoNivelRegional().then((d) => setCargos(d.cargos)).catch(() => {})
              } catch (err: unknown) {
                alert((err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Error al guardar')
              } finally { setSavingCargo(false) }
            }}>
              {savingCargo && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editingCargo ? 'Guardar cambios' : 'Crear cargo'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stats bar — hidden on cargos tab */}
      {!isCargos && (
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        {[
          { icon: isTrabajadores ? Briefcase : User, label: isTrabajadores ? 'Total trabajadores' : 'Total usuarios', value: total,                                       color: 'text-foreground' },
          { icon: Shield,  label: 'Activos',          value: users.filter((u) => u.estado === 1).length, color: 'text-green-600' },
          { icon: UserCog, label: 'Inactivos',        value: users.filter((u) => u.estado === 0).length, color: 'text-red-500' },
          { icon: Users,   label: 'Esta pagina',      value: users.length,                                color: 'text-blue-500' },
        ].map(({ icon: Icon, label, value, color }) => (
          <Card key={label} className="py-3">
            <CardContent className="flex items-center gap-3 px-4 py-0">
              <Icon className={`h-5 w-5 ${color}`} />
              <div>
                <p className="text-xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      )}

      {/* Table — hidden on cargos tab */}
      {!isCargos && (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              {isTrabajadores ? <Briefcase className="h-5 w-5" /> : <User className="h-5 w-5" />}
              {isTrabajadores ? 'Lista de trabajadores' : 'Lista de usuarios'} <span className="text-muted-foreground font-normal">({total})</span>
            </CardTitle>
            <div className="flex gap-2">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-8 h-9"
                  placeholder="Buscar por nombre, cedula..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1) }}
                />
              </div>
              <Button variant="ghost" size="icon" onClick={load}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{isTrabajadores ? 'Trabajador' : 'Usuario'}</TableHead>
                  <TableHead>Contacto</TableHead>
                  {isTrabajadores && <TableHead>Cargo</TableHead>}
                  {isTrabajadores && <TableHead>Sede</TableHead>}
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={isTrabajadores ? 6 : 4} className="text-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={isTrabajadores ? 6 : 4} className="text-center py-12 text-muted-foreground">
                      {isTrabajadores ? 'No se encontraron trabajadores' : 'No se encontraron usuarios'}
                    </TableCell>
                  </TableRow>
                ) : users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-sm">
                          {u.nombre_completo.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-sm leading-tight">{u.nombre_completo}</p>
                          <p className="text-xs text-muted-foreground">CC {u.cedula}</p>
                          {u.usuario && <p className="text-xs text-muted-foreground/70">@{u.usuario}</p>}
                          {isTrabajadores && u.tipo_usuario != null && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary mt-0.5">
                              {TIPO_USUARIO[u.tipo_usuario]?.label ?? `Tipo ${u.tipo_usuario}`}
                            </span>
                          )}
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="text-sm space-y-0.5">
                        {u.correo && <p className="text-muted-foreground truncate max-w-[180px]">{u.correo}</p>}
                        {u.telefono && <p className="text-muted-foreground">{u.telefono}</p>}
                        {!u.correo && !u.telefono && <span className="text-muted-foreground/50 text-xs">—</span>}
                      </div>
                    </TableCell>

                    {isTrabajadores && (
                      <TableCell>
                        {u.nombre_cargo ? (
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Briefcase className="h-3 w-3 shrink-0" />
                            <span className="truncate max-w-[140px]">{u.nombre_cargo}</span>
                          </div>
                        ) : <span className="text-muted-foreground/50 text-xs">—</span>}
                      </TableCell>
                    )}

                    {isTrabajadores && (
                      <TableCell>
                        {u.location_name ? (
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Building2 className="h-3 w-3 shrink-0" />
                            <span className="truncate max-w-[140px]">{u.location_name}</span>
                          </div>
                        ) : <span className="text-muted-foreground/50 text-xs">—</span>}
                      </TableCell>
                    )}

                    <TableCell className="text-center">
                      <button
                        onClick={() => handleToggleEstado(u)}
                        title="Clic para cambiar estado"
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${
                          u.estado === 1
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-red-100 text-red-700 hover:bg-red-200'
                        }`}
                      >
                        {u.estado === 1
                          ? <><ToggleRight className="h-3.5 w-3.5" /> Activo</>
                          : <><ToggleLeft className="h-3.5 w-3.5" /> Inactivo</>}
                      </button>
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" title="Editar datos" onClick={() => openEdit(u)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        {isTrabajadores && (
                          <Button variant="ghost" size="icon" title="Cambiar rol" onClick={() => openRoleDialog(u)}>
                            <Shield className="h-4 w-4 text-blue-500" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t">
              <Button variant="ghost" size="icon" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">{page} / {totalPages}</span>
              <Button variant="ghost" size="icon" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {/* ── Create / Edit Dialog ─────────────────────────────────────────── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingId
                ? (isTrabajadores ? 'Editar trabajador' : 'Editar usuario')
                : (isTrabajadores ? 'Nuevo trabajador' : 'Nuevo usuario')}
            </DialogTitle>
          </DialogHeader>

          {formError && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">{formError}</div>
          )}

          <div className="space-y-4">
            {/* Credenciales — only when creating */}
            {!editingId && (
              <div className="rounded-lg border p-4 space-y-3 bg-muted/30">
                <p className="text-sm font-semibold text-foreground">Credenciales de acceso</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Usuario *</Label>
                    <Input className="mt-1 h-8 text-sm" placeholder="nombre.usuario"
                      value={form.usuario} onChange={(e) => setForm((f) => ({ ...f, usuario: e.target.value }))} />
                  </div>
                  <div>
                    <Label className="text-xs">Contrasena *</Label>
                    <Input className="mt-1 h-8 text-sm" type="password" placeholder="••••••••"
                      value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Tipo de usuario</Label>
                  <Select value={form.tipo_usuario} onValueChange={(v) => setForm((f) => ({ ...f, tipo_usuario: v }))}>
                    <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {isTrabajadores ? (
                        <>
                          <SelectItem value="1">1 — Admin de Sede</SelectItem>
                          <SelectItem value="2">2 — Lectura Admin</SelectItem>
                          <SelectItem value="3">3 — Especial</SelectItem>
                          <SelectItem value="4">4 — Super Admin</SelectItem>
                        </>
                      ) : (
                        <SelectItem value="0">0 — Usuario normal</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {/* Datos personales */}
            <div className="rounded-lg border p-4 space-y-3">
              <p className="text-sm font-semibold text-foreground">Datos personales</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Nombre completo *</Label>
                  <Input className="mt-1 h-8 text-sm" placeholder="Juan Perez"
                    value={form.nombre_completo} onChange={(e) => setForm((f) => ({ ...f, nombre_completo: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Cedula *</Label>
                  <Input className="mt-1 h-8 text-sm" placeholder="12345678"
                    value={form.cedula} onChange={(e) => setForm((f) => ({ ...f, cedula: e.target.value }))}
                    disabled={!!editingId} />
                </div>
                <div>
                  <Label className="text-xs">Correo electronico</Label>
                  <Input type="email" className="mt-1 h-8 text-sm" placeholder="juan@empresa.com"
                    value={form.correo} onChange={(e) => setForm((f) => ({ ...f, correo: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Telefono</Label>
                  <Input className="mt-1 h-8 text-sm" placeholder="+57 300 123 4567"
                    value={form.telefono} onChange={(e) => setForm((f) => ({ ...f, telefono: e.target.value }))} />
                </div>
              </div>
            </div>

            {/* Cargo y Sede — solo para trabajadores */}
            {isTrabajadores && (
              <div className="rounded-lg border p-4 space-y-3">
                <p className="text-sm font-semibold text-foreground">Cargo y sede</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Cargo</Label>
                    <Select value={form.cargo || '__none__'} onValueChange={(v) => setForm((f) => ({ ...f, cargo: v === '__none__' ? '' : v }))}>
                      <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">Sin cargo</SelectItem>
                        {cargos.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Sede</Label>
                    <Select value={form.location_id || '__none__'} onValueChange={(v) => setForm((f) => ({ ...f, location_id: v === '__none__' ? '' : v }))}>
                      <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue placeholder="Seleccionar sede" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">Sin sede</SelectItem>
                        {locations.map((l) => <SelectItem key={l.id} value={String(l.id)}>{l.name} — {l.city}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editingId ? 'Guardar cambios' : (isTrabajadores ? 'Crear trabajador' : 'Crear usuario')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Role Dialog ──────────────────────────────────────────────────── */}
      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Cambiar rol — {roleTarget?.nombre_completo}</DialogTitle>
          </DialogHeader>
          <div className="py-2 space-y-3">
            <p className="text-sm text-muted-foreground">
              Selecciona el nuevo tipo de usuario. Esto afecta el acceso al sistema.
            </p>
            <Select value={newRole} onValueChange={setNewRole}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(TIPO_USUARIO)
                  .filter(([k]) => isTrabajadores ? Number(k) >= 1 : true)
                  .map(([k, v]) => {
                    const Icon = v.icon
                    return (
                      <SelectItem key={k} value={k}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          <span>{v.label} ({k})</span>
                        </div>
                      </SelectItem>
                    )
                  })}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleChangeRole}>Aplicar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
