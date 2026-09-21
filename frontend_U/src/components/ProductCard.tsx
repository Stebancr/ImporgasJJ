import { Link, useNavigate } from 'react-router-dom'
import { ShoppingCart, Star, Heart, Eye, Check } from 'lucide-react'
import { useState } from 'react'
import { Product } from '../types'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { useFavorites } from '../context/FavoritesContext'

interface ProductCardProps {
  product: Product
}

function ProductCard({ product }: ProductCardProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { addToCart } = useCart()
  const { isFavorite, addToFavorites, removeByProduct } = useFavorites()
  const [favLoading, setFavLoading] = useState(false)
  const [addedToCart, setAddedToCart] = useState(false)

  const isWishlisted = isFavorite(parseInt(product.id))

  const handleToggleFavorite = async (e: React.MouseEvent) => {
    e.preventDefault()
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

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault()
    addToCart(product, 1)
    setAddedToCart(true)
    setTimeout(() => setAddedToCart(false), 2000)
  }

  return (
    <div 
      className="group min-w-0 bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden border border-[#E5E7EB] hover:border-[#001575]/20"
    >
      {/* Image Container */}
      <div className="relative aspect-square overflow-hidden bg-[#F9FAFB]">
        <Link to={`/producto/${product.id}`}>
          <img
            src={product.images[0] || 'https://placehold.co/400x400/f3f4f6/9ca3af?text=Producto'}
            alt={product.name} loading="lazy" decoding="async" width={400} height={400}
            className="w-full h-full object-contain group-hover:scale-110 transition-transform duration-500"
          />
        </Link>
        
        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-2">
          {product.discount && (
            <span className="px-2.5 py-1 bg-gradient-to-r from-[#EF4444] to-[#DC2626] text-white text-xs font-bold rounded-lg shadow-lg">
              -{product.discount}%
            </span>
          )}
          {product.isFeatured && (
            <span className="px-2.5 py-1 bg-gradient-to-r from-[#001575] to-[#00104f] text-white text-xs font-bold rounded-lg shadow-lg">
              Destacado
            </span>
          )}
        </div>

        {/* Quick Actions */}
        <div 
          className={`absolute top-3 right-3 flex flex-col gap-2 transition-all duration-300 ${
            'opacity-100 translate-x-0'
          }`}
        >
          <button
            aria-label={isWishlisted ? "Quitar de favoritos" : "Agregar a favoritos"} aria-pressed={isWishlisted}
            onClick={handleToggleFavorite}
            disabled={favLoading}
            className={`w-11 h-11 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 ${
              isWishlisted
                ? 'bg-[#EF4444] text-white hover:bg-[#DC2626]'
                : 'bg-white text-[#6B7280] hover:text-[#EF4444] hover:bg-red-50'
            } ${
              favLoading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <Heart className={`w-4 h-4 ${
              isWishlisted ? 'fill-current' : ''
            }`} />
          </button>
          <Link
            to={`/producto/${product.id}`}
            aria-label={`Ver ${product.name}`} className="w-11 h-11 bg-white rounded-full flex items-center justify-center shadow-lg text-[#6B7280] hover:text-[#001575] transition-colors"
          >
            <Eye className="w-4 h-4" />
          </Link>
        </div>

        {/* Out of Stock Overlay */}
        {!product.isAvailable && (
          <div className="absolute inset-0 bg-[#1A1D21]/60 backdrop-blur-sm flex items-center justify-center">
            <span className="px-4 py-2 bg-white text-[#1A1D21] font-semibold rounded-lg shadow-lg">
              Agotado
            </span>
          </div>
        )}

      </div>

      {/* Content */}
      <div className="p-4 lg:p-5">
        {/* Brand */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-[#001575] bg-[#e8ecff] px-2 py-0.5 rounded-md">
            {product.brand}
          </span>
          <span className="text-xs text-[#6B7280]">
            {product.isAvailable ? (product.stock > 0 ? `${product.stock} disponibles` : 'Disponible para pedido') : 'No disponible'}
          </span>
        </div>

        {/* Name */}
        <Link to={`/producto/${product.id}`}>
          <h3 className="font-semibold text-[#1A1D21] mb-2 line-clamp-2 group-hover:text-[#001575] transition-colors leading-snug">
            {product.name}
          </h3>
        </Link>

        {/* Rating */}
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center gap-0.5">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={`w-4 h-4 ${
                  i < product.rating 
                    ? 'text-[#F59E0B] fill-[#F59E0B]' 
                    : 'text-[#E5E7EB] fill-[#E5E7EB]'
                }`}
              />
            ))}
          </div>
          <span className="text-sm text-[#6B7280]">
            ({product.reviewsCount})
          </span>
        </div>

        {/* Price */}
        <div className="flex flex-wrap items-baseline gap-2 mb-4">
          <span className="text-xl font-bold text-[#1A1D21]">
            {formatPrice(product.price)}
          </span>
          {product.originalPrice && (
            <span className="text-sm text-[#9CA3AF] line-through">
              {formatPrice(product.originalPrice)}
            </span>
          )}
        </div>

        {/* Mobile: always-visible add-to-cart */}
        <button
          onClick={handleAddToCart}
          disabled={!product.isAvailable}
          className={`w-full flex items-center justify-center gap-2 text-white py-2.5 rounded-xl font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all ${
            addedToCart
              ? 'bg-gradient-to-r from-[#10B981] to-[#059669] scale-95'
              : 'bg-gradient-to-r from-[#001575] to-[#00104f] active:scale-95'
          }`}
        >
          {addedToCart ? (
            <>
              <Check className="w-4 h-4" />
              <span>¡Agregado!</span>
            </>
          ) : (
            <>
              <ShoppingCart className="w-4 h-4" />
              <span>{product.isAvailable ? 'Agregar al carrito' : 'Agotado'}</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export default ProductCard
