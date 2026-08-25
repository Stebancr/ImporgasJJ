import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Phone, Facebook, Instagram, Youtube, ExternalLink } from 'lucide-react'

// ── Intersection Observer hook for scroll animations ─────────────────────────
function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect() } }, { threshold })
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, visible }
}

// ── Values ────────────────────────────────────────────────────────────────────
const values = [
  { emoji: '✅', title: 'Responsabilidad', desc: 'Cumplimos con nuestros compromisos y respondemos por la calidad de cada servicio que prestamos.' },
  { emoji: '🏆', title: 'Excelencia', desc: 'Buscamos la perfección en cada instalación y reparación, superando las expectativas de nuestros clientes.' },
  { emoji: '💡', title: 'Innovación y Sostenibilidad', desc: 'Adoptamos tecnologías modernas y prácticas sostenibles para cuidar el medio ambiente.' },
  { emoji: '🔍', title: 'Transparencia', desc: 'Actuamos con honestidad y claridad en cada proceso, generando confianza en nuestros clientes.' },
  { emoji: '🤝', title: 'Trabajo en Equipo', desc: 'Colaboramos juntos para lograr los mejores resultados, valorando cada aporte individual.' },
  { emoji: '🫡', title: 'Respeto', desc: 'Tratamos a cada persona con dignidad y consideración, dentro y fuera de nuestra organización.' },
  { emoji: '😊', title: 'Alegría, Entusiasmo y Buen Humor', desc: 'Llevamos energía positiva a cada trabajo, creando un ambiente agradable para clientes y equipo.' },
]

// ── Animated section wrapper ──────────────────────────────────────────────────
function AnimSection({ children, className = '', delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const { ref, visible } = useInView()
  return (
    <div ref={ref} className={`transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

export default function NosotrosPage() {
  return (
    <div className="min-h-screen bg-[#FAFBFC]">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative bg-gradient-to-br from-[#001575] via-[#0022b3] to-[#001575] text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur rounded-full text-white/90 text-sm font-medium mb-6">
            <span className="w-2 h-2 bg-[#F58634] rounded-full animate-pulse" />
            Sobre nosotros
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            Conoce a{' '}
            <span className="text-[#F58634]">ImporGas JJ</span>
          </h1>
          <p className="text-xl text-white/80 max-w-2xl mx-auto">
            Más de una década llevando soluciones profesionales en equipos a gas a miles de hogares y empresas en Colombia.
          </p>
        </div>
      </section>

      {/* ── Quiénes Somos ────────────────────────────────────────────────── */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">

            <AnimSection>
              <div className="relative rounded-3xl overflow-hidden shadow-2xl">
                <img
                  src="https://imporgasjj.com/wp-content/uploads/2024/05/western-chinese-business-hong-kong-893x1024.jpg"
                  alt="Equipo ImporGas JJ S.A.S"
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#001575]/40 to-transparent" />
                <div className="absolute bottom-6 left-6 right-6">
                  <div className="bg-white/90 backdrop-blur rounded-2xl px-5 py-4 shadow-lg">
                    <p className="font-bold text-[#001575] text-lg">ImporGas JJ S.A.S</p>
                    <p className="text-gray-600 text-sm">NIT: 900739269-1</p>
                  </div>
                </div>
              </div>
            </AnimSection>

            <AnimSection delay={150}>
              <div className="space-y-6">
                <div>
                  <span className="inline-block text-[#F58634] font-semibold text-sm uppercase tracking-widest mb-2">¿Quiénes Somos?</span>
                  <h2 className="text-3xl lg:text-4xl font-bold text-[#001575] mb-4">Tu aliado de confianza en equipos a gas</h2>
                </div>
                <p className="text-gray-600 leading-relaxed">
                  ImporGas JJ S.A.S es una empresa colombiana especializada en la comercialización y servicio técnico de equipos de funcionamiento a gas. Nacimos con la misión de brindar soluciones integrales, seguras y de alta calidad a hogares y negocios en todo el territorio nacional.
                </p>
                <p className="text-gray-600 leading-relaxed">
                  Contamos con un equipo de técnicos certificados y altamente capacitados en la instalación, reparación y mantenimiento de calentadores, estufas, hornos, campanas, lavadoras, neveras y secadoras. Nuestra experiencia y compromiso con la excelencia nos han convertido en una marca de referencia en el sector.
                </p>
                <p className="text-gray-600 leading-relaxed">
                  Nos distinguimos por la seriedad, la puntualidad y el trato personalizado que ofrecemos a cada uno de nuestros clientes. Porque para nosotros, cada hogar merece lo mejor.
                </p>
                <div className="flex flex-wrap gap-4 pt-2">
                  <a href="tel:+573165266734"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-[#F58634] hover:bg-[#d4711e] text-white rounded-xl font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-[#F58634]/30 hover:-translate-y-0.5">
                    <Phone className="w-4 h-4" />
                    316 526 6734
                  </a>
                  <Link to="/contacto"
                    className="inline-flex items-center gap-2 px-6 py-3 border-2 border-[#001575] text-[#001575] rounded-xl font-semibold hover:bg-[#001575] hover:text-white transition-all duration-200">
                    Contáctanos
                  </Link>
                </div>
              </div>
            </AnimSection>
          </div>
        </div>
      </section>

      {/* ── Misión y Visión ──────────────────────────────────────────────── */}
      <section className="py-16 lg:py-20 bg-gradient-to-b from-white to-[#f0f4ff]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimSection>
            <div className="text-center mb-12">
              <h2 className="text-3xl lg:text-4xl font-bold text-[#001575]">Misión y Visión</h2>
              <p className="text-gray-500 mt-2">El propósito que nos mueve cada día</p>
            </div>
          </AnimSection>

          <div className="grid md:grid-cols-2 gap-8">
            <AnimSection delay={100}>
              <div className="bg-white rounded-3xl p-8 lg:p-10 shadow-lg border border-[#e8ecff] hover:shadow-xl hover:-translate-y-1 transition-all duration-300 h-full">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#001575] to-[#0033cc] flex items-center justify-center text-2xl mb-6 shadow-lg shadow-[#001575]/20">
                  🎯
                </div>
                <h3 className="text-2xl font-bold text-[#001575] mb-4">Nuestra Misión</h3>
                <p className="text-gray-600 leading-relaxed">
                  Brindar soluciones integrales, seguras y de alta calidad en la comercialización y servicio técnico de equipos a gas, garantizando la satisfacción total de nuestros clientes a través de un equipo humano comprometido, capacitado y orientado a la excelencia en cada servicio que prestamos.
                </p>
              </div>
            </AnimSection>

            <AnimSection delay={200}>
              <div className="bg-gradient-to-br from-[#001575] to-[#0033cc] rounded-3xl p-8 lg:p-10 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300 h-full">
                <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center text-2xl mb-6">
                  🚀
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Nuestra Visión</h3>
                <p className="text-white/85 leading-relaxed">
                  Para el año 2030, ser la empresa líder en Colombia en la comercialización y servicio técnico de equipos a gas, reconocida por nuestra innovación, calidad y compromiso con la sostenibilidad, expandiendo nuestra presencia en todas las principales ciudades del país con un equipo técnico de referencia nacional.
                </p>
              </div>
            </AnimSection>
          </div>
        </div>
      </section>

      {/* ── Valores ──────────────────────────────────────────────────────── */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AnimSection>
            <div className="text-center mb-12">
              <span className="inline-block text-[#F58634] font-semibold text-sm uppercase tracking-widest mb-2">Nuestros pilares</span>
              <h2 className="text-3xl lg:text-4xl font-bold text-[#001575]">Valores Corporativos</h2>
              <p className="text-gray-500 mt-2 max-w-xl mx-auto">Los principios que guían cada decisión y acción en ImporGas JJ S.A.S</p>
            </div>
          </AnimSection>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {values.map((v, i) => (
              <AnimSection key={v.title} delay={i * 70}>
                <div className="group bg-white rounded-2xl p-6 shadow-md border border-gray-100 hover:shadow-xl hover:-translate-y-2 hover:border-[#F58634]/30 transition-all duration-300 h-full cursor-default">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#fff3e8] to-[#ffe5cc] flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform duration-300">
                    {v.emoji}
                  </div>
                  <h4 className="font-bold text-[#001575] mb-2 group-hover:text-[#F58634] transition-colors">{v.title}</h4>
                  <p className="text-sm text-gray-500 leading-relaxed">{v.desc}</p>
                </div>
              </AnimSection>
            ))}
          </div>
        </div>
      </section>

      {/* ── Social & Contact CTA ─────────────────────────────────────────── */}
      <section className="py-16 bg-gradient-to-br from-[#001575] to-[#0033cc]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <AnimSection>
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Síguenos en redes sociales</h2>
            <p className="text-white/70 mb-10 text-lg">Mantente al día con nuestros servicios, consejos y novedades</p>

            <div className="flex flex-wrap justify-center gap-4 mb-12">
              {[
                { href: 'https://www.facebook.com/share/1HLuktBrTn/?mibextid=wwXIfr', label: 'Facebook', color: 'hover:bg-[#1877f2]' },
                { href: 'https://www.instagram.com/imporgas_jj?igsh=MWhxM2RhbzA1NXhkZQ==', label: 'Instagram', color: 'hover:bg-gradient-to-r hover:from-[#f09433] hover:to-[#bc1888]' },
                { href: 'https://www.youtube.com/channel/UCfMTkKKn_CnwKzerEIcBkcw', label: 'YouTube', color: 'hover:bg-[#ff0000]' },
                { href: 'https://www.tiktok.com/@imporgasjjsas', label: 'TikTok', color: 'hover:bg-[#010101]' },
              ].map(({ href, label, color }) => (
                <a key={label} href={href} target="_blank" rel="noopener noreferrer"
                  className={`flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur ${color} text-white rounded-xl font-medium transition-all duration-200 hover:scale-105`}>
                  <ExternalLink className="w-4 h-4" />
                  {label}
                </a>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href="tel:+573165266734"
                className="flex items-center gap-3 px-8 py-4 bg-[#F58634] hover:bg-[#d4711e] text-white rounded-xl font-bold text-lg transition-all duration-200 hover:shadow-xl hover:shadow-[#F58634]/30 hover:-translate-y-1">
                <Phone className="w-5 h-5" />
                316 526 6734
              </a>
              <Link to="/contacto"
                className="flex items-center gap-3 px-8 py-4 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold text-lg transition-all duration-200">
                Escribenos
              </Link>
            </div>
          </AnimSection>
        </div>
      </section>

    </div>
  )
}
