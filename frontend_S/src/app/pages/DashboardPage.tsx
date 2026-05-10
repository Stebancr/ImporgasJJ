import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Package, Users, ShoppingCart, TrendingUp, DollarSign, AlertTriangle } from 'lucide-react'

const stats = [
  {
    title: 'Total Productos',
    value: '156',
    change: '+12%',
    changeType: 'positive' as const,
    icon: Package,
  },
  {
    title: 'Usuarios Activos',
    value: '45',
    change: '+5%',
    changeType: 'positive' as const,
    icon: Users,
  },
  {
    title: 'Ordenes del Mes',
    value: '89',
    change: '+18%',
    changeType: 'positive' as const,
    icon: ShoppingCart,
  },
  {
    title: 'Ingresos del Mes',
    value: '$12,450',
    change: '+8%',
    changeType: 'positive' as const,
    icon: DollarSign,
  },
]

const lowStockProducts = [
  { id: 1, name: 'Calentador Haceb 10L', stock: 3, minStock: 5 },
  { id: 2, name: 'Regulador de Gas Fisher', stock: 2, minStock: 10 },
  { id: 3, name: 'Manguera Gas 1.5m', stock: 5, minStock: 15 },
]

const recentOrders = [
  { id: 'ORD-001', customer: 'Juan Perez', total: '$350.00', status: 'Entregado' },
  { id: 'ORD-002', customer: 'Maria Garcia', total: '$180.00', status: 'En camino' },
  { id: 'ORD-003', customer: 'Carlos Lopez', total: '$520.00', status: 'Preparando' },
  { id: 'ORD-004', customer: 'Ana Martinez', total: '$95.00', status: 'Pendiente' },
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground">Resumen general del sistema de inventario</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                <span className="text-emerald-500">{stat.change}</span> vs mes anterior
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Low Stock Alert */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Productos con Bajo Stock
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {lowStockProducts.map((product) => (
                <div
                  key={product.id}
                  className="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-900"
                >
                  <div>
                    <p className="font-medium text-foreground">{product.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Stock minimo: {product.minStock} unidades
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-amber-600 dark:text-amber-500">
                      {product.stock}
                    </p>
                    <p className="text-xs text-muted-foreground">unidades</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Orders */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShoppingCart className="h-5 w-5 text-primary" />
              Ordenes Recientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentOrders.map((order) => (
                <div
                  key={order.id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-foreground">{order.id}</p>
                    <p className="text-sm text-muted-foreground">{order.customer}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-foreground">{order.total}</p>
                    <p className="text-xs text-muted-foreground">{order.status}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
