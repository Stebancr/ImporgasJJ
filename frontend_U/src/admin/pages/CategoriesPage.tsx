import { useState, useEffect, useRef } from 'react'
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
import { Plus, Search, Edit, Trash2, FolderTree, Loader2 } from 'lucide-react'
import { categoriesService } from '@/admin/services/admin_categories'
import type { Category } from '@/admin/types'

import { CategoryIcon, categoryIcons, resolveCategoryIcon } from '@/components/CategoryIcon'
import { CategoryIconPicker } from '@/components/CategoryIconPicker'
import { isAxiosError } from 'axios'


const toSlug = (name: string) =>
  name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const saving = useRef(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
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

  const fetchCategories = async () => {
    try {
      setIsLoading(true)
      const res = await categoriesService.getAll({ per_page: 100 })
      setCategories(res.data)
    } catch {
      setError('No se pudieron cargar las categorias')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchCategories() }, [])

  const filteredCategories = categories.filter((category) =>
    category.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleOpenDialog = (category?: Category) => {
    setError(null)
    setFieldErrors({})
    if (category) {
      setEditingCategory(category)
      setFormData({
        name: category.name,
        description: category.description,
        icon: resolveCategoryIcon(category.slug, category.icon, category.icon_key) || 'flame',
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

  const handleSave = async () => {
    if (saving.current) return
    if (!formData.name.trim()) {
      setFieldErrors({name: 'El nombre es requerido'})
      return
    }
    if (!Object.prototype.hasOwnProperty.call(categoryIcons, formData.icon)) {
      setFieldErrors({icon_key: 'Selecciona un icono disponible.'})
      return
    }
    setFieldErrors({})
    saving.current = true
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        name: formData.name.trim(),
        slug: editingCategory?.slug || toSlug(formData.name),
        description: formData.description.trim(),
        icon: editingCategory?.icon || formData.icon,
        icon_key: formData.icon,
        order: parseInt(formData.order) || 0,
        is_active: formData.is_active,
      }
      if (editingCategory) {
        await categoriesService.update(editingCategory.id, payload)
      } else {
        await categoriesService.create(payload)
      }
      setIsDialogOpen(false)
      await fetchCategories()
    } catch (caught) {
      const data = isAxiosError(caught) ? caught.response?.data : undefined
      const fields: Record<string, string> = {}
      for (const key of ['name', 'slug', 'icon_key']) {
        const message = data?.[key]
        if (Array.isArray(message) && typeof message[0] === 'string') fields[key] = message[0].slice(0, 200)
      }
      setFieldErrors(fields)
      setError('No se pudo guardar la categoría. Revisa los campos e inténtalo de nuevo.')
    } finally {
      saving.current = false
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar esta categoría?')) return
    try {
      await categoriesService.delete(id)
      setCategories((prev) => prev.filter((c) => c.id !== id))
    } catch {
      alert('No se pudo eliminar la categoria')
    }
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
              {!isLoading && (
                <Badge variant="secondary">{filteredCategories.length}</Badge>
              )}
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar categorias..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
               aria-label="Buscar categorias..." />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Categoria</TableHead>
                    <TableHead>Descripcion</TableHead>
                    <TableHead className="text-center">Orden</TableHead>
                    <TableHead className="text-center">Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCategories.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                        No hay categorias registradas
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredCategories.map((category) => (
                      <TableRow key={category.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                              <CategoryIcon iconKey={category.icon_key} slug={category.slug} name={category.icon} className="h-5 w-5" />
                            </div>
                            <span className="font-medium">{category.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-muted-foreground">
                          {category.description}
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
                             aria-label="Editar">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(category.id)}
                             aria-label="Eliminar">
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

      {/* Category Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent aria-describedby={undefined} className="max-h-[90dvh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {editingCategory ? 'Editar Categoria' : 'Agregar Categoria'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                aria-invalid={Boolean(fieldErrors.name)} aria-describedby={fieldErrors.name ? 'category-name-error' : undefined} placeholder="Ej: Calentadores"
              />
              {fieldErrors.name && <p id="category-name-error" role="alert" className="text-sm text-destructive">{fieldErrors.name}</p>}
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CategoryIconPicker value={formData.icon} onChange={icon => setFormData({ ...formData, icon })} error={fieldErrors.icon_key} />
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
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSaving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingCategory ? 'Guardar cambios' : 'Crear categoria'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
