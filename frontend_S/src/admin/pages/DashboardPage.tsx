import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'
import { gestionService } from '@/admin/services/gestion'
import type { StockEntry, Factura } from '@/admin/services/gestion'
import { productsService, usersService, locationsService } from '@/admin/services'
import type { Location } from '@/admin/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Package, Users, FileText, DollarSign, TrendingUp,
  AlertTriangle, Receipt, Loader2, TrendingDown,
} from 'lucide-react'

// â”€â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const fmt = (val: number) =>
  val.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })

const ESTADO_COLORS: Record<string, string> = {
  emitida: 'bg-green-100 text-green-700',
  anulada: 'bg-red-100 text-red-700',
}

// â”€â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function DashboardPage() {
  const { user } = useAuth()
  const isSuperAdmin = (user?.tipo_usuario ?? 0) === 4
  const locationId = user?.location_id ?? null

  const [loading, setLoading] = useState(true)
  const [totalProductos, setTotalProductos] = useState(0)
  const [totalUsuarios, setTotalUsuarios] = useState(0)
  const [totalFacturas, setTotalFacturas] = useState(0)
  const [ingresosMes, setIngresosMes] = useState(0)
  const [recentFacturas, setRecentFacturas] = useState<Factura[]>([])
  const [lowStock, setLowStock] = useState<StockEntry[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedLocation, setSelectedLocation] = useState<string>('__all__')

  // Load locations list for super admin sede picker
  useEffect(() => {
    if (isSuperAdmin) {
      locationsService.getAll({ per_page: 100 })
        .then((res) => setLocations(res.data))
        .catch(() => {})
    }
  }, [isSuperAdmin])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      // Stock params: super admin can filter by sede or see aggregate
      const stockParams: Record<string, unknown> = { per_page: 50 }
      if (isSuperAdmin && selectedLocation !== '__all__') {
        stockParams.location_id = Number(selectedLocation)
      } else if (!isSuperAdmin && locationId) {
        stockParams.location_id = locationId
      }

      const [stockRes, facturasRes, prodRes, userRes] = await Promise.allSettled([
        gestionService.getStock(stockParams as never),
        gestionService.getFacturas({ page: 1 }),
        productsService.getAll({ per_page: 1 } as never),
        usersService.listarColaboradores({ page: 1, page_size: 1 }),
      ])

      if (stockRes.status === 'fulfilled') {
        const low = stockRes.value.data.filter((e) => e.quantity <= 5).sort((a, b) => a.quantity - b.quantity)
        setLowStock(low)
      }

      if (facturasRes.status === 'fulfilled') {
        const { data, total } = facturasRes.value
        setTotalFacturas(total)
        setRecentFacturas(data)
        const ingreso = data
          .filter((f) => f.estado === 'emitida')
          .reduce((s, f) => s + Number(f.total), 0)
        setIngresosMes(ingreso)
      }

      if (prodRes.status === 'fulfilled') {
        const pr = prodRes.value as unknown as { total?: number; count?: number }
        setTotalProductos(pr.total ?? pr.count ?? 0)
      }

      if (userRes.status === 'fulfilled') {
        setTotalUsuarios(userRes.value.count)
      }
    } finally {
      setLoading(false)
    }
  }, [isSuperAdmin, locationId, selectedLocation])

  useEffect(() => { loadData() }, [loadData])

  const stats = [
    { title: 'Total Productos', value: totalProductos, icon: Package, color: 'text-blue-500' },
    { title: 'Usuarios Registrados', value: totalUsuarios, icon: Users, color: 'text-violet-500' },
    { title: 'Facturas Totales', value: totalFacturas, icon: FileText, color: 'text-orange-500' },
    { title: 'Ingresos (Ãºltimas 8)', value: fmt(ingresosMes), icon: DollarSign, color: 'text-emerald-500', isCurrency: true },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground text-sm">Resumen general del sistema</p>
        </div>
        {isSuperAdmin && locations.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Sede:</span>
            <Select value={selectedLocation} onValueChange={setSelectedLocation}>
              <SelectTrigger className="h-9 w-52">
                <SelectValue placeholder="Todas las sedes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Todas las sedes</SelectItem>
                {locations.map((l) => (
                  <SelectItem key={l.id} value={String(l.id)}>{l.name} â€” {l.city}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{s.title}</CardTitle>
              <s.icon className={`h-4 w-4 ${s.color}`} />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              ) : (
                <div className="text-2xl font-bold">
                  {typeof s.value === 'number' ? s.value.toLocaleString('es-CO') : s.value}
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                {s.isCurrency ? 'facturas activas recientes' : 'en el sistema'}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Low / Negative Stock */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Stock bajo o negativo
              {!isSuperAdmin && locationId && (
                <span className="text-xs font-normal text-muted-foreground ml-1">â€” su sede</span>
              )}
              {isSuperAdmin && selectedLocation === '__all__' && (
                <span className="text-xs font-normal text-muted-foreground ml-1">â€” todas las sedes (agregado)</span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
            ) : lowStock.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground text-sm">
                âœ“ Sin productos con stock crÃ­tico
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {lowStock.map((e) => {
                  const isNeg = e.quantity < 0
                  const isZero = e.quantity === 0
                  const rowColor = isNeg
                    ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                    : isZero
                    ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                    : 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900'
                  const qtyColor = isNeg || isZero ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-500'
                  return (
                    <div key={e.id} className={`flex items-center justify-between px-3 py-2 rounded-lg border ${rowColor}`}>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-sm truncate">{e.producto_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {isNeg ? 'Stock negativo â€” faltante' : isZero ? 'Sin unidades' : 'Stock bajo'}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 ml-3 shrink-0">
                        {isNeg && <TrendingDown className="h-4 w-4 text-red-500" />}
                        <span className={`text-lg font-bold ${qtyColor}`}>{e.quantity}</span>
                        <span className="text-xs text-muted-foreground">uds</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Facturas */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Receipt className="h-5 w-5 text-primary" />
              Facturas recientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
            ) : recentFacturas.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground text-sm">Sin facturas registradas</div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {recentFacturas.map((fac) => (
                  <div key={fac.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-medium">{fac.numero}</span>
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${ESTADO_COLORS[fac.estado] ?? ''}`}>
                          {fac.estado}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{fac.cliente_nombre}</p>
                    </div>
                    <div className="text-right ml-3 shrink-0">
                      <p className="font-semibold text-sm">{fmt(Number(fac.total))}</p>
                      <p className="text-xs text-muted-foreground">{fac.fecha_emision}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

