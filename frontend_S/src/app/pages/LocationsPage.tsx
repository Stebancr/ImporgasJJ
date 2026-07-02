import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Plus, Search, Edit, Trash2, MapPin } from 'lucide-react'
import { locationsService } from '@/services/locations'
import type { Location } from '@/types'

const defaultForm = {
  name: '',
  address: '',
  city: '',
  phone: '',
  hours_weekday: '',
  hours_saturday: '',
  hours_sunday: '',
  is_active: true,
}

export default function LocationsPage() {
  const [locations, setLocations] = useState<Location[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [formData, setFormData] = useState(defaultForm)

  const fetchLocations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await locationsService.getAll({ per_page: 100 })
      setLocations(res.data)
    } catch {
      setError('Error al cargar las ubicaciones')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchLocations() }, [])

  const filteredLocations = locations.filter(
    (location) =>
      location.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      location.city.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleOpenDialog = (location?: Location) => {
    if (location) {
      setEditingLocation(location)
      setFormData({
        name: location.name,
        address: location.address,
        city: location.city,
        phone: location.phone,
        hours_weekday: location.hours_weekday,
        hours_saturday: location.hours_saturday,
        hours_sunday: location.hours_sunday,
        is_active: location.is_active,
      })
    } else {
      setEditingLocation(null)
      setFormData(defaultForm)
    }
    setError(null)
    setIsDialogOpen(true)
  }

  const handleSave = async () => {
    if (!formData.name || !formData.address || !formData.city) {
      setError('Nombre, dirección y ciudad son obligatorios')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      if (editingLocation) {
        await locationsService.update(editingLocation.id, formData)
      } else {
        await locationsService.create(formData)
      }
      setIsDialogOpen(false)
      await fetchLocations()
    } catch {
      setError('Error al guardar la ubicación')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar esta ubicación?')) return
    try {
      await locationsService.delete(id)
      await fetchLocations()
    } catch {
      setError('Error al eliminar la ubicación')
    }
  }

  const handleToggleActive = async (id: number) => {
    try {
      const updated = await locationsService.toggleActive(id)
      setLocations(prev => prev.map(l => l.id === id ? updated : l))
    } catch {
      setError('Error al cambiar el estado')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ubicaciones</h1>
          <p className="text-muted-foreground">Administra los puntos físicos y bodegas</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Ubicación
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Lista de Ubicaciones
              <Badge variant="secondary">{locations.length}</Badge>
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar ubicaciones..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12 text-center text-muted-foreground">Cargando...</div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Dirección</TableHead>
                    <TableHead>Ciudad</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead className="text-center">Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLocations.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        No hay ubicaciones
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredLocations.map((location) => (
                      <TableRow key={location.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                              <MapPin className="h-4 w-4" />
                            </div>
                            <span className="font-medium">{location.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{location.address}</TableCell>
                        <TableCell>{location.city}</TableCell>
                        <TableCell className="text-muted-foreground">{location.phone || '—'}</TableCell>
                        <TableCell className="text-center">
                          <button onClick={() => handleToggleActive(location.id)}>
                            <Badge variant={location.is_active ? 'success' : 'secondary'} className="cursor-pointer">
                              {location.is_active ? 'Activa' : 'Inactiva'}
                            </Badge>
                          </button>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(location)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(location.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Location Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>
              {editingLocation ? 'Editar Ubicación' : 'Agregar Ubicación'}
            </DialogTitle>
          </DialogHeader>
          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Bodega Principal"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="address">Dirección *</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Ej: Calle 45 #23-56"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="city">Ciudad *</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Ej: Bogotá"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="phone">Teléfono</Label>
                <Input
                  id="phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+57 1 234 5678"
                />
              </div>
            </div>            <div className="grid gap-2">
              <Label>Horarios de atención</Label>
              <div className="grid grid-cols-1 gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-20 shrink-0">Lun - Vie</span>
                  <Input
                    value={formData.hours_weekday}
                    onChange={(e) => setFormData({ ...formData, hours_weekday: e.target.value })}
                    placeholder="Ej: 8:00 AM - 6:00 PM"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-20 shrink-0">Sábado</span>
                  <Input
                    value={formData.hours_saturday}
                    onChange={(e) => setFormData({ ...formData, hours_saturday: e.target.value })}
                    placeholder="Ej: 9:00 AM - 2:00 PM"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-20 shrink-0">Domingo</span>
                  <Input
                    value={formData.hours_sunday}
                    onChange={(e) => setFormData({ ...formData, hours_sunday: e.target.value })}
                    placeholder="Ej: Cerrado"
                  />
                </div>
              </div>
            </div>            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-input"
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                Ubicación activa
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSaving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Guardando...' : editingLocation ? 'Guardar cambios' : 'Crear ubicación'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
