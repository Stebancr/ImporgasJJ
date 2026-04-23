import { Link } from 'react-router-dom'
import { ShoppingCart, Star, Heart, Eye } from 'lucide-react'
import { useState } from 'react'
import { Product } from '../types'

interface ProductCardProps {
  product: Product
}

function ProductCard({ product }: ProductCardProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [isWishlisted, setIsWishlisted] = useState(false)

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  return (
    <div 
      className="group bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden border border-[#E5E7EB] hover:border-[#0066FF]/20"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Image Container */}
      <div className="relative aspect-square overflow-hidden bg-[#F9FAFB]">
        <Link to={`/producto/${product.id}`}>
          <img
            src={product.images[0] || 'https://placehold.co/400x400/f3f4f6/9ca3af?text=Producto'}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
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
            <span className="px-2.5 py-1 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white text-xs font-bold rounded-lg shadow-lg">
              Destacado
            </span>
          )}
        </div>

        {/* Quick Actions */}
        <div 
          className={`absolute top-3 right-3 flex flex-col gap-2 transition-all duration-300 ${
            isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
          }`}
        >
          <button
            onClick={() => setIsWishlisted(!isWishlisted)}
            className={`w-9 h-9 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 ${
              isWishlisted 
                ? 'bg-[#EF4444] text-white' 
                : 'bg-white text-[#6B7280] hover:text-[#EF4444]'
            }`}
          >
            <Heart className={`w-4 h-4 ${isWishlisted ? 'fill-current' : ''}`} />
          </button>
          <Link
            to={`/producto/${product.id}`}
            className="w-9 h-9 bg-white rounded-full flex items-center justify-center shadow-lg text-[#6B7280] hover:text-[#0066FF] transition-colors"
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

        {/* Add to Cart - Hover (desktop only) */}
        <div 
          className={`hidden sm:block absolute bottom-0 left-0 right-0 p-4 transition-all duration-300 ${
            isHovered && product.isAvailable ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <button
            disabled={!product.isAvailable}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl hover:shadow-[#0066FF]/25 transition-all disabled:opacity-50"
          >
            <ShoppingCart className="w-5 h-5" />
            <span>Agregar al carrito</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 lg:p-5">
        {/* Brand */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-[#0066FF] bg-[#E6F0FF] px-2 py-0.5 rounded-md">
            {product.brand}
          </span>
          <span className="text-xs text-[#6B7280]">
            {product.stock > 0 ? `${product.stock} disponibles` : 'Sin stock'}
          </span>
        </div>

        {/* Name */}
        <Link to={`/producto/${product.id}`}>
          <h3 className="font-semibold text-[#1A1D21] mb-2 line-clamp-2 group-hover:text-[#0066FF] transition-colors leading-snug">
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
        <div className="flex items-baseline gap-2 mb-4">
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
          disabled={!product.isAvailable}
          className="sm:hidden w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white py-2.5 rounded-xl font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all"
        >
          <ShoppingCart className="w-4 h-4" />
          <span>{product.isAvailable ? 'Agregar al carrito' : 'Agotado'}</span>
        </button>
      </div>
    </div>
  )
}

export default ProductCard
