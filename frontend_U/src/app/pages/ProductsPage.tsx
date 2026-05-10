import './styles/ProductsPage.css'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal, X, ChevronDown, Grid3X3, LayoutList, Search } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import { Product, FilterOptions } from '../../types'

// Mock data
const allProducts: Product[] = [
  {
    id: '1',
    name: 'Calentador de Agua a Gas 13L Premium',
    description: 'Calentador de paso de alta eficiencia con encendido electronico',
    price: 650000,
    originalPrice: 750000,
    category: 'calentadores',
    brand: 'Haceb',
    images: ['https://placehold.co/400x400/FF6B35/white?text=Calentador+13L'],
    rating: 5,
    reviewsCount: 128,
    stock: 15,
    specifications: {},
    isAvailable: true,
    discount: 13,
  },
  {
    id: '2',
    name: 'Aire Acondicionado Split Inverter 12000 BTU',
    description: 'Aire inverter con tecnologia de ahorro energetico A++',
    price: 1850000,
    originalPrice: 2100000,
    category: 'aires',
    brand: 'Samsung',
    images: ['https://placehold.co/400x400/0066FF/white?text=Aire+Inverter'],
    rating: 4,
    reviewsCount: 89,
    stock: 8,
    specifications: {},
    isAvailable: true,
    discount: 12,
  },
  {
    id: '3',
    name: 'Regulador de Gas Alta Presion Industrial',
    description: 'Regulador industrial certificado con valvula de seguridad',
    price: 85000,
    category: 'reguladores',
    brand: 'Fisher',
    images: ['https://placehold.co/400x400/10B981/white?text=Regulador+Pro'],
    rating: 5,
    reviewsCount: 234,
    stock: 50,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '4',
    name: 'Kit Profesional de Instalacion de Gas',
    description: 'Kit completo con herramientas certificadas',
    price: 320000,
    originalPrice: 380000,
    category: 'herramientas',
    brand: 'Stanley',
    images: ['https://placehold.co/400x400/F59E0B/white?text=Kit+Pro'],
    rating: 4,
    reviewsCount: 67,
    stock: 12,
    specifications: {},
    isAvailable: true,
    discount: 16,
  },
  {
    id: '5',
    name: 'Calentador de Agua 10L Tiro Natural',
    description: 'Calentador economico para hogares pequenos',
    price: 450000,
    category: 'calentadores',
    brand: 'Challenger',
    images: ['https://placehold.co/400x400/FF6B35/white?text=Calentador+10L'],
    rating: 4,
    reviewsCount: 95,
    stock: 20,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '6',
    name: 'Aire Acondicionado Portatil 9000 BTU',
    description: 'Ideal para espacios pequenos y facil de mover',
    price: 1200000,
    category: 'aires',
    brand: 'LG',
    images: ['https://placehold.co/400x400/0066FF/white?text=Aire+Portatil'],
    rating: 3,
    reviewsCount: 45,
    stock: 5,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '7',
    name: 'Regulador de Gas Domestico',
    description: 'Para cilindros de uso residencial con seguridad',
    price: 35000,
    category: 'reguladores',
    brand: 'Coltgas',
    images: ['https://placehold.co/400x400/10B981/white?text=Regulador+Dom'],
    rating: 4,
    reviewsCount: 312,
    stock: 100,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '8',
    name: 'Detector de Fugas de Gas Digital',
    description: 'Detector portatil con alarma sonora y visual LED',
    price: 120000,
    category: 'herramientas',
    brand: 'Bosch',
    images: ['https://placehold.co/400x400/F59E0B/white?text=Detector+Pro'],
    rating: 5,
    reviewsCount: 78,
    stock: 25,
    specifications: {},
    isAvailable: true,
  },
]

const categories = [
  { value: '', label: 'Todas las categorias', count: allProducts.length },
  { value: 'calentadores', label: 'Calentadores', count: 45 },
  { value: 'aires', label: 'Aires Acondicionados', count: 32 },
  { value: 'reguladores', label: 'Reguladores', count: 28 },
  { value: 'herramientas', label: 'Herramientas', count: 56 },
]

const brands = ['Todas', 'Haceb', 'Samsung', 'LG', 'Fisher', 'Stanley', 'Bosch', 'Challenger', 'Coltgas']

const sortOptions = [
  { value: '', label: 'Relevancia' },
  { value: 'price-asc', label: 'Precio: Menor a Mayor' },
  { value: 'price-desc', label: 'Precio: Mayor a Menor' },
  { value: 'rating', label: 'Mejor Valorados' },
  { value: 'newest', label: 'Mas Recientes' },
]

function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [filters, setFilters] = useState<FilterOptions>({
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    minPrice: undefined,
    maxPrice: undefined,
    inStock: true,
    sortBy: undefined,
  })

  const updateFilter = (key: keyof FilterOptions, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    if (value) {
      searchParams.set(key, String(value))
    } else {
      searchParams.delete(key)
    }
    setSearchParams(searchParams)
  }

  const clearFilters = () => {
    setFilters({
      category: '',
      brand: '',
      minPrice: undefined,
      maxPrice: undefined,
      inStock: true,
      sortBy: undefined,
    })
    setSearchParams({})
  }

  const filteredProducts = allProducts.filter((product) => {
    if (filters.category && product.category !== filters.category) return false
    if (filters.brand && filters.brand !== 'Todas' && product.brand !== filters.brand) return false
    if (filters.minPrice && product.price < filters.minPrice) return false
    if (filters.maxPrice && product.price > filters.maxPrice) return false
    if (filters.inStock && !product.isAvailable) return false
    return true
  })

  const sortedProducts = [...filteredProducts].sort((a, b) => {
    switch (filters.sortBy) {
      case 'price-asc':
        return a.price - b.price
      case 'price-desc':
        return b.price - a.price
      case 'rating':
        return b.rating - a.rating
      default:
        return 0
    }
  })

  const activeFiltersCount = [
    filters.category,
    filters.brand && filters.brand !== 'Todas',
    filters.minPrice,
    filters.maxPrice,
  ].filter(Boolean).length

  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      {/* Header */}
      <div className="bg-white border-b border-[#E5E7EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-2">
                {filters.category 
                  ? categories.find(c => c.value === filters.category)?.label 
                  : 'Todos los Productos'
                }
              </h1>
              <p className="text-[#6B7280]">
                {sortedProducts.length} productos encontrados
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Mobile Filter Button */}
              <button
                onClick={() => setIsFilterOpen(true)}
                className="lg:hidden flex items-center gap-2 px-4 py-2.5 bg-white border border-[#E5E7EB] rounded-xl hover:border-[#0066FF] transition-colors"
              >
                <SlidersHorizontal className="w-5 h-5" />
                <span>Filtros</span>
                {activeFiltersCount > 0 && (
                  <span className="w-5 h-5 bg-[#0066FF] text-white text-xs rounded-full flex items-center justify-center">
                    {activeFiltersCount}
                  </span>
                )}
              </button>

              {/* View Mode Toggle */}
              <div className="hidden sm:flex items-center bg-[#F3F4F6] rounded-xl p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-lg transition-all ${
                    viewMode === 'grid' 
                      ? 'bg-white text-[#0066FF] shadow-sm' 
                      : 'text-[#6B7280] hover:text-[#1A1D21]'
                  }`}
                >
                  <Grid3X3 className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-all ${
                    viewMode === 'list' 
                      ? 'bg-white text-[#0066FF] shadow-sm' 
                      : 'text-[#6B7280] hover:text-[#1A1D21]'
                  }`}
                >
                  <LayoutList className="w-5 h-5" />
                </button>
              </div>
              
              {/* Sort Dropdown */}
              <div className="relative">
                <select
                  value={filters.sortBy || ''}
                  onChange={(e) => updateFilter('sortBy', e.target.value as FilterOptions['sortBy'])}
                  className="appearance-none px-4 py-2.5 pr-10 bg-white border border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] transition-colors cursor-pointer"
                >
                  {sortOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#6B7280] pointer-events-none" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Sidebar Filters - Desktop */}
          <aside className="hidden lg:block w-72 flex-shrink-0">
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 sticky top-28">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-[#1A1D21]">Filtros</h2>
                {activeFiltersCount > 0 && (
                  <button 
                    onClick={clearFilters} 
                    className="text-sm text-[#0066FF] hover:text-[#0052CC] font-medium"
                  >
                    Limpiar todo
                  </button>
                )}
              </div>

              {/* Search in category */}
              <div className="mb-6">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Buscar en esta categoria..."
                    className="w-full pl-10 pr-4 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all text-sm"
                  />
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>

              {/* Category Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Categoria</h3>
                <div className="space-y-2">
                  {categories.map((category) => (
                    <label 
                      key={category.value} 
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                        filters.category === category.value
                          ? 'bg-[#E6F0FF] text-[#0066FF]'
                          : 'hover:bg-[#F3F4F6] text-[#4B5563]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="category"
                          checked={filters.category === category.value}
                          onChange={() => updateFilter('category', category.value)}
                          className="w-4 h-4 text-[#0066FF] border-[#D1D5DB] focus:ring-[#0066FF]"
                        />
                        <span className="text-sm font-medium">{category.label}</span>
                      </div>
                      <span className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-0.5 rounded-full">
                        {category.count}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Brand Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Marca</h3>
                <select
                  value={filters.brand || 'Todas'}
                  onChange={(e) => updateFilter('brand', e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all text-sm"
                >
                  {brands.map((brand) => (
                    <option key={brand} value={brand}>
                      {brand}
                    </option>
                  ))}
                </select>
              </div>

              {/* Price Range */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Rango de Precio</h3>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minPrice || ''}
                      onChange={(e) => updateFilter('minPrice', e.target.value ? Number(e.target.value) : undefined)}
                      className="w-full px-3 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all text-sm"
                    />
                  </div>
                  <span className="text-[#9CA3AF] self-center">-</span>
                  <div className="flex-1">
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxPrice || ''}
                      onChange={(e) => updateFilter('maxPrice', e.target.value ? Number(e.target.value) : undefined)}
                      className="w-full px-3 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#0066FF] focus:bg-white transition-all text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Stock Filter */}
              <div>
                <label className="flex items-center gap-3 cursor-pointer">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={filters.inStock}
                      onChange={(e) => updateFilter('inStock', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-[#E5E7EB] rounded-full peer-checked:bg-[#0066FF] transition-colors" />
                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                  </div>
                  <span className="text-sm text-[#4B5563]">Solo productos disponibles</span>
                </label>
              </div>
            </div>
          </aside>

          {/* Products Grid */}
          <div className="flex-1">
            {sortedProducts.length > 0 ? (
              <div className={`grid gap-6 ${
                viewMode === 'grid' 
                  ? 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3' 
                  : 'grid-cols-1'
              }`}>
                {sortedProducts.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            ) : (
              <div className="text-center py-20 bg-white rounded-2xl border border-[#E5E7EB]">
                <div className="w-20 h-20 bg-[#F3F4F6] rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search className="w-10 h-10 text-[#9CA3AF]" />
                </div>
                <h3 className="text-xl font-semibold text-[#1A1D21] mb-2">
                  No se encontraron productos
                </h3>
                <p className="text-[#6B7280] mb-6">
                  Intenta ajustar los filtros o buscar algo diferente
                </p>
                <button 
                  onClick={clearFilters} 
                  className="px-6 py-2.5 bg-[#0066FF] text-white font-semibold rounded-xl hover:bg-[#0052CC] transition-colors"
                >
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Filter Modal */}
      {isFilterOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div 
            className="absolute inset-0 bg-black/50 backdrop-blur-sm" 
            onClick={() => setIsFilterOpen(false)} 
          />
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-sm bg-white shadow-2xl overflow-y-auto animate-slide-up">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-[#E5E7EB] px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[#1A1D21]">Filtros</h2>
              <button 
                onClick={() => setIsFilterOpen(false)}
                className="w-10 h-10 hover:bg-[#F3F4F6] rounded-xl flex items-center justify-center transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6">
              {/* Mobile Category Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Categoria</h3>
                <div className="space-y-2">
                  {categories.map((category) => (
                    <label 
                      key={category.value} 
                      className={`flex items-center justify-between px-3 py-3 rounded-xl cursor-pointer transition-all ${
                        filters.category === category.value
                          ? 'bg-[#E6F0FF] text-[#0066FF]'
                          : 'bg-[#F3F4F6] text-[#4B5563]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="category-mobile"
                          checked={filters.category === category.value}
                          onChange={() => updateFilter('category', category.value)}
                          className="w-4 h-4 text-[#0066FF]"
                        />
                        <span className="text-sm font-medium">{category.label}</span>
                      </div>
                      <span className="text-xs">{category.count}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Mobile Brand Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Marca</h3>
                <select
                  value={filters.brand || 'Todas'}
                  onChange={(e) => updateFilter('brand', e.target.value)}
                  className="w-full px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                >
                  {brands.map((brand) => (
                    <option key={brand} value={brand}>
                      {brand}
                    </option>
                  ))}
                </select>
              </div>

              {/* Mobile Price Range */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Rango de Precio</h3>
                <div className="flex gap-3">
                  <input
                    type="number"
                    placeholder="Min"
                    value={filters.minPrice || ''}
                    onChange={(e) => updateFilter('minPrice', e.target.value ? Number(e.target.value) : undefined)}
                    className="flex-1 px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                  />
                  <input
                    type="number"
                    placeholder="Max"
                    value={filters.maxPrice || ''}
                    onChange={(e) => updateFilter('maxPrice', e.target.value ? Number(e.target.value) : undefined)}
                    className="flex-1 px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Apply Button */}
            <div className="sticky bottom-0 bg-white border-t border-[#E5E7EB] p-4 flex gap-3">
              <button
                onClick={clearFilters}
                className="flex-1 py-3 border border-[#E5E7EB] text-[#4B5563] rounded-xl font-semibold hover:bg-[#F3F4F6] transition-colors"
              >
                Limpiar
              </button>
              <button
                onClick={() => setIsFilterOpen(false)}
                className="flex-1 py-3 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white rounded-xl font-semibold hover:shadow-lg transition-all"
              >
                Ver {sortedProducts.length} productos
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProductsPage
