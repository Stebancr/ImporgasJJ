import { useState } from 'react'
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

interface Location {
  id: number
  name: string
  address: string
  city: string
  phone: string
  is_active: boolean
}

const mockLocations: Location[] = [
  { id: 1, name: 'Bodega Principal', address: 'Calle 45 #23-56', city: 'Bogota', phone: '+57 1 234 5678', is_active: true },
  { id: 2, name: 'Sucursal Norte', address: 'Carrera 15 #78-90', city: 'Bogota', phone: '+57 1 345 6789', is_active: true },
  { id: 3, name: 'Sucursal Medellin', address: 'Avenida 70 #32-15', city: 'Medellin', phone: '+57 4 456 7890', is_active: true },
  { id: 4, name: 'Sucursal Cali', address: 'Calle 5 #45-67', city: 'Cali', phone: '+57 2 567 8901', is_active: true },
  { id: 5, name: 'Punto de Venta Centro', address: 'Carrera 7 #12-34', city: 'Bogota', phone: '+57 1 678 9012', is_active: false },
]

export default function LocationsPage() {
  const [locations, setLocations] = useState<Location[]>(mockLocations)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    city: '',
    phone: '',
    is_active: true,
  })

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
        is_active: location.is_active,
      })
    } else {
      setEditingLocation(null)
      setFormData({
        name: '',
        address: '',
        city: '',
        phone: '',
        is_active: true,
      })
    }
    setIsDialogOpen(true)
  }

  const handleSave = () => {
    if (editingLocation) {
      setLocations(locations.map((l) =>
        l.id === editingLocation.id
          ? {
              ...l,
              name: formData.name,
              address: formData.address,
              city: formData.city,
              phone: formData.phone,
              is_active: formData.is_active,
            }
          : l
      ))
    } else {
      const newLocation: Location = {
        id: Math.max(...locations.map((l) => l.id)) + 1,
        name: formData.name,
        address: formData.address,
        city: formData.city,
        phone: formData.phone,
        is_active: formData.is_active,
      }
      setLocations([...locations, newLocation])
    }
    setIsDialogOpen(false)
  }

  const handleDelete = (id: number) => {
    if (confirm('Esta seguro de eliminar esta ubicacion?')) {
      setLocations(locations.filter((l) => l.id !== id))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ubicaciones</h1>
          <p className="text-muted-foreground">Administra los puntos fisicos y bodegas</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Ubicacion
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Lista de Ubicaciones
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
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Direccion</TableHead>
                  <TableHead>Ciudad</TableHead>
                  <TableHead>Telefono</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLocations.map((location) => (
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
                    <TableCell className="text-muted-foreground">{location.phone}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={location.is_active ? 'success' : 'secondary'}>
                        {location.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenDialog(location)}
                        >
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
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Location Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingLocation ? 'Editar Ubicacion' : 'Agregar Ubicacion'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Bodega Principal"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="address">Direccion</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Ej: Calle 45 #23-56"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="city">Ciudad</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Ej: Bogota"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="phone">Telefono</Label>
                <Input
                  id="phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+57 1 234 5678"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-input"
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                Ubicacion activa
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>
              {editingLocation ? 'Guardar cambios' : 'Crear ubicacion'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
