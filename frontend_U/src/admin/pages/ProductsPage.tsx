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
import { productsService } from '@/admin/services/admin_products'

import { brandsService } from '@/admin/services/admin_brands'
import { categoriesService } from '@/admin/services/admin_categories'
import { locationsService } from '@/admin/services/admin_locations'

import { clearProductDraft, productDraftKey, readDraftImages, readProductDraft, saveDraftImages, saveProductDraft } from '@/admin/services/product_draft'
import type { Product, Brand, Category, ProductSpec, Location } from '@/admin/types'
import ProductDescription from '@/components/ProductDescription'
import ShippingProfileFields from '@/components/ShippingProfileFields'
import { emptyShippingProfile, type ShippingProfile } from '@/services/shipping'
import { useShippingConfig } from '@/hooks/useShippingConfig'

interface FormData {
  shipping_profile?: ShippingProfile
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
  shipping_profile: { ...emptyShippingProfile, declared_value_from_price: true },
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
  const imageBusy = false
  const [gallery, setGallery] = useState<{id?:number;file?:number;url:string;alt_text:string}[]>([])
  const [primary, setPrimary] = useState(0)
  const [fieldErrors, setFieldErrors] = useState<Record<string,string>>({})
  const errorRef = useRef<HTMLDivElement>(null)
  const saveLock = useRef(false)
  const operation = useRef<{key:string;fingerprint:string}>({ key: crypto.randomUUID(), fingerprint: '' })
  const [confirmClose, setConfirmClose] = useState(false)
  const closeEditor = () => { if (!saveLock.current) setConfirmClose(true) }
  const showErrors = (errors:Record<string,string>) => {
    setFieldErrors(errors)
    setError('Revisa los campos indicados. Tus cambios se conservan.')
    requestAnimationFrame(() => { const target=document.querySelector<HTMLElement>('[role="dialog"] [aria-invalid="true"]'); (target??errorRef.current)?.focus(); (target??errorRef.current)?.scrollIntoView({block:'nearest'}) })
  }
  const [imageError, setImageError] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [brands, setBrands] = useState<Brand[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [shippingFilter, setShippingFilter] = useState<'' | 'complete' | 'incomplete'>('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoadingProduct, setIsLoadingProduct] = useState(false)
  const [editorReady, setEditorReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [draftReady, setDraftReady] = useState(false)
  const [draftRestored, setDraftRestored] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [formData, setFormData] = useState<FormData>(defaultForm)
  const {enabled:tccEnabled}=useShippingConfig()
  const initialShipping=useRef(JSON.stringify(defaultForm.shipping_profile))

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
        shipping_status: shippingFilter || undefined,
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
  }, [searchTerm, page, shippingFilter])

  useEffect(() => {
    brandsService.getAll({ is_active: true, per_page: 100 }).then(r => setBrands(r.data)).catch(() => {})
    categoriesService.getAll({ is_active: true, per_page: 100 }).then(r => setCategories(r.data)).catch(() => {})
    locationsService.getAll({ is_active: true, per_page: 100 }).then(r => setLocations(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!isDialogOpen || editingProduct || !draftReady) return
    const key = productDraftKey()
    saveProductDraft(key, { formData, newSpecRows, stockValues, operationKey:operation.current.key,
      gallery:gallery.filter(item=>item.file!==undefined).map(item=>({file:item.file!,alt_text:item.alt_text})),primary })
  }, [isDialogOpen, editingProduct, draftReady, formData, newSpecRows, stockValues, gallery, primary])

  useEffect(() => {
    if (!isDialogOpen || editingProduct || !draftReady) return
    void saveDraftImages(productDraftKey(), imageFiles)
  }, [isDialogOpen, editingProduct, draftReady, imageFiles])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (files.some(file => !['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 5*1024*1024)) {
      setImageError('Usa imágenes JPG, PNG o WebP de hasta 5 MB por archivo.'); return
    }
    const activeFiles=gallery.filter(item=>item.file!==undefined).map(item=>imageFiles[item.file!])
    const unique = files.filter((file,index) => ![...activeFiles,...files.slice(0,index)].some(other => other.name===file.name && other.size===file.size && other.lastModified===file.lastModified))
    if (gallery.length + unique.length > 30) { setImageError('Puedes guardar hasta 30 imágenes.'); return }
    setImageError('')
    const previews = unique.map(file=>URL.createObjectURL(file))
    setGallery(prev=>[...prev,...unique.map((_,index)=>({file:imageFiles.length+index,url:previews[index],alt_text:''}))])
    setImageFiles(prev=>[...prev,...unique])
    setImagePreviews(prev=>[...prev,...previews])
  }

  const removeGalleryImage = (index:number) => {
    setGallery(prev=>prev.filter((_,i)=>i!==index))
    setPrimary(prev=>prev===index?0:prev>index?prev-1:prev)
  }
  const moveImage = (index:number, direction:number) => {
    const target=index+direction
    if(target<0 || target>=gallery.length) return
    setGallery(prev=>{const next=[...prev]; [next[index],next[target]]=[next[target],next[index]]; return next})
    setPrimary(prev=>prev===index?target:prev===target?index:prev)
  }
  const handleOpenDialog = async (product?: Product) => {
    setEditorReady(false)
    setImageError('')
    setGallery([])
    setPrimary(0)
    setFieldErrors({})
    setConfirmClose(false)
    operation.current = {key:crypto.randomUUID(),fingerprint:''}
    setDraftReady(false)
    setDraftRestored(false)
    imagePreviews.forEach(URL.revokeObjectURL)
    setImageFiles([])
    setImagePreviews([])
    setExistingSpecs([])
    setNewSpecRows([])
    setStockValues({})
    setError(null)
    if (product) {
      setEditingProduct(product)
      initialShipping.current=JSON.stringify(emptyShippingProfile)
      setFormData(defaultForm)
      setIsDialogOpen(true)
      setIsLoadingProduct(true)
      try {
        const [full, stockEntries] = await Promise.all([
          productsService.getById(product.id),
          productsService.getStock(product.id),
        ])
        setEditingProduct(full)
        initialShipping.current=JSON.stringify(full.shipping_profile??emptyShippingProfile)
        setGallery((full.images??[]).map(img=>({id:img.id,url:img.image_url||img.image,alt_text:img.alt_text})))
        setPrimary(Math.max(0,(full.images??[]).findIndex(img=>img.is_primary)))
        setFormData({
          name: full.name,
          description: full.description ?? '',
          shipping_profile: full.shipping_profile ?? emptyShippingProfile,
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
        setEditorReady(true)
      } catch {
        setError('Error al cargar los datos del producto')
      } finally {
        setIsLoadingProduct(false)
      }
    } else {
      setEditingProduct(null)
      initialShipping.current=JSON.stringify(defaultForm.shipping_profile)
      const key = productDraftKey()
      const draft = readProductDraft(key)
      if(draft?.operationKey) operation.current.key=draft.operationKey
      setFormData(draft?.formData ?? defaultForm)
      setNewSpecRows(draft?.newSpecRows ?? [])
      setStockValues(draft?.stockValues ?? {})
      setDraftRestored(Boolean(draft))
      setIsLoadingProduct(true)
      setIsDialogOpen(true)
      const files = await readDraftImages(key)
      setImageFiles(files)
      const previews = files.map(file => URL.createObjectURL(file))
      setImagePreviews(previews)
      setGallery((draft?.gallery??files.map((_,index)=>({file:index,alt_text:''}))).filter(item=>files[item.file]).map(item=>({...item,url:previews[item.file]})))
      setPrimary(draft?.primary??0)
      setDraftReady(true)
      setEditorReady(true)
      setIsLoadingProduct(false)
    }
  }

  const handleSave = async () => {
    if(saveLock.current || !editorReady) return
    const errors:Record<string,string>={}
    if(!formData.name.trim()) errors.name='Escribe el nombre del producto.'
    if(!formData.category) errors.category='Selecciona una categoría.'
    if(!formData.brand) errors.brand='Selecciona una marca.'
    if(!Number.isFinite(Number(formData.price)) || Number(formData.price)<=0) errors.price='El precio debe ser mayor que cero.'
    if(formData.original_price && Number(formData.original_price)<Number(formData.price)) errors.original_price='Debe ser mayor o igual al precio de venta.'
    const shipping=formData.shipping_profile??emptyShippingProfile
    const sendShipping=JSON.stringify(shipping)!==initialShipping.current||(!editingProduct&&tccEnabled===true)
    if(sendShipping){
      if(!Number.isInteger(shipping.packages_per_unit)||Number(shipping.packages_per_unit)<1||Number(shipping.packages_per_unit)>100) errors.shipping_profile='Indica entre 1 y 100 paquetes.'
      if(formData.is_available && shipping.requires_shipping){
        for(const field of ['weight_kg','height_cm','width_cm','length_cm',...(shipping.declared_value_from_price?[]:['declared_value'])] as const){
          const value=shipping[field as keyof ShippingProfile]
          if(!value||!Number.isFinite(Number(value))||Number(value)<=0) errors[`shipping_profile.${field}`]='Ingresa un valor mayor que cero.'
        }
      }
    }
    if(Object.values(stockValues).some(value=>value!==''&&(!/^\d+$/.test(value)||Number(value)>2147483647))) errors.stocks='Las existencias deben ser números enteros no negativos.'
    if(newSpecRows.some(row=>!row.name.trim()||!row.value.trim())) errors.specs='Completa o elimina las características vacías.'
    if(Object.keys(errors).length){showErrors(errors);return}
    saveLock.current=true
    setIsSaving(true);setError(null);setFieldErrors({})
    try {
      const files=gallery.filter(item=>item.file!==undefined).map(item=>imageFiles[item.file!])
      let upload=0
      const payload={
        product:{...formData,price:formData.price,original_price:formData.original_price||null,
          category:Number(formData.category),brand:Number(formData.brand),shipping_profile:sendShipping?shipping:undefined},
        updated_at:editingProduct?.updated_at,
        images:gallery.map(item=>({... (item.id?{id:item.id}:{file:`upload_${upload++}`}),alt_text:item.alt_text})),
        primary:gallery.length?primary:null,
        stocks:Object.entries(stockValues).filter(([,value])=>value!=='').map(([location,quantity])=>({location:Number(location),quantity:Number(quantity)})),
        specs:[...existingSpecs.map(spec=>({id:spec.id,value:spec.value})),...newSpecRows.map(row=>({name:row.name.trim(),value:row.value.trim()}))],
      }
      const fingerprint=JSON.stringify(payload)+files.map(file=>`${file.name}:${file.size}:${file.lastModified}`).join('|')
      operation.current.fingerprint=fingerprint
      await productsService.saveEditor(editingProduct?.id,{...payload,key:operation.current.key},files)
      if(!editingProduct){setDraftReady(false);await clearProductDraft(productDraftKey())}
      setIsDialogOpen(false)
      await fetchProducts()
    } catch(err:unknown) {
      const response=(err as {response?:{status?:number;data?:unknown}}).response
      const status=response?.status
      if(status===400 && response?.data && typeof response.data==='object') {
        operation.current={key:crypto.randomUUID(),fingerprint:''}
        if(!editingProduct) {
          const draft=readProductDraft(productDraftKey())
          if(draft) saveProductDraft(productDraftKey(),{...draft,operationKey:operation.current.key})
        }
        const flatten=(value:unknown):string=>typeof value==='string'?value:Array.isArray(value)?value.map(flatten).join(' '):value&&typeof value==='object'?Object.values(value).map(flatten).join(' '):''
        showErrors(Object.fromEntries(Object.entries(response.data).map(([key,value])=>[key,flatten(value)])))
      } else {
        setError(status===401?'Tu sesión caducó. Inicia sesión para guardar.':status===403?'No tienes permisos para guardar productos.':status===409?'El producto cambió o la solicitud ya fue utilizada. Conserva tus cambios y revisa la versión actual.':status===413?'Los archivos superan el tamaño permitido. Reduce su tamaño.':'No se pudo confirmar el guardado. Conservamos tus datos; reintenta sin cerrar el formulario.')
        requestAnimationFrame(()=>errorRef.current?.focus())
      }
    } finally {saveLock.current=false;setIsSaving(false)}
  }
  const handleDelete = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar este producto?')) return
    try {
      await productsService.delete(id)
      await fetchProducts()
    } catch {
      setError('Error al eliminar el producto')
    }
  }

  const handleDeleteSpec = (id:number) => setExistingSpecs(prev=>prev.filter(spec=>spec.id!==id))

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(price)

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))


  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Productos</h1>
          <p className="text-muted-foreground">Administra el catálogo de productos</p>
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
            <label className="text-sm">Configuración de envío
              <select aria-label="Filtrar configuración de envío" className="ml-2 rounded border p-2" value={shippingFilter} onChange={e=>{setShippingFilter(e.target.value as typeof shippingFilter);setPage(1)}}>
                <option value="">Todos</option><option value="complete">TCC completo</option><option value="incomplete">TCC incompleto</option>
              </select>
            </label>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar productos..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setPage(1) }}
                className="pl-9"
               aria-label="Buscar productos..." />
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
                    <TableHead>categoría</TableHead>
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
                          {product.shipping_ready === false && <button type="button" className="mt-1 block text-left focus-visible:outline focus-visible:outline-2" title={(product.shipping_missing_fields ?? []).join(', ')} aria-label={`Editar envío de ${product.name}: ${(product.shipping_missing_fields ?? []).join(', ')}`} onClick={()=>handleOpenDialog(product)}><Badge variant="warning">Faltan especificaciones de envío</Badge><span className="block text-xs text-muted-foreground">{product.shipping_missing_fields?.join(', ')}</span></button>}
                          {product.shipping_ready === true && <Badge variant="secondary" className="mt-1">Configuración de envío completa</Badge>}
                          {product.is_featured && (
                            <Badge variant="secondary" className="mt-1">Destacado</Badge>
                          )}
                        </TableCell>
                        <TableCell>{product.category_name || product.category?.name || '—'}</TableCell>
                        <TableCell>{product.brand_name || product.brand?.name || '—'}</TableCell>
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
                            <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(product)} aria-label="Editar">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(product.id)}
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Página {page} de {totalPages} ({total} productos)
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
      <Dialog open={isDialogOpen} onOpenChange={(open) => { if (open) setIsDialogOpen(true); else closeEditor() }}>
        <DialogContent
          className="max-w-3xl max-h-[90dvh] overflow-y-auto p-0 sm:p-0 [&>button]:z-30"
          aria-describedby={undefined}
          onPointerDownOutside={(event) => event.preventDefault()}
          onEscapeKeyDown={(event) => event.preventDefault()}
        >
          <DialogHeader className="sticky top-0 z-20 border-b bg-background px-6 py-4">
            <DialogTitle>
              {editingProduct ? 'Editar Producto' : 'Agregar Producto'}
            </DialogTitle>
          </DialogHeader>
          {!editingProduct && draftRestored && (
            <p className="text-sm text-muted-foreground">Se recuperó el borrador guardado en este navegador.</p>
          )}
          {error && <div ref={errorRef} tabIndex={-1} role="alert" className="mx-6 rounded border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"><p className="font-medium">{error}</p>{Object.entries(fieldErrors).map(([key,message])=><p key={key}>{message}</p>)}</div>}
          {confirmClose && <div role="alert" className="mx-6 rounded border p-4 space-y-3"><p>¿Cerrar el formulario? Los cambios no guardados de edición se descartarán.</p><div className="flex gap-2"><Button variant="outline" onClick={()=>setConfirmClose(false)}>Seguir editando</Button><Button variant="destructive" onClick={()=>{setConfirmClose(false);setIsDialogOpen(false)}}>Cerrar formulario</Button></div></div>}
          {isLoadingProduct ? (
            <div className="py-12 text-center text-muted-foreground">Cargando datos del producto...</div>
          ) : (
            <>
            <fieldset disabled={isSaving} className="grid min-w-0 gap-5 px-6 py-4"><h3 className="font-semibold">Información básica</h3>
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre del producto *</Label>
              <Input
                id="name" aria-invalid={!!fieldErrors.name} aria-describedby="name-error"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Calentador de Paso 10L"
              />{fieldErrors.name && <p id="name-error" className="text-sm text-destructive">{fieldErrors.name}</p>}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Descripción</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripción del producto..."
                rows={3}
                aria-describedby="description-help"
              />
              <p id="description-help" className="text-xs text-muted-foreground">Escribe cada característica en una línea nueva. Puedes comenzar la línea con * o -.</p>
              <details className="rounded border p-3 text-sm min-w-0">
                <summary className="cursor-pointer font-medium">Vista previa de la descripción</summary>
                <div className="mt-3"><ProductDescription text={formData.description} /></div>
              </details>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="price">Precio *</Label>
                <Input
                  id="price" aria-invalid={!!fieldErrors.price} aria-describedby="price-error"
                  type="number"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  placeholder="450000"
                />{fieldErrors.price && <p id="price-error" className="text-sm text-destructive">{fieldErrors.price}</p>}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="original_price">Precio original (opcional)</Label>
                <Input
                  id="original_price" aria-invalid={!!fieldErrors.original_price} aria-describedby="original_price-error"
                  type="number"
                  value={formData.original_price}
                  onChange={(e) => setFormData({ ...formData, original_price: e.target.value })}
                  placeholder="500000"
                />{fieldErrors.original_price && <p id="original_price-error" className="text-sm text-destructive">{fieldErrors.original_price}</p>}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Categoría *</Label>{fieldErrors.category && <p className="text-sm text-destructive">{fieldErrors.category}</p>}
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar categoría" />
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
                <Label>Marca *</Label>{fieldErrors.brand && <p className="text-sm text-destructive">{fieldErrors.brand}</p>}
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

            <ShippingProfileFields errors={fieldErrors} price={formData.price} value={formData.shipping_profile ?? emptyShippingProfile} onChange={shipping_profile=>setFormData({...formData,shipping_profile})}/>

            {fieldErrors.shipping_profile && <p className="text-sm text-destructive">{fieldErrors.shipping_profile}</p>}{fieldErrors.specs && <p className="text-sm text-destructive">{fieldErrors.specs}</p>}{/* Specifications */}
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
                        <th className="text-left px-3 py-2 font-medium text-muted-foreground">Característica</th>
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
                             aria-label="Cerrar">
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
                    placeholder="Característica (ej: Capacidad)"
                    value={row.name}
                    onChange={e => setNewSpecRows(prev => prev.map((r, j) => j === i ? { ...r, name: e.target.value } : r))}
                    className="flex-1"
                   aria-label="Característica (ej: Capacidad)" />
                  <Input
                    placeholder="Valor (ej: 13 litros)"
                    value={row.value}
                    onChange={e => setNewSpecRows(prev => prev.map((r, j) => j === i ? { ...r, value: e.target.value } : r))}
                    className="flex-1"
                   aria-label="Valor (ej: 13 litros)" />
                  <button
                    type="button"
                    onClick={() => setNewSpecRows(prev => prev.filter((_, j) => j !== i))}
                    className="h-8 w-8 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors flex-shrink-0"
                   aria-label="Cerrar">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {newSpecRows.length === 0 && existingSpecs.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Agrega las características del producto (marca, modelo, capacidad, etc.)
                </p>
              )}
            </div>

            <h3 className="font-semibold">Inventario por sede</h3>{fieldErrors.stocks && <p className="text-sm text-destructive">{fieldErrors.stocks}</p>}{/* Stock per location */}
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
                             aria-label="0" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <section className="space-y-3 min-w-0">
              <h3 className="font-semibold">Imágenes del producto</h3>
              <p className="text-sm text-muted-foreground">Selecciona la principal, ordena las imágenes y describe su contenido. Los cambios se aplican al guardar.</p>
              {(imageError||fieldErrors.images) && <p role="alert" className="text-sm text-destructive">{imageError||fieldErrors.images}</p>}
              <Button type="button" variant="outline" onClick={()=>fileInputRef.current?.click()}><Upload className="mr-2 h-4 w-4"/>Agregar imágenes</Button>
              <p className="text-xs text-muted-foreground">JPG, PNG o WebP · Máximo 5 MB por imagen · Hasta 30 imágenes</p>
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={handleFileSelect}/>
              <div className="grid grid-cols-1 min-[400px]:grid-cols-2 sm:grid-cols-3 gap-3">
                {gallery.map((item,index)=><div key={item.id?`saved-${item.id}`:`new-${item.file}`} className={`rounded-lg border p-3 space-y-2 min-w-0 ${index===primary?'border-primary bg-primary/5':''}`}>
                  <button type="button" className="w-full rounded focus-visible:ring-2 focus-visible:ring-primary" aria-pressed={primary===index} aria-label={`Usar imagen ${index+1} como principal`} onClick={()=>setPrimary(index)}><img src={item.url} alt={item.alt_text||`Imagen ${index+1}`} className="h-28 w-full object-contain"/><span className="text-xs">{primary===index?'Principal':'Elegir como principal'}</span></button>
                  <Input maxLength={255} aria-label={`Descripción de imagen ${index+1}`} placeholder="Texto alternativo" value={item.alt_text} onChange={event=>setGallery(prev=>prev.map((image,i)=>i===index?{...image,alt_text:event.target.value}:image))}/>
                  <div className="flex gap-1"><Button type="button" variant="outline" size="sm" disabled={index===0} aria-label={`Mover imagen ${index+1} antes`} onClick={()=>moveImage(index,-1)}>←</Button><Button type="button" variant="outline" size="sm" disabled={index===gallery.length-1} aria-label={`Mover imagen ${index+1} después`} onClick={()=>moveImage(index,1)}>→</Button><Button type="button" variant="ghost" size="sm" aria-label={`Eliminar imagen ${index+1}`} onClick={()=>removeGalleryImage(index)}><Trash2 className="h-4 w-4"/></Button></div>
                </div>)}
              </div>
            </section>
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
          </fieldset>
          <DialogFooter className="sticky bottom-0 z-20 border-t bg-background px-6 py-4">
            <Button variant="outline" onClick={closeEditor} disabled={isSaving || imageBusy}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={isSaving || imageBusy || !editorReady}>
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

