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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Search, Eye, ShoppingCart } from 'lucide-react'
import type { OrderStatus } from '@/types'

interface Order {
  id: number
  orderNumber: string
  customer: string
  email: string
  total: number
  status: OrderStatus
  payment_method: string
  shipping_address: string
  created_at: string
  items: {
    product: string
    quantity: number
    unit_price: number
  }[]
}

const mockOrders: Order[] = [
  {
    id: 1,
    orderNumber: 'ORD-001',
    customer: 'Juan Perez',
    email: 'juan@email.com',
    total: 485000,
    status: 'delivered',
    payment_method: 'Tarjeta de credito',
    shipping_address: 'Calle 45 #23-56, Bogota',
    created_at: '2024-01-15T10:30:00',
    items: [
      { product: 'Calentador Haceb 10L', quantity: 1, unit_price: 450000 },
      { product: 'Regulador de Gas', quantity: 1, unit_price: 35000 },
    ],
  },
  {
    id: 2,
    orderNumber: 'ORD-002',
    customer: 'Maria Garcia',
    email: 'maria@email.com',
    total: 1850000,
    status: 'shipping',
    payment_method: 'Transferencia',
    shipping_address: 'Carrera 15 #78-90, Medellin',
    created_at: '2024-01-16T14:20:00',
    items: [
      { product: 'Aire Samsung 12000 BTU', quantity: 1, unit_price: 1850000 },
    ],
  },
  {
    id: 3,
    orderNumber: 'ORD-003',
    customer: 'Carlos Lopez',
    email: 'carlos@email.com',
    total: 170000,
    status: 'preparing',
    payment_method: 'Contraentrega',
    shipping_address: 'Avenida 70 #32-15, Cali',
    created_at: '2024-01-17T09:15:00',
    items: [
      { product: 'Kit Instalacion Gas', quantity: 2, unit_price: 85000 },
    ],
  },
  {
    id: 4,
    orderNumber: 'ORD-004',
    customer: 'Ana Martinez',
    email: 'ana@email.com',
    total: 520000,
    status: 'pending',
    payment_method: 'Tarjeta debito',
    shipping_address: 'Calle 100 #15-20, Bogota',
    created_at: '2024-01-18T16:45:00',
    items: [
      { product: 'Calentador Haceb 10L', quantity: 1, unit_price: 450000 },
      { product: 'Manguera Gas 1.5m', quantity: 2, unit_price: 35000 },
    ],
  },
]

const statusConfig: Record<OrderStatus, { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' }> = {
  pending: { label: 'Pendiente', variant: 'secondary' },
  paid: { label: 'Pagado', variant: 'default' },
  preparing: { label: 'Preparando', variant: 'warning' },
  shipping: { label: 'En camino', variant: 'default' },
  delivered: { label: 'Entregado', variant: 'success' },
  installed: { label: 'Instalado', variant: 'success' },
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>(mockOrders)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      order.orderNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.customer.toLowerCase().includes(searchTerm.toLowerCase())
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

  const handleStatusChange = (orderId: number, newStatus: OrderStatus) => {
    setOrders(orders.map((o) =>
      o.id === orderId ? { ...o, status: newStatus } : o
    ))
    if (selectedOrder?.id === orderId) {
      setSelectedOrder({ ...selectedOrder, status: newStatus })
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
                {filteredOrders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.orderNumber}</TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{order.customer}</p>
                        <p className="text-sm text-muted-foreground">{order.email}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatPrice(order.total)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {order.payment_method}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={statusConfig[order.status].variant}>
                        {statusConfig[order.status].label}
                      </Badge>
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
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Order Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Detalle de Orden {selectedOrder?.orderNumber}</DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Cliente</p>
                  <p className="font-medium">{selectedOrder.customer}</p>
                  <p className="text-sm text-muted-foreground">{selectedOrder.email}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Direccion de envio</p>
                  <p className="font-medium">{selectedOrder.shipping_address}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Metodo de pago</p>
                  <p className="font-medium">{selectedOrder.payment_method}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fecha</p>
                  <p className="font-medium">{formatDate(selectedOrder.created_at)}</p>
                </div>
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
                      {selectedOrder.items.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>{item.product}</TableCell>
                          <TableCell className="text-center">{item.quantity}</TableCell>
                          <TableCell className="text-right">{formatPrice(item.unit_price)}</TableCell>
                          <TableCell className="text-right font-medium">
                            {formatPrice(item.quantity * item.unit_price)}
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow>
                        <TableCell colSpan={3} className="text-right font-bold">
                          Total
                        </TableCell>
                        <TableCell className="text-right font-bold">
                          {formatPrice(selectedOrder.total)}
                        </TableCell>
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
