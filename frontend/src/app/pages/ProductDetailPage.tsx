import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ShoppingCart, Heart, Share2, Truck, Shield, Star, ChevronLeft, ChevronRight, Minus, Plus, Check } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import { Product } from '../../types'
import './styles/ProductDetailPage.css'

// Mock product data
const productData: Product = {
  id: '1',
  name: 'Calentador de Agua a Gas 13 Litros - Tiro Forzado',
  description: 'Calentador de paso de alta eficiencia con tecnología de tiro forzado que garantiza una combustión segura. Ideal para hogares con múltiples puntos de agua. Incluye pantalla digital para control de temperatura y sistema de encendido electrónico.',
  price: 650000,
  originalPrice: 750000,
  category: 'calentadores',
  brand: 'Haceb',
  images: [
    'https://placehold.co/600x600/f97316/white?text=Calentador+1',
    'https://placehold.co/600x600/ea580c/white?text=Calentador+2',
    'https://placehold.co/600x600/c2410c/white?text=Calentador+3',
    'https://placehold.co/600x600/9a3412/white?text=Calentador+4',
  ],
  rating: 5,
  reviewsCount: 128,
  stock: 15,
  specifications: {
    'Capacidad': '13 Litros/min',
    'Tipo de Gas': 'Natural / Propano',
    'Encendido': 'Electrónico',
    'Tipo de Tiro': 'Forzado',
    'Potencia': '26 kW',
    'Dimensiones': '60 x 35 x 18 cm',
    'Peso': '12 kg',
    'Garantía': '5 años',
  },
  isAvailable: true,
  discount: 13,
}

const relatedProducts: Product[] = [
  {
    id: '5',
    name: 'Calentador de Agua 10L Tiro Natural',
    description: 'Calentador económico',
    price: 450000,
    category: 'calentadores',
    brand: 'Challenger',
    images: ['https://placehold.co/400x400/f97316/white?text=Calentador+10L'],
    rating: 4,
    reviewsCount: 95,
    stock: 20,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '3',
    name: 'Regulador de Gas Alta Presión',
    description: 'Regulador industrial',
    price: 85000,
    category: 'reguladores',
    brand: 'Fisher',
    images: ['https://placehold.co/400x400/22c55e/white?text=Regulador'],
    rating: 5,
    reviewsCount: 234,
    stock: 50,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '8',
    name: 'Detector de Fugas de Gas',
    description: 'Detector portátil',
    price: 120000,
    category: 'herramientas',
    brand: 'Bosch',
    images: ['https://placehold.co/400x400/eab308/white?text=Detector'],
    rating: 5,
    reviewsCount: 78,
    stock: 25,
    specifications: {},
    isAvailable: true,
  },
  {
    id: '4',
    name: 'Kit de Herramientas Instalación',
    description: 'Kit profesional',
    price: 320000,
    category: 'herramientas',
    brand: 'Stanley',
    images: ['https://placehold.co/400x400/eab308/white?text=Kit+Pro'],
    rating: 4,
    reviewsCount: 67,
    stock: 12,
    specifications: {},
    isAvailable: true,
    discount: 16,
    originalPrice: 380000,
  },
]

function ProductDetailPage() {
  const { id } = useParams()
  const [selectedImage, setSelectedImage] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [activeTab, setActiveTab] = useState<'description' | 'specs' | 'reviews'>('description')

  // In a real app, fetch product by id
  const product = productData
  console.log('Product ID:', id)

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(price)
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
                  <button className="p-2 border rounded-lg hover:bg-gray-50 transition-colors">
                    <Heart className="w-5 h-5 text-gray-600" />
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
                {product.isAvailable ? (
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
                  disabled={!product.isAvailable}
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-3 px-8 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  <ShoppingCart className="w-5 h-5" />
                  Agregar al Carrito
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
                  <p className="text-gray-600 leading-relaxed">{product.description}</p>
                  <h3 className="text-lg font-semibold text-gray-900 mt-6 mb-4">Características Principales</h3>
                  <ul className="space-y-2">
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">Tecnología de tiro forzado para mayor seguridad</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">Pantalla digital con control de temperatura</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">Encendido electrónico sin piloto</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-600">Compatible con gas natural y propano</span>
                    </li>
                  </ul>
                </div>
              )}

              {activeTab === 'specs' && (
                <div className="grid md:grid-cols-2 gap-4">
                  {Object.entries(product.specifications).map(([key, value]) => (
                    <div key={key} className="flex justify-between py-3 border-b">
                      <span className="text-gray-600">{key}</span>
                      <span className="font-medium text-gray-900">{value}</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'reviews' && (
                <div className="text-center py-8">
                  <p className="text-gray-500">Las reseñas estarán disponibles próximamente</p>
                </div>
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
