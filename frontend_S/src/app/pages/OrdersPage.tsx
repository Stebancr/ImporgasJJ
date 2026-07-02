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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Search, Eye, ShoppingCart, RefreshCw } from 'lucide-react'
import type { Order, OrderStatus } from '@/types'
import { ordersService } from '@/services/orders'

const statusConfig: Record<OrderStatus, { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' }> = {
  pending:   { label: 'Pendiente',     variant: 'secondary' },
  paid:      { label: 'Pagado',        variant: 'default' },
  preparing: { label: 'Preparando',    variant: 'warning' },
  shipping:  { label: 'En camino',     variant: 'default' },
  delivered: { label: 'Entregado',     variant: 'success' },
  installed: { label: 'Instalado',     variant: 'success' },
  cancelled: { label: 'Cancelado',     variant: 'destructive' },
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  const fetchOrders = () => {
    setLoading(true)
    ordersService.getAll()
      .then((res) => setOrders(Array.isArray(res?.data) ? res.data : []))
      .catch(() => setOrders([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      (order.order_number ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.customer_name ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.customer_email ?? '').toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleViewOrder = (order: Order) => {
    setSelectedOrder(order)
    setIsDetailOpen(true)
  }

  const handleStatusChange = async (orderId: number, newStatus: OrderStatus) => {
    setUpdatingId(orderId)
    try {
      await ordersService.updateStatus(orderId, newStatus)
      setOrders((prev) => prev.map((o) => o.id === orderId ? { ...o, status: newStatus } : o))
      if (selectedOrder?.id === orderId) {
        setSelectedOrder({ ...selectedOrder, status: newStatus })
      }
    } catch {
      alert('Error al actualizar el estado')
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Ordenes</h1>
        <p className="text-muted-foreground">Administra los pedidos de los clientes</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5" />
              Lista de Ordenes
            </CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Button variant="outline" size="icon" onClick={fetchOrders} title="Actualizar">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="Filtrar por estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                  <SelectItem value="paid">Pagado</SelectItem>
                  <SelectItem value="preparing">Preparando</SelectItem>
                  <SelectItem value="shipping">En camino</SelectItem>
                  <SelectItem value="delivered">Entregado</SelectItem>
                  <SelectItem value="installed">Instalado</SelectItem>
                  <SelectItem value="cancelled">Cancelado</SelectItem>
                </SelectContent>
              </Select>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar ordenes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-center py-8 text-muted-foreground">Cargando órdenes...</p>
            ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Orden</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Metodo de pago</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOrders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-10 text-muted-foreground">
                      {searchTerm || statusFilter !== 'all'
                        ? 'No se encontraron órdenes con ese filtro.'
                        : 'No hay órdenes registradas aún.'}
                    </TableCell>
                  </TableRow>
                ) : (
                filteredOrders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.order_number}</TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{order.customer_name}</p>
                        <p className="text-sm text-muted-foreground">{order.customer_email}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatPrice(order.total)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {order.payment_method === 'wompi' ? 'Wompi' : 'Contra entrega'}
                    </TableCell>
                    <TableCell className="text-center">
                      <Select
                        value={order.status}
                        onValueChange={(value) => handleStatusChange(order.id, value as OrderStatus)}
                        disabled={updatingId === order.id}
                      >
                        <SelectTrigger className="h-7 w-36 mx-auto text-xs border-none shadow-none focus:ring-0 px-2">
                          <Badge variant={statusConfig[order.status]?.variant ?? 'secondary'} className="cursor-pointer">
                            {updatingId === order.id ? '...' : (statusConfig[order.status]?.label ?? order.status)}
                          </Badge>
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pending">Pendiente</SelectItem>
                          <SelectItem value="paid">Pagado</SelectItem>
                          <SelectItem value="preparing">Preparando</SelectItem>
                          <SelectItem value="shipping">En camino</SelectItem>
                          <SelectItem value="delivered">Entregado</SelectItem>
                          <SelectItem value="installed">Instalado</SelectItem>
                          <SelectItem value="cancelled">Cancelado</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(order.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleViewOrder(order)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
                )}
              </TableBody>
            </Table>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Order Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Detalle de Orden {selectedOrder?.order_number}</DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Cliente</p>
                  <p className="font-medium">{selectedOrder.customer_name}</p>
                  <p className="text-sm text-muted-foreground">{selectedOrder.customer_email}</p>
                  {selectedOrder.customer_phone && (
                    <p className="text-sm text-muted-foreground">{selectedOrder.customer_phone}</p>
                  )}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Direccion de envio</p>
                  <p className="font-medium">{selectedOrder.shipping_address}</p>
                  {selectedOrder.city && (
                    <p className="text-sm text-muted-foreground">{selectedOrder.city}{selectedOrder.department ? `, ${selectedOrder.department}` : ''}</p>
                  )}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Metodo de pago</p>
                  <p className="font-medium">{selectedOrder.payment_method === 'wompi' ? 'Wompi' : 'Contra entrega'}</p>
                  {selectedOrder.wompi_reference && (
                    <p className="text-xs text-muted-foreground font-mono">Ref: {selectedOrder.wompi_reference}</p>
                  )}
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fecha</p>
                  <p className="font-medium">{formatDate(selectedOrder.created_at)}</p>
                </div>
                {selectedOrder.tracking_code && (
                  <div className="col-span-2">
                    <p className="text-sm text-muted-foreground">Código de seguimiento</p>
                    <p className="font-mono text-xs text-blue-700">{String(selectedOrder.tracking_code)}</p>
                  </div>
                )}
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-2">Productos</p>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead className="text-center">Cantidad</TableHead>
                        <TableHead className="text-right">Precio</TableHead>
                        <TableHead className="text-right">Subtotal</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(selectedOrder.items ?? []).map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>{item.product?.name ?? `Producto #${item.product_id}`}</TableCell>
                          <TableCell className="text-center">{item.quantity}</TableCell>
                          <TableCell className="text-right">{formatPrice(item.unit_price)}</TableCell>
                          <TableCell className="text-right font-medium">
                            {formatPrice(item.quantity * item.unit_price)}
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow>
                        <TableCell colSpan={3} className="text-right text-muted-foreground">Subtotal</TableCell>
                        <TableCell className="text-right">{formatPrice(Number(selectedOrder.subtotal ?? selectedOrder.total))}</TableCell>
                      </TableRow>
                      {selectedOrder.shipping_cost != null && Number(selectedOrder.shipping_cost) > 0 && (
                        <TableRow>
                          <TableCell colSpan={3} className="text-right text-muted-foreground">Envío</TableCell>
                          <TableCell className="text-right">{formatPrice(Number(selectedOrder.shipping_cost))}</TableCell>
                        </TableRow>
                      )}
                      <TableRow>
                        <TableCell colSpan={3} className="text-right font-bold">Total</TableCell>
                        <TableCell className="text-right font-bold">{formatPrice(Number(selectedOrder.total))}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </div>

              <div>
                <Label htmlFor="status">Cambiar estado</Label>
                <Select
                  value={selectedOrder.status}
                  onValueChange={(value) => handleStatusChange(selectedOrder.id, value as OrderStatus)}
                >
                  <SelectTrigger className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pendiente</SelectItem>
                    <SelectItem value="paid">Pagado</SelectItem>
                    <SelectItem value="preparing">Preparando</SelectItem>
                    <SelectItem value="shipping">En camino</SelectItem>
                    <SelectItem value="delivered">Entregado</SelectItem>
                    <SelectItem value="installed">Instalado</SelectItem>
                    <SelectItem value="cancelled">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDetailOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
