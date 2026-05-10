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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Search, Edit, Trash2, Package } from 'lucide-react'

interface Product {
  id: number
  name: string
  slug: string
  description: string
  price: number
  original_price: number | null
  category: string
  brand: string
  total_stock: number
  is_available: boolean
  is_featured: boolean
  rating: number
}

const mockProducts: Product[] = [
  {
    id: 1,
    name: 'Calentador de Paso Haceb 10L',
    slug: 'calentador-haceb-10l',
    description: 'Calentador de paso a gas natural, 10 litros por minuto',
    price: 450000,
    original_price: 500000,
    category: 'Calentadores',
    brand: 'Haceb',
    total_stock: 15,
    is_available: true,
    is_featured: true,
    rating: 4.5,
  },
  {
    id: 2,
    name: 'Regulador de Gas Fisher',
    slug: 'regulador-gas-fisher',
    description: 'Regulador de gas para cilindros de 40 y 100 libras',
    price: 35000,
    original_price: null,
    category: 'Reguladores de Gas',
    brand: 'Fisher',
    total_stock: 50,
    is_available: true,
    is_featured: false,
    rating: 4.8,
  },
  {
    id: 3,
    name: 'Aire Acondicionado Samsung 12000 BTU',
    slug: 'aire-samsung-12000',
    description: 'Aire acondicionado inverter, alta eficiencia energetica',
    price: 1850000,
    original_price: 2100000,
    category: 'Aires Acondicionados',
    brand: 'Samsung',
    total_stock: 8,
    is_available: true,
    is_featured: true,
    rating: 4.7,
  },
  {
    id: 4,
    name: 'Kit Instalacion Gas',
    slug: 'kit-instalacion-gas',
    description: 'Kit completo para instalacion de gas domiciliario',
    price: 85000,
    original_price: null,
    category: 'Herramientas e Instalacion',
    brand: 'Stanley',
    total_stock: 25,
    is_available: true,
    is_featured: false,
    rating: 4.3,
  },
]

const categories = ['Calentadores', 'Aires Acondicionados', 'Reguladores de Gas', 'Herramientas e Instalacion']
const brands = ['Haceb', 'Samsung', 'LG', 'Fisher', 'Stanley', 'Bosch', 'Challenger', 'Coltgas']

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>(mockProducts)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    original_price: '',
    category: '',
    brand: '',
    total_stock: '',
    is_available: true,
    is_featured: false,
  })

  const filteredProducts = products.filter(
    (product) =>
      product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.brand.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const handleOpenDialog = (product?: Product) => {
    if (product) {
      setEditingProduct(product)
      setFormData({
        name: product.name,
        description: product.description,
        price: product.price.toString(),
        original_price: product.original_price?.toString() || '',
        category: product.category,
        brand: product.brand,
        total_stock: product.total_stock.toString(),
        is_available: product.is_available,
        is_featured: product.is_featured,
      })
    } else {
      setEditingProduct(null)
      setFormData({
        name: '',
        description: '',
        price: '',
        original_price: '',
        category: '',
        brand: '',
        total_stock: '',
        is_available: true,
        is_featured: false,
      })
    }
    setIsDialogOpen(true)
  }

  const handleSave = () => {
    if (editingProduct) {
      setProducts(products.map((p) =>
        p.id === editingProduct.id
          ? {
              ...p,
              name: formData.name,
              slug: formData.name.toLowerCase().replace(/ /g, '-'),
              description: formData.description,
              price: parseFloat(formData.price),
              original_price: formData.original_price ? parseFloat(formData.original_price) : null,
              category: formData.category,
              brand: formData.brand,
              total_stock: parseInt(formData.total_stock),
              is_available: formData.is_available,
              is_featured: formData.is_featured,
            }
          : p
      ))
    } else {
      const newProduct: Product = {
        id: Math.max(...products.map((p) => p.id)) + 1,
        name: formData.name,
        slug: formData.name.toLowerCase().replace(/ /g, '-'),
        description: formData.description,
        price: parseFloat(formData.price),
        original_price: formData.original_price ? parseFloat(formData.original_price) : null,
        category: formData.category,
        brand: formData.brand,
        total_stock: parseInt(formData.total_stock),
        is_available: formData.is_available,
        is_featured: formData.is_featured,
        rating: 0,
      }
      setProducts([...products, newProduct])
    }
    setIsDialogOpen(false)
  }

  const handleDelete = (id: number) => {
    if (confirm('Esta seguro de eliminar este producto?')) {
      setProducts(products.filter((p) => p.id !== id))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Productos</h1>
          <p className="text-muted-foreground">Administra el catalogo de productos</p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Producto
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Lista de Productos
            </CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar productos..."
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
                  <TableHead>Producto</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead className="text-right">Precio</TableHead>
                  <TableHead className="text-center">Stock</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{product.name}</p>
                        {product.is_featured && (
                          <Badge variant="secondary" className="mt-1">Destacado</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{product.category}</TableCell>
                    <TableCell>{product.brand}</TableCell>
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
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenDialog(product)}
                        >
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
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Product Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProduct ? 'Editar Producto' : 'Agregar Producto'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre del producto</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Calentador de Paso 10L"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Descripcion</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripcion del producto..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="price">Precio</Label>
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
                <Label htmlFor="category">Categoria</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar categoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat} value={cat}>
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="brand">Marca</Label>
                <Select
                  value={formData.brand}
                  onValueChange={(value) => setFormData({ ...formData, brand: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar marca" />
                  </SelectTrigger>
                  <SelectContent>
                    {brands.map((brand) => (
                      <SelectItem key={brand} value={brand}>
                        {brand}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="total_stock">Stock total</Label>
              <Input
                id="total_stock"
                type="number"
                value={formData.total_stock}
                onChange={(e) => setFormData({ ...formData, total_stock: e.target.value })}
                placeholder="100"
              />
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
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>
              {editingProduct ? 'Guardar cambios' : 'Crear producto'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
