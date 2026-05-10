import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, ShoppingCart, User, Search, Flame, ChevronDown } from 'lucide-react'

function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isScrolled, setIsScrolled] = useState(false)
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    setIsMenuOpen(false)
  }, [location])

  const navigation = [
    { name: 'Inicio', href: '/' },
    { name: 'Productos', href: '/productos' },
    { name: 'Seguimiento', href: '/seguimiento' },
    { name: 'Contacto', href: '/contacto' },
  ]

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      window.location.href = `/productos?search=${encodeURIComponent(searchQuery)}`
    }
  }

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  return (
    <header 
      className={`sticky top-0 z-50 transition-all duration-300 ${
        isScrolled 
          ? 'bg-white/95 backdrop-blur-lg shadow-lg shadow-black/5' 
          : 'bg-white'
      }`}
    >
      {/* Top Bar */}
      <div className="hidden lg:block bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-9 text-sm">
            <div className="flex items-center gap-6">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                Envio gratis en compras +$500.000
              </span>
            </div>
            <div className="flex items-center gap-6">
              <a href="tel:+573001234567" className="hover:text-white/80 transition-colors">
                +57 300 123 4567
              </a>
              <span className="text-white/40">|</span>
              <a href="mailto:info@gasstore.com" className="hover:text-white/80 transition-colors">
                info@gasstore.com
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative">
              <div className="absolute inset-0 bg-[#FF6B35]/20 rounded-xl blur-lg group-hover:bg-[#FF6B35]/30 transition-colors" />
              <div className="relative w-10 h-10 lg:w-11 lg:h-11 bg-gradient-to-br from-[#FF6B35] to-[#E55A2B] rounded-xl flex items-center justify-center shadow-lg shadow-[#FF6B35]/25">
                <Flame className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-xl lg:text-2xl font-bold text-[#1A1D21] tracking-tight">GasStore</span>
              <span className="hidden lg:block text-xs text-[#6B7280] -mt-0.5">Tu tienda de confianza</span>
            </div>
          </Link>

          {/* Search Bar - Desktop */}
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-xl mx-8">
            <div className={`relative w-full transition-all duration-300 ${isSearchFocused ? 'scale-[1.02]' : ''}`}>
              <input
                type="text"
                placeholder="Buscar calentadores, aires, reguladores..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
                className={`w-full pl-12 pr-4 py-3 bg-[#F3F4F6] border-2 rounded-xl transition-all duration-300 text-[#1A1D21] placeholder:text-[#9CA3AF] ${
                  isSearchFocused 
                    ? 'border-[#0066FF] bg-white shadow-lg shadow-[#0066FF]/10' 
                    : 'border-transparent hover:bg-[#E5E7EB]'
                }`}
              />
              <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${
                isSearchFocused ? 'text-[#0066FF]' : 'text-[#9CA3AF]'
              }`} />
            </div>
          </form>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`relative px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  isActive(item.href)
                    ? 'text-[#0066FF] bg-[#E6F0FF]'
                    : 'text-[#4B5563] hover:text-[#0066FF] hover:bg-[#F3F4F6]'
                }`}
              >
                {item.name}
                {isActive(item.href) && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 bg-[#0066FF] rounded-full" />
                )}
              </Link>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-2 lg:gap-3">
            <Link 
              to="/carrito" 
              className="relative p-2.5 lg:p-3 text-[#4B5563] hover:text-[#0066FF] hover:bg-[#F3F4F6] rounded-xl transition-all duration-200 group"
            >
              <ShoppingCart className="w-5 h-5 lg:w-6 lg:h-6" />
              <span className="absolute -top-0.5 -right-0.5 lg:top-0 lg:right-0 min-w-[20px] h-5 bg-gradient-to-r from-[#FF6B35] to-[#E55A2B] text-white text-xs font-bold rounded-full flex items-center justify-center px-1.5 shadow-lg shadow-[#FF6B35]/30 group-hover:scale-110 transition-transform">
                0
              </span>
            </Link>
            
            <Link 
              to="/login" 
              className="hidden md:flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[#0066FF]/25 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
            >
              <User className="w-4 h-4" />
              <span>Ingresar</span>
            </Link>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="lg:hidden p-2.5 text-[#4B5563] hover:text-[#0066FF] hover:bg-[#F3F4F6] rounded-xl transition-colors"
            >
              {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <div 
        className={`lg:hidden absolute top-full left-0 right-0 bg-white border-t border-[#E5E7EB] shadow-xl transition-all duration-300 z-40 max-h-[calc(100dvh-4rem)] overflow-y-auto ${
          isMenuOpen 
            ? 'opacity-100 translate-y-0' 
            : 'opacity-0 -translate-y-4 pointer-events-none'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 py-4">
          {/* Mobile Search */}
          <form onSubmit={handleSearch} className="mb-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar productos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all"
              />
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
            </div>
          </form>

          {/* Mobile Navigation */}
          <nav className="flex flex-col gap-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition-all ${
                  isActive(item.href)
                    ? 'text-[#0066FF] bg-[#E6F0FF]'
                    : 'text-[#4B5563] hover:bg-[#F3F4F6]'
                }`}
              >
                {item.name}
                <ChevronDown className="w-4 h-4 -rotate-90" />
              </Link>
            ))}
          </nav>

          {/* Mobile Login Button */}
          <Link
            to="/login"
            className="mt-4 flex items-center justify-center gap-2 w-full px-5 py-3 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white rounded-xl font-semibold"
          >
            <User className="w-5 h-5" />
            <span>Ingresar</span>
          </Link>
        </div>
      </div>
    </header>
  )
}

export default Header
