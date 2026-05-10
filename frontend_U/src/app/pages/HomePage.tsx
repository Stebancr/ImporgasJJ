import './styles/HomePage.css'
import { Link } from 'react-router-dom'
import { ArrowRight, Truck, Shield, Headphones, Wrench, Play, Zap, ThermometerSun, Gauge, PenToolIcon as Tool } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import GoogleMap from '../../components/GoogleMap'
import { Product } from '../../types'

// Mock data
const featuredProducts: Product[] = [
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
    isFeatured: true,
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
    isFeatured: true,
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
    isFeatured: true,
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
    isFeatured: true,
    discount: 16,
  },
]

const categories = [
  { 
    name: 'Calentadores', 
    icon: ThermometerSun, 
    slug: 'calentadores', 
    count: 45,
    color: 'from-[#FF6B35] to-[#E55A2B]',
    bgColor: 'bg-[#FFF0EB]',
    textColor: 'text-[#FF6B35]',
  },
  { 
    name: 'Aires Acondicionados', 
    icon: Zap, 
    slug: 'aires', 
    count: 32,
    color: 'from-[#0066FF] to-[#0052CC]',
    bgColor: 'bg-[#E6F0FF]',
    textColor: 'text-[#0066FF]',
  },
  { 
    name: 'Reguladores', 
    icon: Gauge, 
    slug: 'reguladores', 
    count: 28,
    color: 'from-[#10B981] to-[#059669]',
    bgColor: 'bg-[#D1FAE5]',
    textColor: 'text-[#10B981]',
  },
  { 
    name: 'Herramientas', 
    icon: Tool, 
    slug: 'herramientas', 
    count: 56,
    color: 'from-[#F59E0B] to-[#D97706]',
    bgColor: 'bg-[#FEF3C7]',
    textColor: 'text-[#F59E0B]',
  },
]

const features = [
  {
    icon: Truck,
    title: 'Envio Gratis',
    description: 'En compras mayores a $500.000',
    color: 'text-[#0066FF]',
    bgColor: 'bg-[#E6F0FF]'
  },
  {
    icon: Shield,
    title: 'Garantia Extendida',
    description: 'Hasta 5 años de proteccion',
    color: 'text-[#10B981]',
    bgColor: 'bg-[#D1FAE5]'
  },
  {
    icon: Wrench,
    title: 'Instalacion Profesional',
    description: 'Incluida con cada compra',
    color: 'text-[#FF6B35]',
    bgColor: 'bg-[#FFF0EB]'
  },
  {
    icon: Headphones,
    title: 'Soporte 24/7',
    description: 'Atencion personalizada',
    color: 'text-[#8B5CF6]',
    bgColor: 'bg-[#EDE9FE]'
  },
]

function HomePage() {
  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#0066FF] via-[#0052CC] to-[#003D99]">
          <div className="absolute inset-0 opacity-30" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }} />
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-28 pb-32 lg:pb-40">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <div className="text-center lg:text-left animate-fade-in">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur rounded-full text-white/90 text-sm font-medium mb-6">
                <span className="w-2 h-2 bg-[#10B981] rounded-full animate-pulse" />
                Envios a todo el pais
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold text-white mb-6 leading-[1.1] tracking-tight">
                Todo en{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF6B35] to-[#FFB800]">
                  Gas
                </span>{' '}
                y Climatizacion
              </h1>
              
              <p className="text-lg lg:text-xl text-white/80 mb-8 leading-relaxed max-w-xl mx-auto lg:mx-0">
                Calentadores, aires acondicionados, reguladores y herramientas de las mejores marcas con instalacion profesional incluida.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link
                  to="/productos"
                  className="group inline-flex items-center justify-center gap-2 bg-white text-[#0066FF] px-8 py-4 rounded-xl font-semibold shadow-xl shadow-black/10 hover:shadow-2xl hover:-translate-y-1 active:translate-y-0 transition-all duration-200"
                >
                  Ver Productos
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  to="/contacto"
                  className="group inline-flex items-center justify-center gap-2 bg-white/10 backdrop-blur border border-white/20 text-white px-8 py-4 rounded-xl font-semibold hover:bg-white/20 transition-all"
                >
                  <Play className="w-5 h-5" />
                  Ver video
                </Link>
              </div>

              {/* Stats */}
              <div className="mt-12 pt-8 border-t border-white/10 grid grid-cols-3 gap-4 sm:gap-8">
                {[
                  { value: '10K+', label: 'Clientes felices' },
                  { value: '500+', label: 'Productos' },
                  { value: '10', label: 'Años experiencia' },
                ].map((stat) => (
                  <div key={stat.label} className="text-center lg:text-left">
                    <p className="text-2xl lg:text-3xl font-bold text-white">{stat.value}</p>
                    <p className="text-sm text-white/60">{stat.label}</p>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="hidden lg:flex flex-col gap-3 relative animate-slide-up">
              {/* Ambient glow */}
              <div className="absolute -inset-6 bg-gradient-to-br from-[#FF6B35]/20 to-[#FFB800]/20 rounded-3xl blur-2xl pointer-events-none" />

              {/* Product showcase card */}
              <div className="relative bg-white/10 backdrop-blur-sm rounded-3xl p-5 border border-white/15">
                <p className="text-white/50 text-xs font-semibold uppercase tracking-widest mb-4">Productos destacados</p>
                <div className="space-y-3">
                  {[
                    { Icon: ThermometerSun, name: 'Calentador 13L Premium', price: '$650.000', badge: '-13%', img: 'https://placehold.co/52x52/FF6B35/white?text=13L' },
                    { Icon: Zap, name: 'Aire Inverter 12000 BTU', price: '$1.850.000', badge: '-12%', img: 'https://placehold.co/52x52/0066FF/white?text=Aire' },
                    { Icon: Gauge, name: 'Regulador Alta Presión', price: '$85.000', badge: 'Nuevo', img: 'https://placehold.co/52x52/10B981/white?text=Reg' },
                    { Icon: Tool, name: 'Kit Instalación Pro', price: '$320.000', badge: '-16%', img: 'https://placehold.co/52x52/F59E0B/white?text=Kit' },
                  ].map((item) => (
                    <div key={item.name} className="flex items-center gap-3 bg-white/5 hover:bg-white/10 transition-colors rounded-2xl p-3">
                      <img src={item.img} alt={item.name} className="w-12 h-12 rounded-xl flex-shrink-0 object-cover" />
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium text-sm truncate">{item.name}</p>
                        <p className="text-[#10B981] font-bold text-sm">{item.price}</p>
                      </div>
                      <span className="text-xs font-bold px-2 py-0.5 bg-white/10 text-orange-300 rounded-full flex-shrink-0">
                        {item.badge}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick stats row */}
              <div className="relative bg-white/10 backdrop-blur-sm rounded-2xl border border-white/15 p-4 flex justify-around text-center">
                {[
                  { value: '4.9★', label: 'Rating' },
                  { value: '48h', label: 'Entrega' },
                  { value: '5 años', label: 'Garantía' },
                  { value: '100%', label: 'Seguro' },
                ].map((stat, i, arr) => (
                  <>
                    <div key={stat.label}>
                      <p className="text-white font-bold text-lg leading-tight">{stat.value}</p>
                      <p className="text-white/50 text-xs mt-0.5">{stat.label}</p>
                    </div>
                    {i < arr.length - 1 && <div className="w-px bg-white/20" />}
                  </>
                ))}
              </div>

              {/* Floating guarantee badge */}
              <div className="absolute -top-4 -right-5 bg-white rounded-2xl p-3 shadow-2xl animate-float z-10">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 bg-gradient-to-br from-[#10B981] to-[#059669] rounded-xl flex items-center justify-center flex-shrink-0">
                    <Shield className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-bold text-[#1A1D21] text-sm leading-tight">Garantía</p>
                    <p className="text-xs text-[#6B7280]">Hasta 5 años</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Wave Divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
            <path d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z" fill="#FAFBFC"/>
          </svg>
        </div>
      </section>

      {/* Features */}
      <section className="py-8 lg:py-0 lg:-mt-14 relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-2xl lg:rounded-3xl shadow-xl shadow-black/5 p-6 lg:p-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
              {features.map((feature) => (
                <div key={feature.title} className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left">
                  <div className={`w-14 h-14 ${feature.bgColor} rounded-2xl flex items-center justify-center flex-shrink-0`}>
                    <feature.icon className={`w-7 h-7 ${feature.color}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#1A1D21] mb-0.5">{feature.title}</h3>
                    <p className="text-sm text-[#6B7280]">{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-4">
              Explora por Categoria
            </h2>
            <p className="text-[#6B7280] max-w-2xl mx-auto text-lg">
              Encuentra exactamente lo que necesitas para tu hogar o negocio
            </p>
          </div>
          
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
            {categories.map((category) => (
              <Link
                key={category.slug}
                to={`/productos?category=${category.slug}`}
                className="group relative bg-white rounded-2xl p-6 lg:p-8 border border-[#E5E7EB] hover:border-transparent hover:shadow-xl transition-all duration-300 overflow-hidden"
              >
                {/* Background gradient on hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${category.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                
                <div className="relative z-10">
                  <div className={`w-14 h-14 lg:w-16 lg:h-16 ${category.bgColor} group-hover:bg-white/20 rounded-2xl flex items-center justify-center mb-4 transition-colors`}>
                    <category.icon className={`w-7 h-7 lg:w-8 lg:h-8 ${category.textColor} group-hover:text-white transition-colors`} />
                  </div>
                  <h3 className="font-semibold text-[#1A1D21] group-hover:text-white text-lg mb-1 transition-colors">
                    {category.name}
                  </h3>
                  <p className="text-sm text-[#6B7280] group-hover:text-white/80 transition-colors">
                    {category.count} productos
                  </p>
                </div>

                {/* Arrow */}
                <div className="absolute bottom-6 right-6 w-10 h-10 bg-[#F3F4F6] group-hover:bg-white/20 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-4 group-hover:translate-x-0">
                  <ArrowRight className="w-5 h-5 text-[#1A1D21] group-hover:text-white" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-12">
            <div>
              <span className="inline-block px-3 py-1 bg-[#E6F0FF] text-[#0066FF] text-sm font-medium rounded-full mb-3">
                Lo mas vendido
              </span>
              <h2 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-2">
                Productos Destacados
              </h2>
              <p className="text-[#6B7280] text-lg">Los favoritos de nuestros clientes</p>
            </div>
            <Link
              to="/productos"
              className="group flex items-center gap-2 text-[#0066FF] font-semibold hover:gap-3 transition-all"
            >
              Ver todos
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#FF6B35] via-[#FF8F65] to-[#FFB800]">
            {/* Pattern */}
            <div className="absolute inset-0 opacity-10" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }} />
            
            <div className="relative px-8 py-12 lg:px-16 lg:py-20 text-center">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                Necesitas asesoria personalizada?
              </h2>
              <p className="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
                Nuestros expertos te ayudaran a elegir el producto perfecto para tu hogar o negocio
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/contacto"
                  className="group inline-flex items-center justify-center gap-2 bg-white text-[#FF6B35] px-8 py-4 rounded-xl font-semibold shadow-xl hover:shadow-2xl hover:-translate-y-1 active:translate-y-0 transition-all"
                >
                  Hablar con un Asesor
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <a
                  href="tel:+573001234567"
                  className="inline-flex items-center justify-center gap-2 bg-white/20 backdrop-blur text-white px-8 py-4 rounded-xl font-semibold hover:bg-white/30 transition-all"
                >
                  Llamar Ahora
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Location Map */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <span className="inline-block px-3 py-1 bg-[#D1FAE5] text-[#059669] text-sm font-medium rounded-full mb-3">
              Visitanos
            </span>
            <h2 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-4">
              Nuestra Ubicacion
            </h2>
            <p className="text-[#6B7280] max-w-2xl mx-auto text-lg">
              Encuentra nuestra tienda fisica y recibe atencion personalizada
            </p>
          </div>
          <GoogleMap />
        </div>
      </section>
    </div>
  )
}

export default HomePage
