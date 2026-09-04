import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/admin/context/AuthContext'
import { useLocation } from 'react-router-dom'
import { gestionService } from '@/admin/services/admin_gestion'
import type { StockEntry, Cotizacion, Factura, DocumentoItem } from '@/admin/services/admin_gestion'
import { productsService, locationsService } from '@/admin/services/admin_index'
import type { Location } from '@/admin/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Search, Plus, Eye, Trash2, FileCheck, Ban, Pencil,
  FileText, Receipt, ChevronLeft, ChevronRight,
  Loader2, AlertTriangle, RefreshCw, X, Boxes, ClipboardList,
} from 'lucide-react'

// â”€â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const fmt = (val: string | number) =>
  Number(val).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })

const COTIZACION_ESTADOS: Record<Cotizacion['estado'], { label: string; color: string }> = {
  borrador:   { label: 'Borrador',    color: 'bg-gray-100 text-gray-700' },
  enviada:    { label: 'Enviada',     color: 'bg-blue-100 text-blue-700' },
  aprobada:   { label: 'Aprobada',    color: 'bg-green-100 text-green-700' },
  rechazada:  { label: 'Rechazada',   color: 'bg-red-100 text-red-700' },
  vencida:    { label: 'Vencida',     color: 'bg-orange-100 text-orange-700' },
  convertida: { label: 'Convertida',  color: 'bg-purple-100 text-purple-700' },
}

const FACTURA_ESTADOS: Record<Factura['estado'], { label: string; color: string }> = {
  emitida: { label: 'Emitida', color: 'bg-green-100 text-green-700' },
  anulada: { label: 'Anulada', color: 'bg-red-100 text-red-700' },
}

// â”€â”€â”€ sub-components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function StatusBadge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}

function Pagination({
  page, totalPages, onPrev, onNext,
}: { page: number; totalPages: number; onPrev: () => void; onNext: () => void }) {
  return (
    <div className="flex items-center justify-end gap-2 mt-3">
      <Button variant="ghost" size="icon" disabled={page <= 1} onClick={onPrev}>
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <span className="text-sm text-muted-foreground">{page} / {totalPages}</span>
      <Button variant="ghost" size="icon" disabled={page >= totalPages} onClick={onNext}>
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  )
}

// â”€â”€â”€ Item editor (shared by Cotizacion + Factura forms) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface ItemEditorProps {
  items: DocumentoItem[]
  onChange: (items: DocumentoItem[]) => void
}

function ItemEditor({ items, onChange }: ItemEditorProps) {
  const [products, setProducts] = useState<{ id: number; name: string; price: number }[]>([])
  const [productSearch, setProductSearch] = useState('')
  const [loadingProducts, setLoadingProducts] = useState(false)

  useEffect(() => {
    setLoadingProducts(true)
    productsService.getAll({ search: productSearch || undefined, per_page: 20 } as never)
      .then((res: { data: { id: number; name: string; price: number }[] }) => setProducts(res.data))
      .catch(() => {})
      .finally(() => setLoadingProducts(false))
  }, [productSearch])

  const addItem = (product: { id: number; name: string; price: number }) => {
    const exists = items.find((i) => i.producto_id === product.id)
    if (exists) return
    onChange([
      ...items,
      {
        producto_id: product.id,
        producto_name: product.name,
        descripcion: product.name,
        cantidad: 1,
        precio_unitario: Number(product.price),
        descuento_item: 0,
      },
    ])
  }

  const updateItem = (idx: number, field: keyof DocumentoItem, value: string | number) => {
    const updated = items.map((item, i) =>
      i === idx ? { ...item, [field]: value } : item
    )
    onChange(updated)
  }

  const removeItem = (idx: number) => onChange(items.filter((_, i) => i !== idx))

  return (
    <div className="space-y-3">
      {/* Product search */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8 h-9"
            placeholder="Buscar producto..."
            value={productSearch}
            onChange={(e) => setProductSearch(e.target.value)}
          />
        </div>
        {loadingProducts && <Loader2 className="h-4 w-4 animate-spin self-center text-muted-foreground" />}
      </div>

      {productSearch && products.length > 0 && (
        <div className="border rounded-md max-h-36 overflow-y-auto">
          {products.map((p) => (
            <button
              key={p.id}
              type="button"
              className="w-full text-left flex items-center justify-between px-3 py-2 text-sm hover:bg-accent transition-colors"
              onClick={() => { addItem(p); setProductSearch('') }}
            >
              <span>{p.name}</span>
              <span className="text-muted-foreground">{fmt(p.price)}</span>
            </button>
          ))}
        </div>
      )}

      {/* Items table */}
      {items.length > 0 && (
        <div className="border rounded-md overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-3 py-2 font-medium">DescripciÃ³n</th>
                <th className="text-center px-3 py-2 font-medium w-20">Cant.</th>
                <th className="text-right px-3 py-2 font-medium w-32">Precio unit.</th>
                <th className="text-right px-3 py-2 font-medium w-28">Desc. $</th>
                <th className="text-right px-3 py-2 font-medium w-28">Subtotal</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const subtotal = item.precio_unitario * item.cantidad - (item.descuento_item || 0)
                return (
                  <tr key={idx} className="border-t">
                    <td className="px-3 py-1">
                      <Input
                        className="h-7 text-xs"
                        value={item.descripcion}
                        onChange={(e) => updateItem(idx, 'descripcion', e.target.value)}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <Input
                        type="number"
                        min={1}
                        className="h-7 text-xs text-center"
                        value={item.cantidad}
                        onChange={(e) => updateItem(idx, 'cantidad', Number(e.target.value))}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <Input
                        type="number"
                        min={0}
                        className="h-7 text-xs text-right"
                        value={item.precio_unitario}
                        onChange={(e) => updateItem(idx, 'precio_unitario', Number(e.target.value))}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <Input
                        type="number"
                        min={0}
                        className="h-7 text-xs text-right"
                        value={item.descuento_item}
                        onChange={(e) => updateItem(idx, 'descuento_item', Number(e.target.value))}
                      />
                    </td>
                    <td className="px-3 py-1 text-right font-medium text-xs">{fmt(subtotal)}</td>
                    <td className="px-1 py-1">
                      <button type="button" onClick={() => removeItem(idx)} className="text-destructive hover:opacity-70">
                        <X className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-3 border rounded-md border-dashed">
          Agrega al menos un producto
        </p>
      )}
    </div>
  )
}

// â”€â”€â”€ Document totals summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function TotalesForm({
  descuentoPct, impuestoPct, items,
  onDescuento, onImpuesto,
}: {
  descuentoPct: number
  impuestoPct: number
  items: DocumentoItem[]
  onDescuento: (v: number) => void
  onImpuesto: (v: number) => void
}) {
  const subtotal = items.reduce((s, i) => s + i.precio_unitario * i.cantidad - (i.descuento_item || 0), 0)
  const descMonto = (subtotal * descuentoPct) / 100
  const base = subtotal - descMonto
  const impMonto = (base * impuestoPct) / 100
  const total = base + impMonto

  return (
    <div className="space-y-2 text-sm">
      <div className="flex gap-4">
        <div className="flex-1">
          <Label className="text-xs">Descuento %</Label>
          <Input type="number" min={0} max={100} className="h-8 mt-1"
            value={descuentoPct} onChange={(e) => onDescuento(Number(e.target.value))} />
        </div>
        <div className="flex-1">
          <Label className="text-xs">Impuesto %</Label>
          <Input type="number" min={0} max={100} className="h-8 mt-1"
            value={impuestoPct} onChange={(e) => onImpuesto(Number(e.target.value))} />
        </div>
      </div>
      <div className="bg-muted/50 rounded-md p-3 space-y-1">
        <div className="flex justify-between text-muted-foreground">
          <span>Subtotal</span><span>{fmt(subtotal)}</span>
        </div>
        {descMonto > 0 && (
          <div className="flex justify-between text-muted-foreground">
            <span>Descuento ({descuentoPct}%)</span><span>-{fmt(descMonto)}</span>
          </div>
        )}
        {impMonto > 0 && (
          <div className="flex justify-between text-muted-foreground">
            <span>Impuesto ({impuestoPct}%)</span><span>{fmt(impMonto)}</span>
          </div>
        )}
        <div className="flex justify-between font-bold border-t pt-1 text-base">
          <span>Total</span><span>{fmt(total)}</span>
        </div>
      </div>
    </div>
  )
}

// â”€â”€â”€ View Document dialog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function DocumentoDetailDialog({
  open, onClose, titulo, doc,
}: {
  open: boolean
  onClose: () => void
  titulo: string
  doc: Cotizacion | Factura | null
}) {
  if (!doc) return null
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{titulo} â€” {doc.numero}</DialogTitle>
          <DialogDescription className="sr-only">Detalle del documento</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <div><span className="text-muted-foreground">Sede:</span> {doc.location_name}</div>
            <div><span className="text-muted-foreground">Creado por:</span> {doc.creado_por_usuario}</div>
            <div><span className="text-muted-foreground">Cliente:</span> {doc.cliente_nombre}</div>
            <div><span className="text-muted-foreground">CÃ©dula:</span> {doc.cliente_cedula || 'â€”'}</div>
            <div><span className="text-muted-foreground">Correo:</span> {doc.cliente_correo || 'â€”'}</div>
            <div><span className="text-muted-foreground">TelÃ©fono:</span> {doc.cliente_telefono || 'â€”'}</div>
            {'fecha_vencimiento' in doc && (
              <div><span className="text-muted-foreground">Vencimiento:</span> {doc.fecha_vencimiento || 'â€”'}</div>
            )}
            <div><span className="text-muted-foreground">Fecha:</span> {doc.fecha_emision}</div>
          </div>

          {doc.notas && (
            <div><span className="text-muted-foreground">Notas:</span> {doc.notas}</div>
          )}

          <div className="border rounded-md overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-3 py-2">DescripciÃ³n</th>
                  <th className="text-center px-3 py-2">Cant.</th>
                  <th className="text-right px-3 py-2">Precio</th>
                  <th className="text-right px-3 py-2">Desc.</th>
                  <th className="text-right px-3 py-2">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {doc.items.map((item, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-3 py-1">{item.descripcion}</td>
                    <td className="px-3 py-1 text-center">{item.cantidad}</td>
                    <td className="px-3 py-1 text-right">{fmt(item.precio_unitario)}</td>
                    <td className="px-3 py-1 text-right">{fmt(item.descuento_item)}</td>
                    <td className="px-3 py-1 text-right font-medium">{fmt(item.subtotal ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-muted/50 rounded-md p-3 space-y-1 text-sm">
            <div className="flex justify-between text-muted-foreground">
              <span>Subtotal</span><span>{fmt(doc.subtotal)}</span>
            </div>
            {Number(doc.descuento_monto) > 0 && (
              <div className="flex justify-between text-muted-foreground">
                <span>Descuento ({doc.descuento_pct}%)</span><span>-{fmt(doc.descuento_monto)}</span>
              </div>
            )}
            {Number(doc.impuesto_monto) > 0 && (
              <div className="flex justify-between text-muted-foreground">
                <span>Impuesto ({doc.impuesto_pct}%)</span><span>{fmt(doc.impuesto_monto)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold border-t pt-1 text-base">
              <span>Total</span><span>{fmt(doc.total)}</span>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  TAB 1 â€” STOCK
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

function StockTab({ isSuperAdmin, locations }: { isSuperAdmin: boolean; locationId: number | null; locations: Location[] }) {
  const [entries, setEntries] = useState<StockEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [editEntry, setEditEntry] = useState<StockEntry | null>(null)
  const [editQty, setEditQty] = useState(0)
  const [saving, setSaving] = useState(false)
  const [filterLocation, setFilterLocation] = useState<string>('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page }
      if (search) params.search = search
      if (isSuperAdmin && filterLocation) params.location_id = Number(filterLocation)
      const res = await gestionService.getStock(params as never)
      setEntries(res.data)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [page, search, isSuperAdmin, filterLocation])

  useEffect(() => { load() }, [load])

  const openEdit = (entry: StockEntry) => {
    setEditEntry(entry)
    setEditQty(entry.quantity)
  }

  const saveEdit = async () => {
    if (!editEntry) return
    setSaving(true)
    try {
      const payload: { quantity: number; location_id?: number } = { quantity: editQty }
      if (isSuperAdmin && filterLocation) payload.location_id = Number(filterLocation)
      await gestionService.updateStock(editEntry.producto_id, editQty, payload.location_id)
      setEditEntry(null)
      load()
    } catch {
      alert('Error al actualizar el stock')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center justify-between">
        <div className="flex gap-2 flex-1 min-w-0">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input className="pl-8 h-9" placeholder="Buscar producto..." value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
          </div>
          {isSuperAdmin && (
            <Select value={filterLocation || '__all__'} onValueChange={(v) => { setFilterLocation(v === '__all__' ? '' : v); setPage(1) }}>
              <SelectTrigger className="h-9 w-52"><SelectValue placeholder="Todas las sedes" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Todas las sedes</SelectItem>
                {locations.map((l) => (
                  <SelectItem key={l.id} value={String(l.id)}>{l.name} â€” {l.city}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{total} registros</span>
          <Button variant="ghost" size="icon" onClick={load}><RefreshCw className="h-4 w-4" /></Button>
        </div>
      </div>

      <div className="border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Producto</TableHead>
              <TableHead className="text-right">Precio</TableHead>
              <TableHead className="text-center">Cantidad</TableHead>
              <TableHead className="text-right text-xs">Actualizado</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8">
                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
              </TableCell></TableRow>
            ) : entries.length === 0 ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                Sin registros de stock
              </TableCell></TableRow>
            ) : entries.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="font-medium">{e.producto_name}</TableCell>
                <TableCell className="text-right">{fmt(e.precio)}</TableCell>
                <TableCell className="text-center">
                  <span className={`font-bold ${e.quantity === 0 ? 'text-destructive' : e.quantity <= 5 ? 'text-orange-500' : 'text-green-600'}`}>
                    {e.quantity}
                  </span>
                </TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">
                  {new Date(e.updated_at).toLocaleDateString('es-CO')}
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon"
                    disabled={isSuperAdmin && !filterLocation}
                    title={isSuperAdmin && !filterLocation ? 'Selecciona una sede para editar stock' : 'Editar cantidad'}
                    onClick={() => openEdit(e)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages}
          onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
      )}

      {/* Edit dialog */}
      <Dialog open={!!editEntry} onOpenChange={() => setEditEntry(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Ajustar stock â€” {editEntry?.producto_name}</DialogTitle>
            <DialogDescription className="sr-only">Ajusta la cantidad disponible de este producto</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <Label>Nueva cantidad</Label>
              <Input type="number" min={0} className="mt-1"
                value={editQty} onChange={(e) => setEditQty(Number(e.target.value))} />
            </div>
            {isSuperAdmin && (
              <p className="text-xs text-muted-foreground">
                Sede: {filterLocation
                  ? (locations.find((l) => String(l.id) === filterLocation)?.name ?? `ID ${filterLocation}`)
                  : 'Selecciona una sede en el filtro superior'}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditEntry(null)}>Cancelar</Button>
            <Button onClick={saveEdit} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  TAB 2 â€” COTIZACIONES
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

function CotizacionesTab({ isSuperAdmin, locationId, locations }: { isSuperAdmin: boolean; locationId: number | null; locations: Location[] }) {
  const [rows, setRows] = useState<Cotizacion[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [estado, setEstado] = useState('__all__')
  const [loading, setLoading] = useState(false)

  // Detail dialog
  const [detailDoc, setDetailDoc] = useState<Cotizacion | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // Create/Edit dialog
  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [formLoading, setFormLoading] = useState(false)
  const [formData, setFormData] = useState({
    cliente_nombre: '',
    cliente_cedula: '',
    cliente_correo: '',
    cliente_telefono: '',
    fecha_vencimiento: '',
    descuento_pct: 0,
    impuesto_pct: 0,
    notas: '',
    location_id: locationId ?? undefined as number | undefined,
  })
  const [items, setItems] = useState<DocumentoItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page }
      if (search) params.search = search
      if (estado !== '__all__') params.estado = estado
      const res = await gestionService.getCotizaciones(params as never)
      setRows(res.data)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [page, search, estado])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditId(null)
    setFormData({ cliente_nombre: '', cliente_cedula: '', cliente_correo: '', cliente_telefono: '',
      fecha_vencimiento: '', descuento_pct: 0, impuesto_pct: 0, notas: '',
      location_id: locationId ?? undefined })
    setItems([])
    setFormOpen(true)
  }

  const openEdit = async (cot: Cotizacion) => {
    setEditId(cot.id)
    setFormData({
      cliente_nombre: cot.cliente_nombre,
      cliente_cedula: cot.cliente_cedula,
      cliente_correo: cot.cliente_correo,
      cliente_telefono: cot.cliente_telefono,
      fecha_vencimiento: cot.fecha_vencimiento ?? '',
      descuento_pct: 0,
      impuesto_pct: 0,
      notas: cot.notas ?? '',
      location_id: cot.location_id ?? locationId ?? undefined,
    })
    try {
      const res = await gestionService.getCotizacion(cot.id)
      const d = res.data
      setFormData({
        cliente_nombre: d.cliente_nombre,
        cliente_cedula: d.cliente_cedula,
        cliente_correo: d.cliente_correo,
        cliente_telefono: d.cliente_telefono,
        fecha_vencimiento: d.fecha_vencimiento ?? '',
        descuento_pct: Number(d.descuento_pct) || 0,
        impuesto_pct: Number(d.impuesto_pct) || 0,
        notas: d.notas,
        location_id: d.location_id ?? locationId ?? undefined,
      })
      setItems(d.items.map((i) => ({ ...i, descuento_item: Number(i.descuento_item) })))
    } catch {
      setItems([])
    }
    setFormOpen(true)
  }

  const viewDetail = async (id: number) => {
    try {
      const res = await gestionService.getCotizacion(id)
      setDetailDoc(res.data)
      setDetailOpen(true)
    } catch { /* ignore */ }
  }

  const saveForm = async () => {
    if (items.length === 0) { alert('Agrega al menos un producto'); return }
    setFormLoading(true)
    try {
      const payload = {
        ...formData,
        fecha_vencimiento: formData.fecha_vencimiento || undefined,
        items: items.map(({ producto_id, descripcion, cantidad, precio_unitario, descuento_item }) => ({
          producto_id, descripcion, cantidad, precio_unitario, descuento_item,
        })),
      }
      if (editId) {
        await gestionService.updateCotizacion(editId, payload)
      } else {
        await gestionService.createCotizacion(payload)
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      alert(msg || 'Error al guardar la cotizaciÃ³n')
    } finally {
      setFormLoading(false)
    }
  }

  const deleteCot = async (id: number) => {
    if (!confirm('Â¿Eliminar esta cotizaciÃ³n?')) return
    try {
      await gestionService.deleteCotizacion(id)
      load()
    } catch { alert('No se puede eliminar') }
  }

  const convertir = async (id: number) => {
    if (!confirm('Â¿Convertir esta cotizaciÃ³n en factura? Se descontarÃ¡ el stock.')) return
    try {
      await gestionService.convertirCotizacion(id)
      load()
      alert('Factura generada correctamente')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      alert(msg || 'Error al convertir')
    }
  }

  const changeEstado = async (cot: Cotizacion, nuevoEstado: string) => {
    try {
      await gestionService.updateCotizacion(cot.id, { estado: nuevoEstado as Cotizacion['estado'] })
      load()
    } catch { alert('Error al cambiar estado') }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <ClipboardList className="h-5 w-5" />
              Cotizaciones <span className="text-muted-foreground font-normal">({total})</span>
            </CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input className="pl-8 h-9 w-52" placeholder="Buscar por cliente, nÃºmero..." value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
                </div>
                <Select value={estado} onValueChange={(v) => { setEstado(v); setPage(1) }}>
                  <SelectTrigger className="h-9 w-36"><SelectValue placeholder="Estado" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    {Object.entries(COTIZACION_ESTADOS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4 mr-1" />Nueva cotizaciÃ³n</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>NÃºmero</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Sede</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right text-xs">EmisiÃ³n</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8">
                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
              </TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                Sin cotizaciones
              </TableCell></TableRow>
            ) : rows.map((cot) => (
              <TableRow key={cot.id}>
                <TableCell className="font-mono text-xs font-medium">{cot.numero}</TableCell>
                <TableCell>
                  <div className="font-medium text-sm">{cot.cliente_nombre}</div>
                  {cot.cliente_cedula && <div className="text-xs text-muted-foreground">{cot.cliente_cedula}</div>}
                </TableCell>
                <TableCell className="text-sm">{cot.location_name}</TableCell>
                <TableCell>
                  <StatusBadge {...COTIZACION_ESTADOS[cot.estado]} />
                </TableCell>
                <TableCell className="text-right font-medium">{fmt(cot.total)}</TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">{cot.fecha_emision}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 justify-end">
                    <Button variant="ghost" size="icon" title="Ver detalle" onClick={() => viewDetail(cot.id)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    {(cot.estado === 'borrador' || cot.estado === 'enviada') && (
                      <Button variant="ghost" size="icon" title="Editar" onClick={() => openEdit(cot)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    {cot.estado === 'borrador' && (
                      <>
                        <Button variant="ghost" size="icon" title="Marcar enviada"
                          onClick={() => changeEstado(cot, 'enviada')}>
                          <FileText className="h-4 w-4 text-blue-500" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Eliminar" onClick={() => deleteCot(cot.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </>
                    )}
                    {(cot.estado === 'enviada' || cot.estado === 'aprobada') && !cot.tiene_factura && (
                      <Button variant="ghost" size="icon" title="Convertir a factura"
                        onClick={() => convertir(cot.id)}>
                        <FileCheck className="h-4 w-4 text-green-600" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
          </div>
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

      {/* Detail dialog */}
      <DocumentoDetailDialog open={detailOpen} onClose={() => setDetailOpen(false)}
        titulo="CotizaciÃ³n" doc={detailDoc} />

      {/* Create/Edit dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editId ? 'Editar cotizaciÃ³n' : 'Nueva cotizaciÃ³n'}</DialogTitle>
            <DialogDescription className="sr-only">Formulario de cotizaciÃ³n</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Client data */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Cliente *</Label>
                <Input className="mt-1" value={formData.cliente_nombre}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_nombre: e.target.value }))} />
              </div>
              <div>
                <Label>CÃ©dula</Label>
                <Input className="mt-1" value={formData.cliente_cedula}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_cedula: e.target.value }))} />
              </div>
              <div>
                <Label>Correo</Label>
                <Input type="email" className="mt-1" value={formData.cliente_correo}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_correo: e.target.value }))} />
              </div>
              <div>
                <Label>TelÃ©fono</Label>
                <Input className="mt-1" value={formData.cliente_telefono}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_telefono: e.target.value }))} />
              </div>
              <div>
                <Label>Vencimiento</Label>
                <Input type="date" className="mt-1" value={formData.fecha_vencimiento}
                  onChange={(e) => setFormData((d) => ({ ...d, fecha_vencimiento: e.target.value }))} />
              </div>
              {isSuperAdmin && (
                <div>
                  <Label>Sede</Label>
                  <Select
                    value={formData.location_id != null ? String(formData.location_id) : ''}
                    onValueChange={(v) => setFormData((d) => ({ ...d, location_id: v ? Number(v) : undefined }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Seleccionar sede" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations.map((l) => (
                        <SelectItem key={l.id} value={String(l.id)}>{l.name} â€” {l.city}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            {/* Items */}
            <div>
              <Label className="mb-2 block">Productos</Label>
              <ItemEditor items={items} onChange={setItems} />
            </div>

            {/* Totals */}
            <TotalesForm items={items} descuentoPct={formData.descuento_pct} impuestoPct={formData.impuesto_pct}
              onDescuento={(v) => setFormData((d) => ({ ...d, descuento_pct: v }))}
              onImpuesto={(v) => setFormData((d) => ({ ...d, impuesto_pct: v }))} />

            {/* Notes */}
            <div>
              <Label>Notas</Label>
              <Textarea className="mt-1 h-20 resize-none" value={formData.notas}
                onChange={(e) => setFormData((d) => ({ ...d, notas: e.target.value }))} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>Cancelar</Button>
            <Button onClick={saveForm} disabled={formLoading}>
              {formLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editId ? 'Guardar cambios' : 'Crear cotizaciÃ³n'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  TAB 3 â€” FACTURAS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

function FacturasTab({ isSuperAdmin, locationId, locations }: { isSuperAdmin: boolean; locationId: number | null; locations: Location[] }) {
  const [rows, setRows] = useState<Factura[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [estado, setEstado] = useState('__all__')
  const [loading, setLoading] = useState(false)

  const [detailDoc, setDetailDoc] = useState<Factura | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const [formOpen, setFormOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [formLoading, setFormLoading] = useState(false)
  const [formData, setFormData] = useState({
    cliente_nombre: '',
    cliente_cedula: '',
    cliente_correo: '',
    cliente_telefono: '',
    descuento_pct: 0,
    impuesto_pct: 0,
    notas: '',
    location_id: locationId ?? undefined as number | undefined,
  })
  const [items, setItems] = useState<DocumentoItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page }
      if (search) params.search = search
      if (estado !== '__all__') params.estado = estado
      const res = await gestionService.getFacturas(params as never)
      setRows(res.data)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [page, search, estado])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditId(null)
    setFormData({ cliente_nombre: '', cliente_cedula: '', cliente_correo: '', cliente_telefono: '',
      descuento_pct: 0, impuesto_pct: 0, notas: '', location_id: locationId ?? undefined })
    setItems([])
    setFormOpen(true)
  }

  const openEdit = async (fac: Factura) => {
    setEditId(fac.id)
    try {
      const res = await gestionService.getFactura(fac.id)
      const d = res.data
      setFormData({
        cliente_nombre: d.cliente_nombre,
        cliente_cedula: d.cliente_cedula,
        cliente_correo: d.cliente_correo,
        cliente_telefono: d.cliente_telefono,
        descuento_pct: Number(d.descuento_pct) || 0,
        impuesto_pct: Number(d.impuesto_pct) || 0,
        notas: d.notas,
        location_id: d.location_id ?? locationId ?? undefined,
      })
      setItems(d.items.map((i) => ({ ...i, descuento_item: Number(i.descuento_item) })))
    } catch {
      setItems([])
    }
    setFormOpen(true)
  }

  const viewDetail = async (id: number) => {
    try {
      const res = await gestionService.getFactura(id)
      setDetailDoc(res.data)
      setDetailOpen(true)
    } catch { /* ignore */ }
  }

  const saveForm = async () => {
    if (items.length === 0) { alert('Agrega al menos un producto'); return }
    setFormLoading(true)
    try {
      const itemsPayload = items.map(({ producto_id, descripcion, cantidad, precio_unitario, descuento_item }) => ({
        producto_id, descripcion, cantidad, precio_unitario, descuento_item,
      }))
      if (editId) {
        await gestionService.updateFactura(editId, { ...formData, items: itemsPayload })
      } else {
        await gestionService.createFactura({ ...formData, items: itemsPayload })
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      alert(msg || 'Error al guardar la factura')
    } finally {
      setFormLoading(false)
    }
  }

  const anular = async (id: number) => {
    if (!confirm('Â¿Anular esta factura? Se restaurarÃ¡ el stock descontado.')) return
    try {
      await gestionService.anularFactura(id)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      alert(msg || 'Error al anular')
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-5 w-5" />
              Facturas <span className="text-muted-foreground font-normal">({total})</span>
            </CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input className="pl-8 h-9 w-52" placeholder="Buscar por cliente, nÃºmero..." value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
                </div>
                <Select value={estado} onValueChange={(v) => { setEstado(v); setPage(1) }}>
                  <SelectTrigger className="h-9 w-36"><SelectValue placeholder="Estado" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Todos</SelectItem>
                    {Object.entries(FACTURA_ESTADOS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4 mr-1" />Nueva factura</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>NÃºmero</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Sede</TableHead>
              <TableHead>Cot. origen</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right text-xs">EmisiÃ³n</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8">
                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
              </TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                Sin facturas
              </TableCell></TableRow>
            ) : rows.map((fac) => (
              <TableRow key={fac.id}>
                <TableCell className="font-mono text-xs font-medium">{fac.numero}</TableCell>
                <TableCell>
                  <div className="font-medium text-sm">{fac.cliente_nombre}</div>
                  {fac.cliente_cedula && <div className="text-xs text-muted-foreground">{fac.cliente_cedula}</div>}
                </TableCell>
                <TableCell className="text-sm">{fac.location_name}</TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  {fac.cotizacion_numero ?? 'â€”'}
                </TableCell>
                <TableCell>
                  <StatusBadge {...FACTURA_ESTADOS[fac.estado]} />
                </TableCell>
                <TableCell className="text-right font-medium">{fmt(fac.total)}</TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">{fac.fecha_emision}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 justify-end">
                    <Button variant="ghost" size="icon" title="Ver detalle" onClick={() => viewDetail(fac.id)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    {fac.estado === 'emitida' && (
                      <Button variant="ghost" size="icon" title="Editar factura" onClick={() => openEdit(fac)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    {fac.estado === 'emitida' && (
                      <Button variant="ghost" size="icon" title="Anular factura" onClick={() => anular(fac.id)}>
                        <Ban className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
          </div>
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

      <DocumentoDetailDialog open={detailOpen} onClose={() => setDetailOpen(false)}
        titulo="Factura" doc={detailDoc} />

      {/* Create dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editId ? 'Editar factura' : 'Nueva factura directa'}</DialogTitle>
            <DialogDescription className="sr-only">Formulario de factura</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Cliente *</Label>
                <Input className="mt-1" value={formData.cliente_nombre}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_nombre: e.target.value }))} />
              </div>
              <div>
                <Label>CÃ©dula</Label>
                <Input className="mt-1" value={formData.cliente_cedula}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_cedula: e.target.value }))} />
              </div>
              <div>
                <Label>Correo</Label>
                <Input type="email" className="mt-1" value={formData.cliente_correo}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_correo: e.target.value }))} />
              </div>
              <div>
                <Label>TelÃ©fono</Label>
                <Input className="mt-1" value={formData.cliente_telefono}
                  onChange={(e) => setFormData((d) => ({ ...d, cliente_telefono: e.target.value }))} />
              </div>
              {isSuperAdmin && (
                <div>
                  <Label>Sede</Label>
                  <Select
                    value={formData.location_id != null ? String(formData.location_id) : ''}
                    onValueChange={(v) => setFormData((d) => ({ ...d, location_id: v ? Number(v) : undefined }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Seleccionar sede" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations.map((l) => (
                        <SelectItem key={l.id} value={String(l.id)}>{l.name} â€” {l.city}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            <div>
              <Label className="mb-2 block">Productos</Label>
              <ItemEditor items={items} onChange={setItems} />
            </div>

            <TotalesForm items={items} descuentoPct={formData.descuento_pct} impuestoPct={formData.impuesto_pct}
              onDescuento={(v) => setFormData((d) => ({ ...d, descuento_pct: v }))}
              onImpuesto={(v) => setFormData((d) => ({ ...d, impuesto_pct: v }))} />

            <div>
              <Label>Notas</Label>
              <Textarea className="mt-1 h-20 resize-none" value={formData.notas}
                onChange={(e) => setFormData((d) => ({ ...d, notas: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>Cancelar</Button>
            <Button onClick={saveForm} disabled={formLoading}>
              {formLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {editId ? 'Guardar cambios' : 'Emitir factura'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  MAIN PAGE
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

type TabKey = 'cotizaciones' | 'facturas'

const TAB_META: Record<TabKey, { label: string; icon: typeof FileText; description: string }> = {
  cotizaciones: { label: 'Cotizaciones',       icon: ClipboardList, description: 'Gestiona cotizaciones y convÃ©rtelas en factura' },
  facturas:     { label: 'Facturas',           icon: FileText,     description: 'Emite y administra facturas de venta' },
}

export default function GestionPage() {
  const { user } = useAuth()
  const location = useLocation()
  const [sede, setSede] = useState<{ id: number; name: string; city: string } | null>(null)
  const [locations, setLocations] = useState<Location[]>([])

  const isSuperAdmin = (user?.tipo_usuario ?? 0) === 4
  const locationId = user?.location_id ?? null

  // Derive active tab from URL path
  const pathSegment = location.pathname.split('/').pop() as TabKey | undefined
  const activeTab: TabKey =
    pathSegment && pathSegment in TAB_META ? pathSegment : 'cotizaciones'

  useEffect(() => {
    if (!isSuperAdmin && locationId) {
      gestionService.getMiSede()
        .then((res) => setSede(res.location))
        .catch(() => {})
    }
  }, [isSuperAdmin, locationId])

  useEffect(() => {
    locationsService.getAll({ per_page: 100 })
      .then((res) => setLocations(res.data))
      .catch(() => {})
  }, [])

  // Access guard
  if ((user?.tipo_usuario ?? 0) < 1) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <AlertTriangle className="h-10 w-10" />
        <p className="font-medium">Sin permiso para acceder a esta secciÃ³n</p>
      </div>
    )
  }

  const { label, icon: TabIcon, description } = TAB_META[activeTab]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <TabIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{label}</h1>
            <p className="text-muted-foreground text-sm">
              {isSuperAdmin
                ? description + ' â€” todas las sedes'
                : sede
                ? `${description} â€” ${sede.name}, ${sede.city}`
                : description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isSuperAdmin ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
              <Receipt className="h-3.5 w-3.5" />
              Super Administrador
            </span>
          ) : sede ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-muted text-muted-foreground border">
              Admin de sede
            </span>
          ) : null}
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'cotizaciones' && (
        <CotizacionesTab isSuperAdmin={isSuperAdmin} locationId={locationId} locations={locations} />
      )}
      {activeTab === 'facturas' && (
        <FacturasTab isSuperAdmin={isSuperAdmin} locationId={locationId} locations={locations} />
      )}
    </div>
  )
}
