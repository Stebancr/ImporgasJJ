import { CategoryIcon } from '../../components/CategoryIcon'
import api from '../../services/api'
import './styles/HomePage.css'
import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { ArrowRight, Truck, Shield, Headphones, Wrench, Zap, ThermometerSun, Gauge, PenToolIcon as Tool, Flame, Utensils } from 'lucide-react'
import ProductCard from '../../components/ProductCard'
import GoogleMap from '../../components/GoogleMap'
import {useShippingConfig} from '../../hooks/useShippingConfig'
import { Product } from '../../types'
import { productsService } from '../../services/products'
import { locationsService, ApiLocation } from '../../services/locations'



const categories = [
  {
    name: 'Calentadores',
    icon: ThermometerSun,
    slug: 'calentadores',
    color: 'from-[#F58634] to-[#d4711e]',
    bgColor: 'bg-[#fff3e8]',
    textColor: 'text-[#F58634]',
  },
  {
    name: 'Reguladores',
    icon: Gauge,
    slug: 'reguladores',
    color: 'from-[#10B981] to-[#059669]',
    bgColor: 'bg-[#D1FAE5]',
    textColor: 'text-[#10B981]',
  },
  {
    name: 'Herramientas',
    icon: Tool,
    slug: 'herramientas',
    color: 'from-[#F59E0B] to-[#D97706]',
    bgColor: 'bg-[#FEF3C7]',
    textColor: 'text-[#F59E0B]',
  },
]

const features = [
  {
    icon: Truck,
    title: 'Envíos',
    description: 'Consulta el costo de entrega al comprar',
    color: 'text-[#001575]',
    bgColor: 'bg-[#e8ecff]'
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
    color: 'text-[#F58634]',
    bgColor: 'bg-[#fff3e8]'
  },
  {
    icon: Headphones,
    title: 'Soporte 24/7',
    description: 'Atencion personalizada',
    color: 'text-[#8B5CF6]',
    bgColor: 'bg-[#EDE9FE]'
  },
]

// ── Services data ────────────────────────────────────────────────────────────
const services = [
  {
    icon: Flame,
    title: 'Calentadores',
    image: '/calentadores.jpg',
    items: [
      'Instalación de calentadores de agua a gas',
      'Instalación de calentadores eléctricos',
      'Reparación de calentadores',
      'Venta e instalación para piscinas y jacuzzis',
    ],
  },
  {
    icon: Utensils,
    title: 'Estufas, Hornos y Campanas',
    image: '/estufa-horno.jpg',
    items: [
      'Instalación de estufas empotrables',
      'Instalación de hornos',
      'Reparación de estufas',
      'Reparación de hornos',
    ],
  },
]

function HomePage() {
  const shippingConfig=useShippingConfig()
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([])
  const [productsError, setProductsError] = useState(false)
  const [reloadProducts, setReloadProducts] = useState(0)
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [extraCategories, setExtraCategories] = useState<{ id: number; name: string; slug: string; icon: string }[]>([])
  useEffect(() => {
    let active = true
    api.get<{ categories: { id: number; name: string; slug: string; icon: string }[] }>('/products?per_page=1')
      .then(result => {
        if (active) setExtraCategories((result.categories ?? []).filter(item => !categories.some(featured => featured.slug === item.slug)))
      })
      .catch(() => {})
    return () => { active = false }
  }, [])
  const [storeLocations, setStoreLocations] = useState<ApiLocation[]>([])
  useEffect(() => {
    setIsLoadingProducts(true)
    setProductsError(false)
    productsService.getHomeProducts()
      .then(products => setFeaturedProducts(products))
      .catch(() => setProductsError(true))
      .finally(() => setIsLoadingProducts(false))
  }, [reloadProducts])

  useEffect(() => {
    locationsService.getActive()
      .then(locs => setStoreLocations(locs))
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-[#FAFBFC]">
      {shippingConfig.enabled&&shippingConfig.freeShippingThreshold&&<aside className="flex items-center justify-center gap-2 bg-[#001575] px-4 py-3 text-center text-sm font-semibold text-white"><Truck aria-hidden="true" className="h-4 w-4"/>Envío gratis en compras desde {Number(shippingConfig.freeShippingThreshold).toLocaleString('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0})}<span className="sr-only">Sujeto a cobertura y cotización de entrega.</span></aside>}
      <section className="bg-[#001575] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <h1 className="text-3xl lg:text-5xl font-bold leading-tight">Equipos y accesorios para gas</h1>
          <p className="mt-3 max-w-xl text-white/90">Calentadores, reguladores, medidores y repuestos para el hogar y el negocio.</p>
          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
            <Link to="/productos" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#F58634] px-5 text-[#00104f] font-semibold hover:bg-[#ffa868] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">
              Ver catálogo <ArrowRight aria-hidden="true" className="h-5 w-5" />
            </Link>
            <a href="#servicios" className="inline-flex min-h-11 items-center underline underline-offset-4 focus-visible:outline focus-visible:outline-2">Servicio técnico</a>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-8 lg:py-10 bg-[#FAFBFC]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-6">
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-2">
                Productos disponibles
              </h2>

            </div>
            <Link
              to="/productos"
              className="group flex items-center gap-2 text-[#001575] font-semibold hover:gap-3 transition-all"
            >
              Ver todos
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {productsError && <div role="alert" className="col-span-full p-4 rounded-xl bg-red-50 text-red-800">No pudimos cargar los productos. <button className="underline min-h-11" onClick={() => setReloadProducts(value => value + 1)}>Reintentar</button></div>}
            {isLoadingProducts
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} aria-hidden="true" className="rounded-xl bg-gray-100 motion-safe:animate-pulse h-72" />
                ))
              : productsError ? null : featuredProducts.length > 0
                ? featuredProducts.map((product) => (
                    <ProductCard key={product.id} product={product} />
                  ))
                : (
                  <p className="col-span-full text-center text-gray-500 py-12">
                    No hay productos disponibles en este momento.
                  </p>
                )
            }
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-8 lg:py-6 relative z-20">
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
              Explora por categoría
            </h2>
            <p className="text-[#6B7280] max-w-2xl mx-auto text-lg">
              Encuentra exactamente lo que necesitas para tu hogar o negocio
            </p>
          </div>
          
          <div className="home-categories__grid">
              {[...categories, ...extraCategories.map(({ id, name, slug, icon }) => ({
              id, name, slug,
              icon: ({ className }: { className?: string }) => <CategoryIcon name={icon} className={className} />,
              color: 'from-[#001575] to-[#00104f]',
              bgColor: 'bg-[#e8ecff]',
              textColor: 'text-[#001575]',
            }))].map((category) => (
              <Link
                key={category.slug}
                to={'id' in category ? '/productos?category_id=' + category.id : '/productos?category=' + category.slug}
                className="home-category-card group relative bg-white rounded-2xl p-6 lg:p-8 border border-[#E5E7EB] hover:border-transparent hover:shadow-xl transition-all duration-300 overflow-hidden"
              >
                {/* Background gradient on hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${category.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                
                <div className="relative z-10 flex flex-col items-center text-center">
                  <div className={`w-14 h-14 lg:w-16 lg:h-16 ${category.bgColor} group-hover:bg-white/20 rounded-2xl flex items-center justify-center mb-4 transition-colors`}>
                    <category.icon className={`w-7 h-7 lg:w-8 lg:h-8 ${category.textColor} group-hover:text-white transition-colors`} />
                  </div>
                  <h3 className="font-semibold text-[#1A1D21] group-hover:text-white text-lg transition-colors">
                    {category.name}
                  </h3>
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

      {/* ── Nuestros Servicios ────────────────────────────────────────── */}
      <section id="servicios" className="py-12 lg:py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <span className="inline-block px-4 py-1.5 bg-[#fff3e8] text-[#F58634] text-sm font-semibold rounded-full mb-3">
              Lo que hacemos
            </span>
            <h2 className="text-3xl lg:text-4xl font-bold text-[#001575] mb-4">Nuestros Servicios</h2>
            <p className="text-gray-500 max-w-2xl mx-auto text-lg">
              Soluciones integrales para el hogar y la empresa con técnicos certificados y garantía en cada trabajo
            </p>
          </div>

          <div className="home-services__grid">
            {services.map((service) => (
              <div
                key={service.title}
                className="home-service-card group bg-white rounded-3xl overflow-hidden shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-2 transition-all duration-300"
              >
                {/* Image */}
                <div className="relative overflow-hidden h-82">
                  <img
                    src={service.image}
                    alt={service.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#001575]/70 to-transparent" />
                  <div className="absolute bottom-4 left-4">
                    <div className="w-12 h-12 rounded-2xl bg-[#F58634] flex items-center justify-center shadow-lg">
                      <service.icon className="w-6 h-6 text-white" />
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <h3 className="text-xl font-bold text-[#001575] mb-4 group-hover:text-[#F58634] transition-colors">{service.title}</h3>
                  <ul className="space-y-2 mb-6">
                    {service.items.map(item => (
                      <li key={item} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#F58634] flex-shrink-0 mt-1.5" />
                        {item}
                      </li>
                    ))}
                  </ul>
                  <Link to="/contacto"
                    className="inline-flex items-center gap-2 text-[#001575] font-semibold hover:text-[#F58634] transition-colors text-sm group/btn">
                    Solicitar servicio
                    <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#001575] via-[#0033cc] to-[#001575]">
            <div className="absolute inset-0 opacity-10" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }} />
            
            <div className="relative px-8 py-12 lg:px-16 lg:py-20 text-center">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                ¿Necesitas asesoría personalizada?
              </h2>
              <p className="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
                Nuestros técnicos certificados te ayudarán con instalación, reparación y mantenimiento
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/contacto"
                  className="group inline-flex items-center justify-center gap-2 bg-[#F58634] hover:bg-[#d4711e] text-[#00104f] px-8 py-4 rounded-xl font-semibold shadow-xl shadow-[#F58634]/30 hover:-translate-y-1 active:translate-y-0 transition-all"
                >
                  Hablar con un Asesor
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <a
                  href="tel:+573165266734"
                  className="inline-flex items-center justify-center gap-2 bg-white/20 backdrop-blur text-white px-8 py-4 rounded-xl font-semibold hover:bg-white/30 transition-all"
                >
                  316 526 6734
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Location Map */}
      <section className="py-12 lg:py-16 bg-white">
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
          <GoogleMap locations={storeLocations} />
        </div>
      </section>
    </div>
  )
}

export default HomePage
