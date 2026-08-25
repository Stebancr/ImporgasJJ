import { useState, useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Menu, X, ShoppingCart, Search, ChevronDown, LogOut,
  User, Package, Heart, MapPin, CreditCard, Bell, Settings,
  Edit, Truck, Phone,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'

const navigation = [
  { name: 'Inicio', href: '/' },
  { name: 'Productos', href: '/productos' },
  { name: 'Nosotros', href: '/nosotros' },
  { name: 'Contacto', href: '/contacto' },
]

const userMenuItems = [
  { icon: User,       label: 'Mi perfil',          href: '/perfil' },
  { icon: Edit,       label: 'Editar información',  href: '/perfil' },
  { icon: Package,    label: 'Mis pedidos',          href: '/perfil' },
  { icon: Truck,      label: 'Rastrear pedidos',    href: '/seguimiento' },
  { icon: Heart,      label: 'Lista de favoritos',  href: '/perfil' },
  { icon: MapPin,     label: 'Direcciones',         href: '/perfil' },
  { icon: CreditCard, label: 'Métodos de pago',     href: '/perfil' },
  { icon: Bell,       label: 'Notificaciones',      href: '/perfil' },
  { icon: Settings,   label: 'Configuración',       href: '/perfil' },
]

export default function Header() {
  const { isAuthenticated, logout } = useAuth()
  const { totalItems } = useCart()
  const [isDrawerOpen, setIsDrawerOpen]     = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [searchQuery, setSearchQuery]       = useState('')
  const [isScrolled, setIsScrolled]         = useState(false)
  const location    = useLocation()
  const navigate    = useNavigate()
  const userMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => { setIsDrawerOpen(false); setIsUserMenuOpen(false) }, [location])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    document.body.style.overflow = isDrawerOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [isDrawerOpen])

  const isActive = (href: string) =>
    href === '/' ? location.pathname === '/' : location.pathname.startsWith(href)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/productos?search=${encodeURIComponent(searchQuery)}`)
      setIsDrawerOpen(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
    setIsUserMenuOpen(false)
    setIsDrawerOpen(false)
  }

  const FbIcon = () => (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>
  )
  const IgIcon = () => (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>
  )

  const socialLinks = [
    { href: 'https://www.facebook.com/share/1HLuktBrTn/', label: 'Facebook', icon: <FbIcon /> },
    { href: 'https://www.instagram.com/imporgas_jj', label: 'Instagram', icon: <IgIcon /> },
  ]

  return (
    <>
      <header className={`sticky top-0 z-50 transition-all duration-300 ${isScrolled ? 'shadow-lg shadow-black/10' : ''}`}>

        {/* Top bar */}
        <div className="hidden lg:block bg-[#001575] text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-9 text-sm">
              <span className="flex items-center gap-2 text-white/80">
                <span className="w-2 h-2 bg-[#F58634] rounded-full animate-pulse" />
                Servicio técnico especializado en equipos a gas
              </span>
              <div className="flex items-center gap-5">
                <a href="tel:+573165266734" className="flex items-center gap-1.5 text-white/90 hover:text-[#F58634] transition-colors font-medium">
                  <Phone className="w-3.5 h-3.5" />
                  316 526 6734
                </a>
                <span className="text-white/30">|</span>
                {socialLinks.map(({ href, label, icon }) => (
                  <a key={label} href={href} target="_blank" rel="noopener noreferrer"
                    className="text-white/70 hover:text-[#F58634] transition-colors" aria-label={label}>
                    {icon}
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Main header */}
        <div className={`bg-white transition-all duration-300 ${isScrolled ? 'bg-white/97 backdrop-blur-lg' : ''}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-4 h-16 lg:h-20">

              {/* Logo */}
              <Link to="/" className="flex-shrink-0 flex items-center group" aria-label="ImporGas JJ - Inicio">
                <img src="/logo_imporgas.svg" alt="ImporGas JJ S.A.S"
                  className="object-contain transition-transform duration-300 group-hover:scale-105"
                  style={{ height: '40px', width: 'auto' }} />
              </Link>

              {/* Search desktop */}
              <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-xl mx-4 lg:mx-8">
                <div className="relative w-full">
                  <input
                    type="search"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Buscar productos, servicios..."
                    className="w-full pl-5 pr-14 py-2.5 bg-[#f5f7fa] border-2 border-transparent rounded-xl text-sm focus:outline-none focus:border-[#001575] focus:bg-white transition-all placeholder:text-gray-400"
                    aria-label="Buscar productos"
                  />
                  <button type="submit"
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 bg-[#F58634] hover:bg-[#d4711e] rounded-lg flex items-center justify-center transition-colors"
                    aria-label="Buscar">
                    <Search className="w-4 h-4 text-white" />
                  </button>
                </div>
              </form>

              {/* Desktop nav */}
              <nav className="hidden lg:flex items-center gap-1" aria-label="Navegación principal">
                {navigation.map(item => (
                  <Link key={item.name} to={item.href}
                    className={`px-4 py-2 rounded-xl font-medium text-sm transition-all duration-200 ${
                      isActive(item.href)
                        ? 'text-[#001575] bg-[#e8ecff]'
                        : 'text-[#4B5563] hover:text-[#001575] hover:bg-[#f5f7fa]'
                    }`}>
                    {item.name}
                  </Link>
                ))}
              </nav>

              {/* Right actions */}
              <div className="flex items-center gap-1 lg:gap-2 ml-auto">

                {/* Cart */}
                <Link to="/carrito"
                  className="relative p-2.5 text-[#1A1D21] hover:text-[#001575] hover:bg-[#e8ecff] rounded-xl transition-colors"
                  aria-label={`Carrito (${totalItems} productos)`}>
                  <ShoppingCart className="w-6 h-6" />
                  {totalItems > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-[#F58634] text-white text-xs font-bold rounded-full flex items-center justify-center animate-scale-in">
                      {totalItems > 99 ? '99+' : totalItems}
                    </span>
                  )}
                </Link>

                {/* User dropdown - desktop */}
                {isAuthenticated ? (
                  <div className="hidden md:block relative" ref={userMenuRef}>
                    <button
                      onClick={() => setIsUserMenuOpen(v => !v)}
                      className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-[#e8ecff] transition-colors"
                      aria-haspopup="true" aria-expanded={isUserMenuOpen}>
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#001575] to-[#0022b3] flex items-center justify-center text-white text-sm font-bold shadow-sm">
                        U
                      </div>
                      <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isUserMenuOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {isUserMenuOpen && (
                      <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 animate-slide-down z-50">
                        <div className="px-4 py-3 border-b border-gray-100 mb-1">
                          <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold">Mi cuenta</p>
                        </div>
                        {userMenuItems.map(({ icon: Icon, label, href }) => (
                          <Link key={label} to={href}
                            className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-[#e8ecff] hover:text-[#001575] transition-colors mx-1 rounded-xl"
                            onClick={() => setIsUserMenuOpen(false)}>
                            <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            {label}
                          </Link>
                        ))}
                        <div className="border-t border-gray-100 mt-1 pt-1 px-1">
                          <button onClick={handleLogout}
                            className="flex items-center gap-3 w-full px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors rounded-xl">
                            <LogOut className="w-4 h-4 flex-shrink-0" />
                            Cerrar sesión
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <Link to="/login"
                    className="hidden md:flex items-center gap-2 px-4 py-2.5 bg-[#001575] hover:bg-[#00104f] text-white rounded-xl font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-[#001575]/25 hover:-translate-y-0.5 active:translate-y-0 text-sm">
                    <User className="w-4 h-4" />
                    Ingresar
                  </Link>
                )}

                {/* Hamburger */}
                <button
                  onClick={() => setIsDrawerOpen(v => !v)}
                  className="lg:hidden p-2.5 text-[#1A1D21] hover:text-[#001575] hover:bg-[#e8ecff] rounded-xl transition-colors"
                  aria-label="Menú principal" aria-expanded={isDrawerOpen}>
                  {isDrawerOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black/40 backdrop-blur-sm z-50 lg:hidden transition-opacity duration-300 ${isDrawerOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setIsDrawerOpen(false)} aria-hidden="true" />

      {/* Drawer */}
      <aside
        className={`fixed top-0 right-0 h-full w-[85vw] max-w-sm bg-white z-50 lg:hidden shadow-2xl flex flex-col transition-transform duration-300 ${isDrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}
        role="dialog" aria-modal="true" aria-label="Menú lateral">

        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-[#001575]">
          <img src="/logo_imporgas.svg" alt="ImporGas JJ S.A.S" style={{ height: '32px', width: 'auto', filter: 'brightness(0) invert(1)' }} />
          <button onClick={() => setIsDrawerOpen(false)} className="p-2 text-white/80 hover:text-white rounded-xl" aria-label="Cerrar menú">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <form onSubmit={handleSearch} className="mb-5">
            <div className="relative">
              <input type="search" placeholder="Buscar productos..." value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-4 pr-12 py-3 bg-[#f5f7fa] border-2 border-transparent rounded-xl text-sm focus:outline-none focus:border-[#001575] transition-all"
                aria-label="Buscar" />
              <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-[#F58634] rounded-lg flex items-center justify-center">
                <Search className="w-4 h-4 text-white" />
              </button>
            </div>
          </form>

          <a href="tel:+573165266734" className="flex items-center gap-3 px-4 py-3 bg-[#e8ecff] rounded-xl text-[#001575] font-semibold mb-5">
            <Phone className="w-5 h-5" />
            316 526 6734
          </a>

          <nav className="flex flex-col gap-1 mb-6" aria-label="Menú móvil">
            {navigation.map(item => (
              <Link key={item.name} to={item.href}
                className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition-all ${isActive(item.href) ? 'text-[#001575] bg-[#e8ecff]' : 'text-[#4B5563] hover:bg-[#f5f7fa]'}`}>
                {item.name}
                <ChevronDown className="w-4 h-4 -rotate-90 opacity-50" />
              </Link>
            ))}
          </nav>

          {isAuthenticated && (
            <div className="space-y-1">
              <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold px-4 mb-2">Mi cuenta</p>
              {userMenuItems.slice(0, 5).map(({ icon: Icon, label, href }) => (
                <Link key={label} to={href}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-[#e8ecff] hover:text-[#001575] rounded-xl transition-colors">
                  <Icon className="w-4 h-4 text-gray-400" />
                  {label}
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-gray-100 px-4 py-4">
          {isAuthenticated ? (
            <button onClick={handleLogout}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 border-2 border-red-100 text-red-600 rounded-xl font-semibold hover:bg-red-50 transition-colors">
              <LogOut className="w-4 h-4" />
              Cerrar sesión
            </button>
          ) : (
            <Link to="/login"
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors">
              <User className="w-4 h-4" />
              Ingresar
            </Link>
          )}
        </div>
      </aside>

      {/* Floating call button mobile */}
      <a href="tel:+573165266734"
        className="fixed bottom-24 right-4 z-40 lg:hidden w-14 h-14 bg-[#F58634] hover:bg-[#d4711e] text-white rounded-full shadow-xl flex items-center justify-center transition-all duration-300 hover:scale-110 active:scale-95"
        aria-label="Llamar a ImporGas JJ">
        <Phone className="w-6 h-6" />
      </a>
    </>
  )
}
