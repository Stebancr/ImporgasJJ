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
import { Textarea } from '@/components/ui/textarea'
import { Plus, Search, Edit, Trash2, Tags } from 'lucide-react'

interface Brand {
  id: number
  name: string
  slug: string
  logo: string
  description: string
  is_active: boolean
  productsCount: number
}

const mockBrands: Brand[] = [
  { id: 1, name: 'Haceb', slug: 'haceb', logo: '', description: 'Marca colombiana de electrodomesticos', is_active: true, productsCount: 25 },
  { id: 2, name: 'Samsung', slug: 'samsung', logo: '', description: 'Marca coreana de tecnologia', is_active: true, productsCount: 18 },
  { id: 3, name: 'LG', slug: 'lg', logo: '', description: 'Marca coreana de electrodomesticos', is_active: true, productsCount: 15 },
  { id: 4, name: 'Fisher', slug: 'fisher', logo: '', description: 'Especialistas en reguladores de gas', is_active: true, productsCount: 12 },
  { id: 5, name: 'Stanley', slug: 'stanley', logo: '', description: 'Herramientas profesionales', is_active: true, productsCount: 30 },
  { id: 6, name: 'Bosch', slug: 'bosch', logo: '', description: 'Tecnologia alemana de calidad', is_active: true, productsCount: 22 },
  { id: 7, name: 'Challenger', slug: 'challenger', logo: '', description: 'Electrodomesticos colombianos', is_active: true, productsCount: 20 },
  { id: 8, name: 'Coltgas', slug: 'coltgas', logo: '', description: 'Accesorios y reguladores de gas', is_active: true, productsCount: 14 },
]

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>(mockBrands)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    logo: '',
    is_active: true,
  })

  const filteredBrands = brands.filter((brand) =>
    brand.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleOpenDialog = (brand?: Brand) => {
    if (brand) {
      setEditingBrand(brand)
      setFormData({
        name: brand.name,
        description: brand.description,
        logo: brand.logo,
        is_active: brand.is_active,
      })
    } else {
      setEditingBrand(null)
      setFormData({
        name: '',
        description: '',
        logo: '',
        is_active: true,
      })
    }
    setIsDialogOpen(true)
  }

  const handleSave = () => {
    if (editingBrand) {
      setBrands(brands.map((b) =>
        b.id === editingBrand.id
          ? {
              ...b,
              name: formData.name,
              slug: formData.name.toLowerCase().replace(/ /g, '-'),
              description: formData.description,
              logo: formData.logo,
              is_active: formData.is_active,
            }
          : b
      ))
    } else {
      const newBrand: Brand = {
        id: Math.max(...brands.map((b) => b.id)) + 1,
        name: formData.name,
        slug: formData.name.toLowerCase().replace(/ /g, '-'),
        description: formData.description,
        logo: formData.logo,
        is_active: formData.is_active,
        productsCount: 0,
      }
      setBrands([...brands, newBrand])
    }
    setIsDialogOpen(false)
  }

  const handleDelete = (id: number) => {
    if (confirm('Esta seguro de eliminar esta marca?')) {
      setBrands(brands.filter((b) => b.id !== id))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Marcas</h1>
          <p className="text-muted-foreground">Administra las marcas de productos</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Marca
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <Tags className="h-5 w-5" />
              Lista de Marcas
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar marcas..."
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
                  <TableHead>Marca</TableHead>
                  <TableHead>Descripcion</TableHead>
                  <TableHead className="text-center">Productos</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBrands.map((brand) => (
                  <TableRow key={brand.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold">
                          {brand.name.charAt(0)}
                        </div>
                        <span className="font-medium">{brand.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {brand.description}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="secondary">{brand.productsCount}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={brand.is_active ? 'success' : 'secondary'}>
                        {brand.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenDialog(brand)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(brand.id)}
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

      {/* Brand Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingBrand ? 'Editar Marca' : 'Agregar Marca'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Haceb"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Descripcion</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripcion de la marca..."
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="logo">URL del Logo (opcional)</Label>
              <Input
                id="logo"
                value={formData.logo}
                onChange={(e) => setFormData({ ...formData, logo: e.target.value })}
                placeholder="https://ejemplo.com/logo.png"
              />
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
                Marca activa
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>
              {editingBrand ? 'Guardar cambios' : 'Crear marca'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
