import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, Trash2, ShoppingCart, Check } from 'lucide-react'
import { useFavorites } from '../../context/FavoritesContext'
import { useCart } from '../../context/CartContext'
import { Product } from '../../types'

export default function FavoritesPage() {
  const { favorites, loading, removeFromFavorites } = useFavorites()
  const { addToCart } = useCart()
  const [removingIds, setRemovingIds] = useState<number[]>([])
  const [addedToCartIds, setAddedToCartIds] = useState<number[]>([])

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)

  const handleAddToCart = (favorite: any) => {
    const product: Product = {
      id: favorite.product.id.toString(),
      name: favorite.product.name,
      description: favorite.product.description || '',
      price: parseFloat(favorite.product.price),
      originalPrice: favorite.product.original_price ? parseFloat(favorite.product.original_price) : undefined,
      category: favorite.product.category_name || '',
      brand: favorite.product.brand_name || '',
      images: favorite.product.primary_image ? [favorite.product.primary_image] : [],
      rating: favorite.product.rating || 0,
      reviewsCount: favorite.product.reviews_count || 0,
      stock: favorite.product.total_stock || 0,
      specifications: {},
      isAvailable: favorite.product.is_available,
      discount: favorite.product.discount_percentage,
      slug: favorite.product.slug || '',
    }
    addToCart(product, 1)
    setAddedToCartIds(prev => [...prev, favorite.id])
    setTimeout(() => {
      setAddedToCartIds(prev => prev.filter(id => id !== favorite.id))
    }, 2000)
  }

  const handleRemove = async (favoriteId: number) => {
    setRemovingIds(prev => [...prev, favoriteId])
    try {
      await removeFromFavorites(favoriteId)
    } catch (error) {
      console.error('Error removing favorite:', error)
      setRemovingIds(prev => prev.filter(id => id !== favoriteId))
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#001575]"></div>
          <p className="mt-4 text-gray-600">Cargando favoritos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Heart className="w-8 h-8 text-red-500" />
            Mis Favoritos
          </h1>
          <p className="mt-2 text-gray-600">
            {favorites.length} {favorites.length === 1 ? 'producto guardado' : 'productos guardados'}
          </p>
        </div>

        {favorites.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            <Heart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No tienes productos favoritos
            </h3>
            <p className="text-gray-600 mb-6">
              Guarda productos para encontrarlos fácilmente más tarde
            </p>
            <Link
              to="/productos"
              className="inline-block px-6 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors"
            >
              Explorar productos
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {favorites.map((favorite) => (
              <div
                key={favorite.id}
                className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition-all ${
                  removingIds.includes(favorite.id) ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
                }`}
              >
                <Link to={`/producto/${favorite.product.id}`} className="block">
                  <div className="aspect-square bg-gray-100 relative">
                    {favorite.product.primary_image ? (
                      <img
                        src={favorite.product.primary_image}
                        alt={favorite.product.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        Sin imagen
                      </div>
                    )}
                    {favorite.product.discount_percentage > 0 && (
                      <div className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded-lg text-xs font-bold">
                        -{favorite.product.discount_percentage}%
                      </div>
                    )}
                  </div>
                </Link>

                <div className="p-4">
                  <Link to={`/producto/${favorite.product.id}`}>
                    <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 hover:text-[#001575] transition-colors">
                      {favorite.product.name}
                    </h3>
                  </Link>

                  <div className="mb-4">
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-[#001575]">
                        {formatPrice(favorite.product.price)}
                      </span>
                      {favorite.product.original_price && (
                        <span className="text-sm text-gray-500 line-through">
                          {formatPrice(favorite.product.original_price)}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAddToCart(favorite)}
                      disabled={addedToCartIds.includes(favorite.id)}
                      className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-semibold transition-all ${
                        addedToCartIds.includes(favorite.id)
                          ? 'bg-green-500 text-white'
                          : 'bg-[#001575] text-white hover:bg-[#00104f]'
                      }`}
                    >
                      {addedToCartIds.includes(favorite.id) ? (
                        <>
                          <Check className="w-4 h-4" />
                          Agregado
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="w-4 h-4" />
                          Agregar
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleRemove(favorite.id)}
                      disabled={removingIds.includes(favorite.id)}
                      className="px-4 py-2.5 bg-red-50 text-red-600 rounded-xl hover:bg-red-100 transition-colors disabled:opacity-50"
                     aria-label="Eliminar">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
