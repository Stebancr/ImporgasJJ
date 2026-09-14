import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ShoppingCart, Heart, Share2, Truck, Shield, Star, ChevronLeft, ChevronRight, Minus, Plus, Check } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import ProductReviews from '../../components/ProductReviews'
import { Product } from '../../types'
import { productsService } from '../../services/products'
import { useAuth } from '../../context/AuthContext'
import { useCart } from '../../context/CartContext'
import { useFavorites } from '../../context/FavoritesContext'
import './styles/ProductDetailPage.css'

// Fallback mock product while loading
const fallbackProduct: Product = {
  id: '1',
  name: 'Cargando producto...',
  description: '',
  price: 0,
  category: '',
  brand: '',
  images: ['https://placehold.co/600x600/f3f4f6/9ca3af?text=Cargando'],
  rating: 0,
  reviewsCount: 0,
  stock: 0,
  specifications: {},
  isAvailable: true,
}

function ProductDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { addToCart } = useCart()
  const { isFavorite, addToFavorites, removeByProduct } = useFavorites()
  const [selectedImage, setSelectedImage] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [activeTab, setActiveTab] = useState<'description' | 'specs' | 'reviews'>('description')
  const [product, setProduct] = useState<Product>(fallbackProduct)
  const [relatedProducts, setRelatedProducts] = useState<Product[]>([])
  const [_isLoading, setIsLoading] = useState(true)
  const [addedToCart, setAddedToCart] = useState(false)
  const [favLoading, setFavLoading] = useState(false)

  const reloadProduct = useCallback(() => {
    if (!id) return
    productsService.getById(id).then(setProduct).catch(() => {})
  }, [id])

  const isWishlisted = product.id !== '1' && isFavorite(parseInt(product.id))

  const handleToggleFavorite = async () => {
    if (!isAuthenticated) {
      navigate(`/login?redirect=/producto/${product.id}`)
      return
    }
    setFavLoading(true)
    try {
      if (isWishlisted) {
        await removeByProduct(parseInt(product.id))
      } else {
        await addToFavorites(parseInt(product.id))
      }
    } catch {
      // silent
    } finally {
      setFavLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    setIsLoading(true)
    productsService.getById(id)
      .then(p => {
        setProduct(p)
        return productsService.getRelated(id)
      })
      .then(related => setRelatedProducts(related.slice(0, 4)))
      .catch(() => { /* keep fallback */ })
      .finally(() => setIsLoading(false))
  }, [id])


  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const handleAddToCart = () => {
    if (!product.isAvailable || product.stock < 1 || quantity < 1) return
    addToCart(product, quantity)
    setAddedToCart(true)
    setTimeout(() => setAddedToCart(false), 2000)
  }

  const nextImage = () => {
    setSelectedImage((prev) => (prev + 1) % product.images.length)
  }

  const prevImage = () => {
    setSelectedImage((prev) => (prev - 1 + product.images.length) % product.images.length)
  }

  return (
    <div className="product-detail-page bg-gray-50 min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm mb-8">
          <Link to="/" className="text-gray-500 hover:text-blue-600">Inicio</Link>
          <span className="text-gray-400">/</span>
          <Link to="/productos" className="text-gray-500 hover:text-blue-600">Productos</Link>
          <span className="text-gray-400">/</span>
          <Link to={`/productos?category=${product.category}`} className="text-gray-500 hover:text-blue-600 capitalize">
            {product.category}
          </Link>
          <span className="text-gray-400">/</span>
          <span className="text-gray-900">{product.name}</span>
        </nav>

        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          <div className="grid lg:grid-cols-2 gap-8 p-6 lg:p-8">
            {/* Image Gallery */}
            <div>
              <div className="relative aspect-square bg-gray-100 rounded-xl overflow-hidden mb-4">
                <img
                  src={product.images[selectedImage]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
                {product.discount && (
                  <span className="absolute top-4 left-4 bg-red-500 text-white text-sm font-semibold px-3 py-1 rounded-full">
                    -{product.discount}%
                  </span>
                )}
                <button
                  onClick={prevImage}
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/80 rounded-full flex items-center justify-center hover:bg-white transition-colors"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  onClick={nextImage}
                  className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/80 rounded-full flex items-center justify-center hover:bg-white transition-colors"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {product.images.map((image, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedImage(index)}
                    className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-colors ${
                      selectedImage === index ? 'border-blue-600' : 'border-transparent'
                    }`}
                  >
                    <img src={image} alt={`${product.name} ${index + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>

            {/* Product Info */}
            <div>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <p className="text-sm text-blue-600 font-medium mb-1">{product.brand}</p>
                  <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">{product.name}</h1>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleToggleFavorite}
                    disabled={favLoading}
                    className={`p-2 border rounded-lg transition-colors ${
                      isWishlisted
                        ? 'bg-red-50 border-red-300 text-red-500'
                        : 'hover:bg-gray-50 text-gray-600'
                    }`}
                  >
                    <Heart className={`w-5 h-5 ${isWishlisted ? 'fill-current text-red-500' : ''}`} />
                  </button>
                  <button className="p-2 border rounded-lg hover:bg-gray-50 transition-colors">
                    <Share2 className="w-5 h-5 text-gray-600" />
                  </button>
                </div>
              </div>

              {/* Rating */}
              <div className="flex items-center gap-2 mb-6">
                <div className="flex">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-5 h-5 ${i < product.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`}
                    />
                  ))}
                </div>
                <span className="text-gray-600">({product.reviewsCount} reseñas)</span>
              </div>

              {/* Price */}
              <div className="flex items-baseline gap-3 mb-6">
                <span className="text-3xl font-bold text-gray-900">{formatPrice(product.price)}</span>
                {product.originalPrice && (
                  <span className="text-xl text-gray-400 line-through">{formatPrice(product.originalPrice)}</span>
                )}
              </div>

              {/* Stock Status */}
              <div className="flex items-center gap-2 mb-6">
                {product.isAvailable && product.stock > 0 ? (
                  <>
                    <Check className="w-5 h-5 text-green-500" />
                    <span className="text-green-600 font-medium">En stock ({product.stock} disponibles)</span>
                  </>
                ) : (
                  <span className="text-red-600 font-medium">Agotado</span>
                )}
              </div>

              {/* Quantity & Add to Cart */}
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <div className="flex items-center border rounded-lg">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="p-3 hover:bg-gray-50 transition-colors"
                  >
                    <Minus className="w-5 h-5" />
                  </button>
                  <span className="w-16 text-center font-medium">{quantity}</span>
                  <button
                    onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}
                    className="p-3 hover:bg-gray-50 transition-colors"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
                <button
                  onClick={handleAddToCart}
                  disabled={!product.isAvailable || product.stock < 1}
                  style={{ backgroundColor: addedToCart ? '#16a34a' : '#2563eb' }}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-8 rounded-lg font-semibold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
                >
                  {addedToCart ? (
                    <>
                      <Check className="w-5 h-5" />
                      Agregado al Carrito
                    </>
                  ) : (
                    <>
                      <ShoppingCart className="w-5 h-5" />
                      Agregar al Carrito
                    </>
                  )}
                </button>
              </div>

              {/* Benefits */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <Truck className="w-6 h-6 text-blue-600" />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">Envío Gratis</p>
                    <p className="text-xs text-gray-500">En compras +$500.000</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Shield className="w-6 h-6 text-green-600" />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">Garantía</p>
                    <p className="text-xs text-gray-500">5 años de garantía</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-t">
            <div className="flex border-b">
              {(['description', 'specs', 'reviews'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-4 font-medium transition-colors ${
                    activeTab === tab
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {tab === 'description' && 'Descripción'}
                  {tab === 'specs' && 'Especificaciones'}
                  {tab === 'reviews' && `Reseñas (${product.reviewsCount})`}
                </button>
              ))}
            </div>

            <div className="p-6 lg:p-8">
              {activeTab === 'description' && (
                <div className="prose max-w-none">
                  <p className="text-gray-600 leading-relaxed">{product.description || 'Sin descripción disponible.'}</p>
                </div>
              )}

              {activeTab === 'specs' && (
                <div>
                  {Object.keys(product.specifications).length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No hay especificaciones disponibles para este producto.</p>
                  ) : (
                    <div className="overflow-hidden rounded-lg border border-gray-200">
                      <table className="w-full text-sm">
                        <tbody>
                          {Object.entries(product.specifications).map(([key, value], index) => (
                            <tr key={key} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                              <td className="px-4 py-3 font-medium text-gray-700 w-1/3 border-b border-gray-100">{key}</td>
                              <td className="px-4 py-3 text-gray-900 border-b border-gray-100">{value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'reviews' && (
                <ProductReviews productId={Number(product.id)} average={product.rating} count={product.reviewsCount} onChanged={reloadProduct} />
              )}
            </div>
          </div>
        </div>

        {/* Related Products */}
        <section className="mt-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">Productos Relacionados</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {relatedProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

export default ProductDetailPage
