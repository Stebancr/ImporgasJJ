import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Flame,
  LayoutDashboard,
  Package,
  Users,
  Tags,
  FolderTree,
  MapPin,
  ShoppingCart,
  Menu,
  X,
  LogOut,
  ChevronDown,
  ChevronRight,
  User,
  Receipt,
  Boxes,
  FileText,
  ClipboardList,
  MessageSquare,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
  roles?: string[]
  children?: NavItem[]
}

const navigation: NavItem[] = [
  { name: 'Dashboard',   href: '/admin/dashboard',           icon: LayoutDashboard },
  { name: 'Productos',   href: '/admin/productos',  icon: Package },
  { name: 'Categorias',  href: '/admin/categorias',icon: FolderTree },
  { name: 'Marcas',      href: '/admin/marcas',    icon: Tags },
  { name: 'Ubicaciones', href: '/admin/ubicaciones', icon: MapPin },
  { name: 'Ordenes',     href: '/admin/ordenes',    icon: ShoppingCart },
  { name: 'Usuarios',    href: '/admin/usuarios',     icon: Users, roles: ['admin'] },
  { name: 'Visitas',     href: '/admin/visitas',    icon: Wrench, roles: ['admin'] },
  { name: 'CRM Chat',    href: '/admin/chat',       icon: MessageSquare, roles: ['admin'] },
  {
    name: 'Contabilidad',
    href: '/admin/gestion',
    icon: Receipt,
    roles: ['admin'],
    children: [
      { name: 'Cotizaciones',       href: '/admin/gestion/cotizaciones', icon: ClipboardList },
      { name: 'Facturas',           href: '/admin/gestion/facturas',     icon: FileText },
    ],
  },
]

export default function DashboardLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set())
  const [pendingChats, setPendingChats] = useState(0)

  // Poll for pending chat sessions every 5 s
  useEffect(() => {
    if (!user || user.role !== 'admin') return
    const fetchCount = () =>
      import('@/admin/services/chat').then(({ adminChatService }) =>
        adminChatService.getPendingCount().then(setPendingChats).catch(() => {})
      )
    fetchCount()
    const id = setInterval(fetchCount, 5000)
    return () => clearInterval(id)
  }, [user])

  // Auto-open groups whose children match the current path
  useEffect(() => {
    const toOpen = new Set<string>()
    navigation.forEach((item) => {
      if (item.children?.some((c) => location.pathname.startsWith(c.href))) {
        toOpen.add(item.name)
      }
    })
    setOpenGroups(toOpen)
  }, [location.pathname])

  const toggleGroup = (name: string) =>
    setOpenGroups((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  const handleLogout = async () => {
    await logout()
    navigate('/admin/login')
  }

  const filteredNavigation = navigation.filter((item) => {
    if (!item.roles) return true
    return item.roles.includes(user?.role || '')
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-2 px-4 py-5 border-b">
            <div className="p-1.5 bg-primary rounded-lg">
              <Flame className="h-6 w-6 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold text-foreground">ImporgasJJ</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="ml-auto lg:hidden text-muted-foreground hover:text-foreground"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {filteredNavigation.map((item) => {
              if (item.children) {
                const isGroupOpen = openGroups.has(item.name)
                const isGroupActive = item.children.some((c) =>
                  location.pathname.startsWith(c.href)
                )
                return (
                  <div key={item.name}>
                    {/* Group toggle button */}
                    <button
                      onClick={() => toggleGroup(item.name)}
                      className={cn(
                        'w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                        isGroupActive
                          ? 'text-primary bg-primary/10'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      )}
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      <span className="flex-1 text-left">{item.name}</span>
                      <ChevronRight
                        className={cn(
                          'h-4 w-4 transition-transform duration-200',
                          isGroupOpen && 'rotate-90'
                        )}
                      />
                    </button>

                    {/* Children */}
                    <div
                      className={cn(
                        'overflow-hidden transition-all duration-200',
                        isGroupOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                      )}
                    >
                      <div className="ml-4 mt-1 space-y-0.5 border-l border-border pl-3">
                        {item.children
                          .filter((child) =>
                            !child.roles || child.roles.includes(user?.role || '')
                          )
                          .map((child) => {
                            const isChildActive = location.pathname.startsWith(child.href)
                            return (
                              <Link
                                key={child.name}
                                to={child.href}
                                onClick={() => setSidebarOpen(false)}
                                className={cn(
                                  'flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors',
                                  isChildActive
                                    ? 'bg-primary text-primary-foreground font-medium'
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                )}
                              >
                                <child.icon className="h-4 w-4 shrink-0" />
                                {child.name}
                              </Link>
                            )
                          })}
                      </div>
                    </div>
                  </div>
                )
              }

              // Regular item
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span className="flex-1">{item.name}</span>
                  {item.name === 'CRM Chat' && pendingChats > 0 && (
                    <span className="w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-[10px] flex items-center justify-center font-bold">
                      {pendingChats > 9 ? '9+' : pendingChats}
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="border-t p-3">
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-3 w-full px-3 py-2 rounded-md hover:bg-accent transition-colors"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium">
                  {user?.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
                </div>
                <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', userMenuOpen && 'rotate-180')} />
              </button>

              {userMenuOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-1 bg-popover border rounded-md shadow-md py-1">
                  <Link
                    to="/admin/perfil"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent"
                  >
                    <User className="h-4 w-4" />
                    Mi perfil
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-accent"
                  >
                    <LogOut className="h-4 w-4" />
                    Cerrar sesion
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-4 px-4 py-3 bg-background/95 backdrop-blur border-b lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex-1" />
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
