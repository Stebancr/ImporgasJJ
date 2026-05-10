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
import { Plus, Search, Edit, Trash2, FolderTree, Flame, Wind, Gauge, Wrench } from 'lucide-react'

interface Category {
  id: number
  name: string
  slug: string
  icon: string
  description: string
  order: number
  is_active: boolean
  productsCount: number
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  flame: Flame,
  wind: Wind,
  gauge: Gauge,
  wrench: Wrench,
}

const mockCategories: Category[] = [
  {
    id: 1,
    name: 'Calentadores',
    slug: 'calentadores',
    icon: 'flame',
    description: 'Calentadores de agua a gas y electricos',
    order: 1,
    is_active: true,
    productsCount: 45,
  },
  {
    id: 2,
    name: 'Aires Acondicionados',
    slug: 'aires',
    icon: 'wind',
    description: 'Aires acondicionados split e inverter',
    order: 2,
    is_active: true,
    productsCount: 32,
  },
  {
    id: 3,
    name: 'Reguladores de Gas',
    slug: 'reguladores',
    icon: 'gauge',
    description: 'Reguladores y valvulas de gas',
    order: 3,
    is_active: true,
    productsCount: 28,
  },
  {
    id: 4,
    name: 'Herramientas e Instalacion',
    slug: 'herramientas',
    icon: 'wrench',
    description: 'Herramientas y kits de instalacion',
    order: 4,
    is_active: true,
    productsCount: 51,
  },
]

const availableIcons = [
  { value: 'flame', label: 'Llama' },
  { value: 'wind', label: 'Viento' },
  { value: 'gauge', label: 'Medidor' },
  { value: 'wrench', label: 'Herramienta' },
]

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>(mockCategories)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    icon: 'flame',
    order: '',
    is_active: true,
  })

  const filteredCategories = categories.filter((category) =>
    category.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleOpenDialog = (category?: Category) => {
    if (category) {
      setEditingCategory(category)
      setFormData({
        name: category.name,
        description: category.description,
        icon: category.icon,
        order: category.order.toString(),
        is_active: category.is_active,
      })
    } else {
      setEditingCategory(null)
      setFormData({
        name: '',
        description: '',
        icon: 'flame',
        order: (categories.length + 1).toString(),
        is_active: true,
      })
    }
    setIsDialogOpen(true)
  }

  const handleSave = () => {
    if (editingCategory) {
      setCategories(categories.map((c) =>
        c.id === editingCategory.id
          ? {
              ...c,
              name: formData.name,
              slug: formData.name.toLowerCase().replace(/ /g, '-'),
              description: formData.description,
              icon: formData.icon,
              order: parseInt(formData.order),
              is_active: formData.is_active,
            }
          : c
      ))
    } else {
      const newCategory: Category = {
        id: Math.max(...categories.map((c) => c.id)) + 1,
        name: formData.name,
        slug: formData.name.toLowerCase().replace(/ /g, '-'),
        description: formData.description,
        icon: formData.icon,
        order: parseInt(formData.order),
        is_active: formData.is_active,
        productsCount: 0,
      }
      setCategories([...categories, newCategory])
    }
    setIsDialogOpen(false)
  }

  const handleDelete = (id: number) => {
    if (confirm('Esta seguro de eliminar esta categoria?')) {
      setCategories(categories.filter((c) => c.id !== id))
    }
  }

  const renderIcon = (iconName: string) => {
    const IconComponent = iconMap[iconName] || Flame
    return <IconComponent className="h-5 w-5" />
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Categorias</h1>
          <p className="text-muted-foreground">Administra las categorias de productos</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Categoria
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <FolderTree className="h-5 w-5" />
              Lista de Categorias
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar categorias..."
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
                  <TableHead>Categoria</TableHead>
                  <TableHead>Descripcion</TableHead>
                  <TableHead className="text-center">Productos</TableHead>
                  <TableHead className="text-center">Orden</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCategories.map((category) => (
                  <TableRow key={category.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg text-primary">
                          {renderIcon(category.icon)}
                        </div>
                        <span className="font-medium">{category.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {category.description}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="secondary">{category.productsCount}</Badge>
                    </TableCell>
                    <TableCell className="text-center">{category.order}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={category.is_active ? 'success' : 'secondary'}>
                        {category.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenDialog(category)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDelete(category.id)}
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

      {/* Category Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingCategory ? 'Editar Categoria' : 'Agregar Categoria'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Calentadores"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Descripcion</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripcion de la categoria..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="icon">Icono</Label>
                <select
                  id="icon"
                  value={formData.icon}
                  onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                >
                  {availableIcons.map((icon) => (
                    <option key={icon.value} value={icon.value}>
                      {icon.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="order">Orden</Label>
                <Input
                  id="order"
                  type="number"
                  value={formData.order}
                  onChange={(e) => setFormData({ ...formData, order: e.target.value })}
                  placeholder="1"
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
                Categoria activa
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>
              {editingCategory ? 'Guardar cambios' : 'Crear categoria'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
