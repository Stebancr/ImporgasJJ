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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Search, Edit, Trash2, Package, Upload, X } from 'lucide-react'
import { productsService } from '@/admin/services/products'
import type { CreateProductData } from '@/admin/services/products'
import { brandsService } from '@/admin/services/brands'
import { categoriesService } from '@/admin/services/categories'
import { locationsService } from '@/admin/services/locations'
import api from '@/admin/services/api'
import type { Product, Brand, Category, ProductSpec, Location } from '@/admin/types'

interface FormData {
  name: string
  description: string
  price: string
  original_price: string
  category: string
  brand: string
  is_available: boolean
  is_featured: boolean
}

const defaultForm: FormData = {
  name: '',
  description: '',
  price: '',
  original_price: '',
  category: '',
  brand: '',
  is_available: true,
  is_featured: false,
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoadingProduct, setIsLoadingProduct] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [formData, setFormData] = useState<FormData>(defaultForm)

  // Image upload state
  const [imageFiles, setImageFiles] = useState<File[]>([])
  const [imagePreviews, setImagePreviews] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Spec state
  const [existingSpecs, setExistingSpecs] = useState<ProductSpec[]>([])
  const [newSpecRows, setNewSpecRows] = useState<{ name: string; value: string }[]>([])

  // Stock state: locationId -> quantity string
  const [stockValues, setStockValues] = useState<Record<number, string>>({})

  const PER_PAGE = 20

  const fetchProducts = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await productsService.getAll({
        search: searchTerm || undefined,
        page,
        per_page: PER_PAGE,
      })
      setProducts(res.data)
      setTotal(res.total)
    } catch {
      setError('Error al cargar los productos')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts()
  }, [searchTerm, page])

  useEffect(() => {
    brandsService.getAll({ is_active: true, per_page: 100 }).then(r => setBrands(r.data)).catch(() => {})
    categoriesService.getAll({ is_active: true, per_page: 100 }).then(r => setCategories(r.data)).catch(() => {})
    locationsService.getAll({ is_active: true, per_page: 100 }).then(r => setLocations(r.data)).catch(() => {})
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setImageFiles(prev => [...prev, ...files])
    const previews = files.map(f => URL.createObjectURL(f))
    setImagePreviews(prev => [...prev, ...previews])
  }

  const removeImage = (index: number) => {
    URL.revokeObjectURL(imagePreviews[index])
    setImageFiles(prev => prev.filter((_, i) => i !== index))
    setImagePreviews(prev => prev.filter((_, i) => i !== index))
  }

  const handleOpenDialog = async (product?: Product) => {
    setImageFiles([])
    setImagePreviews([])
    setExistingSpecs([])
    setNewSpecRows([])
    setStockValues({})
    setError(null)
    if (product) {
      setEditingProduct(product)
      setFormData(defaultForm)
      setIsDialogOpen(true)
      setIsLoadingProduct(true)
      try {
        const [full, stockEntries] = await Promise.all([
          productsService.getById(product.id),
          productsService.getStock(product.id),
        ])
        setEditingProduct(full)
        setFormData({
          name: full.name,
          description: full.description ?? '',
          price: full.price.toString(),
          original_price: full.original_price?.toString() ?? '',
          category: full.category_id.toString(),
          brand: full.brand_id.toString(),
          is_available: full.is_available,
          is_featured: full.is_featured,
        })
        setExistingSpecs(full.specifications ?? [])
        const stockMap: Record<number, string> = {}
        stockEntries.forEach(s => { stockMap[s.location_id] = s.quantity.toString() })
        setStockValues(stockMap)
      } catch {
        setError('Error al cargar los datos del producto')
      } finally {
        setIsLoadingProduct(false)
      }
    } else {
      setEditingProduct(null)
      setFormData(defaultForm)
      setIsDialogOpen(true)
    }
  }

  const handleSave = async () => {
    if (!formData.name || !formData.price || !formData.category || !formData.brand) {
      setError('Completa los campos obligatorios: nombre, precio, categorÃ­a y marca')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        price: parseFloat(formData.price),
        original_price: formData.original_price ? parseFloat(formData.original_price) : undefined,
        category: parseInt(formData.category),
        brand: parseInt(formData.brand),
        is_available: formData.is_available,
        is_featured: formData.is_featured,
      }

      let savedProduct: Product
      if (editingProduct) {
        savedProduct = await productsService.update(editingProduct.id, payload as Partial<CreateProductData>)
      } else {
        savedProduct = await productsService.create(payload as CreateProductData)
      }

      // Upload images one by one
      for (let i = 0; i < imageFiles.length; i++) {
        await productsService.addImage(savedProduct.id, imageFiles[i], i === 0 && !editingProduct)
      }

      // Save new specs
      const specErrors: string[] = []
      for (const row of newSpecRows.filter(r => r.name.trim() && r.value.trim())) {
        try {
          const attrRes = await api.post<{ id: number } | { data: { id: number } }>('/spec-attributes', { name: row.name.trim() })
          const attrData = attrRes.data as { data?: { id: number }; id?: number }
          const attrId = attrData.data?.id ?? attrData.id
          if (attrId) await productsService.addSpec(savedProduct.id, attrId, row.value.trim())
          else specErrors.push(row.name)
        } catch {
          specErrors.push(row.name)
        }
      }
      if (specErrors.length > 0) {
        setError(`No se guardaron algunas especificaciones: ${specErrors.join(', ')}`)
      }

      // Save stock per location
      for (const [locIdStr, qtyStr] of Object.entries(stockValues)) {
        const qty = parseInt(qtyStr)
        if (!isNaN(qty) && qty >= 0) {
          await productsService.upsertStock(savedProduct.id, parseInt(locIdStr), qty)
        }
      }

      setIsDialogOpen(false)
      await fetchProducts()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string; error?: string } } })?.response?.data
      setError(msg?.detail || msg?.error || 'Error al guardar el producto')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Â¿EstÃ¡ seguro de eliminar este producto?')) return
    try {
      await productsService.delete(id)
      await fetchProducts()
    } catch {
      setError('Error al eliminar el producto')
    }
  }

  const handleDeleteExistingImage = async (imageId: number) => {
    if (!editingProduct) return
    try {
      await productsService.deleteImage(editingProduct.id, imageId)
      setEditingProduct(prev =>
        prev ? { ...prev, images: prev.images?.filter(img => img.id !== imageId) } : null
      )
    } catch {
      setError('Error al eliminar la imagen')
    }
  }

  const handleDeleteSpec = async (specId: number) => {
    if (!editingProduct) return
    try {
      await productsService.deleteSpec(editingProduct.id, specId)
      setExistingSpecs(prev => prev.filter(s => s.id !== specId))
    } catch {
      setError('Error al eliminar la especificaciÃ³n')
    }
  }


  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(price)

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Productos</h1>
          <p className="text-muted-foreground">Administra el catÃ¡logo de productos</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Producto
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
              <Package className="h-5 w-5" />
              Lista de Productos
              <Badge variant="secondary">{total}</Badge>
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar productos..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setPage(1) }}
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
                    <TableHead>Producto</TableHead>
                    <TableHead>categorÃ­a</TableHead>
                    <TableHead>Marca</TableHead>
                    <TableHead className="text-right">Precio</TableHead>
                    <TableHead className="text-center">Stock</TableHead>
                    <TableHead className="text-center">Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                        No hay productos
                      </TableCell>
                    </TableRow>
                  ) : (
                    products.map((product) => (
                      <TableRow key={product.id}>
                        <TableCell>
                          <p className="font-medium">{product.name}</p>
                          {product.is_featured && (
                            <Badge variant="secondary" className="mt-1">Destacado</Badge>
                          )}
                        </TableCell>
                        <TableCell>{product.category_name || product.category?.name || 'â€”'}</TableCell>
                        <TableCell>{product.brand_name || product.brand?.name || 'â€”'}</TableCell>
                        <TableCell className="text-right">
                          <div>
                            <p className="font-medium">{formatPrice(product.price)}</p>
                            {product.original_price && (
                              <p className="text-sm text-muted-foreground line-through">
                                {formatPrice(product.original_price)}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant={product.total_stock > 10 ? 'success' : product.total_stock > 0 ? 'warning' : 'destructive'}
                          >
                            {product.total_stock}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant={product.is_available ? 'success' : 'secondary'}>
                            {product.is_available ? 'Disponible' : 'No disponible'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(product)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(product.id)}
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                PÃ¡gina {page} de {totalPages} ({total} productos)
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 1}>
                  Anterior
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page === totalPages}>
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Product Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>
              {editingProduct ? 'Editar Producto' : 'Agregar Producto'}
            </DialogTitle>
          </DialogHeader>
          {isLoadingProduct ? (
            <div className="py-12 text-center text-muted-foreground">Cargando datos del producto...</div>
          ) : (
            <>
            <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre del producto *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Calentador de Paso 10L"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">DescripciÃ³n</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="DescripciÃ³n del producto..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="price">Precio *</Label>
                <Input
                  id="price"
                  type="number"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  placeholder="450000"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="original_price">Precio original (opcional)</Label>
                <Input
                  id="original_price"
                  type="number"
                  value={formData.original_price}
                  onChange={(e) => setFormData({ ...formData, original_price: e.target.value })}
                  placeholder="500000"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>CategorÃ­a *</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar categorÃ­a" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id.toString()}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Marca *</Label>
                <Select
                  value={formData.brand}
                  onValueChange={(value) => setFormData({ ...formData, brand: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar marca" />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((brand) => (
                      <SelectItem key={brand.id} value={brand.id.toString()}>
                        {brand.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Specifications */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label>Especificaciones del producto</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setNewSpecRows(prev => [...prev, { name: '', value: '' }])}
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Agregar
                </Button>
              </div>
              {existingSpecs.length > 0 && (
                <div className="rounded-md border overflow-hidden text-sm">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-muted-foreground">CaracterÃ­stica</th>
                        <th className="text-left px-3 py-2 font-medium text-muted-foreground">Valor</th>
                        <th className="w-8" />
                      </tr>
                    </thead>
                    <tbody>
                      {existingSpecs.map(spec => (
                        <tr key={spec.id} className="border-t">
                          <td className="px-3 py-2 text-muted-foreground">
                            {spec.attribute_name}{spec.attribute_unit ? ` (${spec.attribute_unit})` : ''}
                          </td>
                          <td className="px-3 py-2 font-medium">{spec.value}</td>
                          <td className="px-2 py-2">
                            <button
                              type="button"
                              onClick={() => handleDeleteSpec(spec.id)}
                              className="h-6 w-6 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {newSpecRows.map((row, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input
                    placeholder="CaracterÃ­stica (ej: Capacidad)"
                    value={row.name}
                    onChange={e => setNewSpecRows(prev => prev.map((r, j) => j === i ? { ...r, name: e.target.value } : r))}
                    className="flex-1"
                  />
                  <Input
                    placeholder="Valor (ej: 13 litros)"
                    value={row.value}
                    onChange={e => setNewSpecRows(prev => prev.map((r, j) => j === i ? { ...r, value: e.target.value } : r))}
                    className="flex-1"
                  />
                  <button
                    type="button"
                    onClick={() => setNewSpecRows(prev => prev.filter((_, j) => j !== i))}
                    className="h-8 w-8 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors flex-shrink-0"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {newSpecRows.length === 0 && existingSpecs.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Agrega las caracterÃ­sticas del producto (marca, modelo, capacidad, etc.)
                </p>
              )}
            </div>

            {/* Stock per location */}
            {locations.length > 0 && (
              <div className="grid gap-2">
                <Label>Stock por sede</Label>
                <div className="rounded-md border overflow-hidden text-sm">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-muted-foreground">Sede</th>
                        <th className="text-left px-3 py-2 font-medium text-muted-foreground">Ciudad</th>
                        <th className="px-3 py-2 font-medium text-muted-foreground w-32">Cantidad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {locations.map(loc => (
                        <tr key={loc.id} className="border-t">
                          <td className="px-3 py-2 font-medium">{loc.name}</td>
                          <td className="px-3 py-2 text-muted-foreground">{loc.city}</td>
                          <td className="px-3 py-2">
                            <Input
                              type="number"
                              min="0"
                              className="h-7 w-24 text-sm"
                              placeholder="0"
                              value={stockValues[loc.id] ?? ''}
                              onChange={e => setStockValues(prev => ({ ...prev, [loc.id]: e.target.value }))}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Image upload */}
            <div className="grid gap-2">
              <Label>ImÃ¡genes del producto</Label>              <div
                className="border-2 border-dashed rounded-lg p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <Upload className="h-8 w-8" />
                  <p className="text-sm">Haz clic para seleccionar ImÃ¡genes</p>
                  <p className="text-xs">PNG, JPG, WEBP (mÃºltiples)</p>
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
              {imagePreviews.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {imagePreviews.map((preview, index) => (
                    <div key={index} className="relative">
                      <img
                        src={preview}
                        alt={`Preview ${index + 1}`}
                        className="h-20 w-20 object-cover rounded border"
                      />
                      {index === 0 && (
                        <span className="absolute bottom-0 left-0 right-0 bg-primary/80 text-primary-foreground text-xs text-center py-0.5 rounded-b">
                          Principal
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {editingProduct && editingProduct.images && editingProduct.images.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">ImÃ¡genes actuales:</p>
                  <div className="flex flex-wrap gap-2">
                    {editingProduct.images.map((img) => (
                      <div key={img.id} className="relative">
                        <img
                          src={img.image_url || img.image}
                          alt={img.alt_text || 'imagen'}
                          className={`h-16 w-16 object-cover rounded border-2 ${img.is_primary ? 'border-primary' : 'border-muted'}`}
                        />
                        {img.is_primary && (
                          <span className="absolute bottom-0 left-0 right-0 bg-primary/80 text-primary-foreground text-xs text-center py-0.5 rounded-b">
                            Principal
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteExistingImage(img.id)}
                          className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_available}
                  onChange={(e) => setFormData({ ...formData, is_available: e.target.checked })}
                  className="h-4 w-4 rounded border-input"
                />
                <span className="text-sm">Disponible</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_featured}
                  onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
                  className="h-4 w-4 rounded border-input"
                />
                <span className="text-sm">Producto destacado</span>
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSaving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Guardando...' : editingProduct ? 'Guardar cambios' : 'Crear producto'}
            </Button>
          </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

