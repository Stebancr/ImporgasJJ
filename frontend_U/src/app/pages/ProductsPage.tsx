import './styles/ProductsPage.css'
import api from '../../services/api'
import { useMobileDrawer } from '../../hooks/useMobileDrawer'
import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal, X, ChevronDown, Grid3X3, LayoutList, Search } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import { Product } from '../../types'
import { productsService } from '../../services/products'

interface CategoryData {
  id: number
  name: string
  slug: string
  product_count: number
}

interface BrandData {
  id: number
  name: string
  slug: string
  product_count: number
}

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
  const filterRef = useMobileDrawer(isFilterOpen, () => setIsFilterOpen(false))
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<CategoryData[]>([])
  const [brands, setBrands] = useState<BrandData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [totalProducts, setTotalProducts] = useState(0)
  
  const [loadError, setLoadError] = useState('')
  const requestId = useRef(0)

  // Filtros
  const [categoryId, setCategoryId] = useState(searchParams.get('category_id') || '')
  const [brandId, setBrandId] = useState(searchParams.get('brand_id') || '')
  const [minPrice, setMinPrice] = useState(searchParams.get('min_price') || '')
  const [maxPrice, setMaxPrice] = useState(searchParams.get('max_price') || '')
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || '')
  const [onlyAvailable, setOnlyAvailable] = useState(true)

  // Cargar productos con filtros
  useEffect(() => {
    const timer = setTimeout(() => { void loadProducts() }, 250)
    return () => { clearTimeout(timer); requestId.current += 1 }
  }, [categoryId, brandId, minPrice, maxPrice, searchQuery, sortBy, onlyAvailable])

  const loadProducts = async () => {
    const id = ++requestId.current
    setIsLoading(true)
    setLoadError('')
    try {
      const response = await productsService.getAll({
        categoryId: categoryId ? parseInt(categoryId) : undefined,
        brandId: brandId ? parseInt(brandId) : undefined,
        minPrice: minPrice ? parseFloat(minPrice) : undefined,
        maxPrice: maxPrice ? parseFloat(maxPrice) : undefined,
        search: searchQuery || undefined,
        sortBy: (sortBy as '' | 'rating' | 'price-asc' | 'price-desc' | 'newest') || undefined,
        inStock: onlyAvailable,
      })
      
      if (id !== requestId.current) return
      setProducts(response)
    } catch {
      if (id === requestId.current) setLoadError('No pudimos cargar los productos. Intenta de nuevo.')
    } finally {
      if (id === requestId.current) setIsLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    api.get<{ categories: CategoryData[]; brands: BrandData[] }>('/products?per_page=1')
      .then(data => { if (active) { setCategories(data.categories || []); setBrands(data.brands || []) } })
      .catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    setCategoryId(searchParams.get('category_id') || '')
    setBrandId(searchParams.get('brand_id') || '')
    setMinPrice(searchParams.get('min_price') || '')
    setMaxPrice(searchParams.get('max_price') || '')
    setSearchQuery(searchParams.get('search') || '')
    setSortBy(searchParams.get('sort') || '')
  }, [searchParams])

  const updateFilter = (key: string, value: string) => {
    // Actualizar URL params
    if (value) {
      searchParams.set(key, value)
    } else {
      searchParams.delete(key)
    }
    setSearchParams(searchParams)

    // Actualizar estado local
    switch (key) {
      case 'category_id':
        setCategoryId(value)
        break
      case 'brand_id':
        setBrandId(value)
        break
      case 'min_price':
        setMinPrice(value)
        break
      case 'max_price':
        setMaxPrice(value)
        break
      case 'search':
        setSearchQuery(value)
        break
      case 'sort':
        setSortBy(value)
        break
    }
  }

  const clearFilters = () => {
    setCategoryId('')
    setBrandId('')
    setMinPrice('')
    setMaxPrice('')
    setSearchQuery('')
    setSortBy('')
    setSearchParams({})
  }

  const activeFiltersCount = [
    categoryId,
    brandId,
    minPrice,
    maxPrice,
  ].filter(Boolean).length

  const selectedCategory = categories.find(c => c.id.toString() === categoryId)

  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      {loadError && <div role="alert" className="max-w-7xl mx-auto p-4 text-red-700">{loadError} <button className="underline min-h-11" onClick={() => void loadProducts()}>Reintentar</button></div>}
      {/* Header */}
      <div className="bg-white border-b border-[#E5E7EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-2">
                {selectedCategory ? selectedCategory.name : 'Todos los Productos'}
              </h1>
              <p className="text-[#6B7280]">
                {products.length} productos encontrados
              </p>
            </div>
            
            <div className="flex flex-wrap min-w-0 items-center gap-3">
              {/* Mobile Filter Button */}
              <button
                onClick={() => setIsFilterOpen(true)}
                className="lg:hidden flex items-center gap-2 px-4 py-2.5 bg-white border border-[#E5E7EB] rounded-xl hover:border-[#001575] transition-colors"
              >
                <SlidersHorizontal className="w-5 h-5" />
                <span>Filtros</span>
                {activeFiltersCount > 0 && (
                  <span className="w-5 h-5 bg-[#001575] text-white text-xs rounded-full flex items-center justify-center">
                    {activeFiltersCount}
                  </span>
                )}
              </button>

              {/* View Mode Toggle */}
              <div className="hidden sm:flex items-center bg-[#F3F4F6] rounded-xl p-1">
                <button
                  aria-label="Vista de cuadrícula" onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-lg transition-all ${
                    viewMode === 'grid' 
                      ? 'bg-white text-[#001575] shadow-sm' 
                      : 'text-[#6B7280] hover:text-[#1A1D21]'
                  }`}
                >
                  <Grid3X3 className="w-5 h-5" />
                </button>
                <button
                  aria-label="Vista de lista" onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-all ${
                    viewMode === 'list' 
                      ? 'bg-white text-[#001575] shadow-sm' 
                      : 'text-[#6B7280] hover:text-[#1A1D21]'
                  }`}
                >
                  <LayoutList className="w-5 h-5" />
                </button>
              </div>
              
              {/* Sort Dropdown */}
              <div className="relative min-w-0 max-w-full flex-1 sm:flex-none">
                <select
                  aria-label="Ordenar productos"
                  value={sortBy}
                  onChange={(e) => updateFilter('sort', e.target.value)}
                  className="w-full min-w-0 appearance-none px-4 py-2.5 pr-10 bg-white border border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-colors cursor-pointer"
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
                    className="text-sm text-[#001575] hover:text-[#00104f] font-medium"
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
                    value={searchQuery}
                    onChange={(e) => updateFilter('search', e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#001575] focus:bg-white transition-all text-sm"
                   aria-label="Buscar en esta categoria..." />
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>

              {/* Category Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Categoria</h3>
                <div className="space-y-2">
                  <label 
                    className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                      !categoryId
                        ? 'bg-[#e8ecff] text-[#001575]'
                        : 'hover:bg-[#F3F4F6] text-[#4B5563]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="category"
                        checked={!categoryId}
                        onChange={() => updateFilter('category_id', '')}
                        className="w-4 h-4 text-[#001575] border-[#D1D5DB] focus:ring-[#001575]"
                      />
                      <span className="text-sm font-medium">Todas las categorias</span>
                    </div>
                    <span className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-0.5 rounded-full">
                      {categories.reduce((sum, c) => sum + c.product_count, 0)}
                    </span>
                  </label>
                  {categories.map((category) => (
                    <label 
                      key={category.id} 
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                        categoryId === category.id.toString()
                          ? 'bg-[#e8ecff] text-[#001575]'
                          : 'hover:bg-[#F3F4F6] text-[#4B5563]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="category"
                          checked={categoryId === category.id.toString()}
                          onChange={() => updateFilter('category_id', category.id.toString())}
                          className="w-4 h-4 text-[#001575] border-[#D1D5DB] focus:ring-[#001575]"
                        />
                        <span className="text-sm font-medium">{category.name}</span>
                      </div>
                      <span className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-0.5 rounded-full">
                        {category.product_count}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Brand Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Marca</h3>
                <select
                  value={brandId}
                  onChange={(e) => updateFilter('brand_id', e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#001575] focus:bg-white transition-all text-sm"
                >
                  <option value="">Todas</option>
                  {brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>
                      {brand.name}
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
                      value={minPrice}
                      onChange={(e) => updateFilter('min_price', e.target.value)}
                      className="w-full px-3 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#001575] focus:bg-white transition-all text-sm"
                     aria-label="Min" />
                  </div>
                  <span className="text-[#9CA3AF] self-center">-</span>
                  <div className="flex-1">
                    <input
                      type="number"
                      placeholder="Max"
                      value={maxPrice}
                      onChange={(e) => updateFilter('max_price', e.target.value)}
                      className="w-full px-3 py-2.5 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:border-[#001575] focus:bg-white transition-all text-sm"
                     aria-label="Max" />
                  </div>
                </div>
              </div>

              {/* Stock Filter */}
              <div>
                <label className="flex items-center gap-3 cursor-pointer">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={onlyAvailable}
                      onChange={(e) => setOnlyAvailable(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-[#E5E7EB] rounded-full peer-checked:bg-[#001575] transition-colors" />
                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                  </div>
                  <span className="text-sm text-[#4B5563]">Solo productos disponibles</span>
                </label>
              </div>
            </div>
          </aside>

          {/* Products Grid */}
          <div className="flex-1 min-w-0">
            {isLoading ? (
              <div className="text-center py-20">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#001575] border-t-transparent" />
                <p className="text-[#6B7280] mt-4">Cargando productos...</p>
              </div>
            ) : products.length > 0 ? (
              <div className={`grid gap-6 ${
                viewMode === 'grid' 
                  ? 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3' 
                  : 'grid-cols-1'
              }`}>
                {products.map((product) => (
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
                  className="px-6 py-2.5 bg-[#001575] text-white font-semibold rounded-xl hover:bg-[#00104f] transition-colors"
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
        <div className="fixed inset-0 z-[60] lg:hidden">
          <div 
            className="absolute inset-0 bg-black/50 backdrop-blur-sm" 
            onClick={() => setIsFilterOpen(false)} 
          />
          <div ref={filterRef as React.RefObject<HTMLDivElement>} role="dialog" aria-modal="true" aria-label="Filtros de productos" className="absolute right-0 top-0 bottom-0 w-full max-w-sm bg-white shadow-2xl overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-[#E5E7EB] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-semibold text-[#1A1D21]">Filtros</h2>
              <button 
                onClick={() => setIsFilterOpen(false)}
                aria-label="Cerrar filtros"
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
                  <label 
                    className={`flex items-center justify-between px-3 py-3 rounded-xl cursor-pointer transition-all ${
                      !categoryId
                        ? 'bg-[#e8ecff] text-[#001575]'
                        : 'bg-[#F3F4F6] text-[#4B5563]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="category-mobile"
                        checked={!categoryId}
                        onChange={() => { updateFilter('category_id', ''); setIsFilterOpen(false) }}
                        className="w-4 h-4 text-[#001575]"
                      />
                      <span className="text-sm font-medium">Todas</span>
                    </div>
                  </label>
                  {categories.map((category) => (
                    <label 
                      key={category.id} 
                      className={`flex items-center justify-between px-3 py-3 rounded-xl cursor-pointer transition-all ${
                        categoryId === category.id.toString()
                          ? 'bg-[#e8ecff] text-[#001575]'
                          : 'bg-[#F3F4F6] text-[#4B5563]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="category-mobile"
                          checked={categoryId === category.id.toString()}
                          onChange={() => { updateFilter('category_id', category.id.toString()); setIsFilterOpen(false) }}
                          className="w-4 h-4 text-[#001575]"
                        />
                        <span className="text-sm font-medium">{category.name}</span>
                      </div>
                      <span className="text-xs">{category.product_count}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Mobile Brand Filter */}
              <div className="mb-6">
                <h3 className="font-semibold text-[#1A1D21] mb-3">Marca</h3>
                <select
                  value={brandId}
                  onChange={(e) => updateFilter('brand_id', e.target.value)}
                  className="w-full px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                >
                  <option value="">Todas</option>
                  {brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>
                      {brand.name}
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
                    value={minPrice}
                    onChange={(e) => updateFilter('min_price', e.target.value)}
                    className="min-w-0 w-full flex-1 px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                   aria-label="Min" />
                  <input
                    type="number"
                    placeholder="Max"
                    value={maxPrice}
                    onChange={(e) => updateFilter('max_price', e.target.value)}
                    className="min-w-0 w-full flex-1 px-4 py-3 bg-[#F3F4F6] rounded-xl text-sm"
                   aria-label="Max" />
                </div>
              </div>

              {/* Apply Button */}
              <button 
                onClick={() => setIsFilterOpen(false)} 
                className="w-full py-3 bg-[#001575] text-white font-semibold rounded-xl hover:bg-[#00104f] transition-colors"
              >
                Aplicar Filtros
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProductsPage
