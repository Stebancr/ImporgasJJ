import { Link } from 'react-router-dom'
import { Phone, Mail, MapPin, ArrowRight } from 'lucide-react'

const socialLinks = [
  {
    href: 'https://www.facebook.com/share/1HLuktBrTn/?mibextid=wwXIfr',
    label: 'Facebook',
    svg: '<path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>',
  },
  {
    href: 'https://www.instagram.com/imporgas_jj?igsh=MWhxM2RhbzA1NXhkZQ==',
    label: 'Instagram',
    svg: '<path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>',
  },
  {
    href: 'https://www.youtube.com/channel/UCfMTkKKn_CnwKzerEIcBkcw',
    label: 'YouTube',
    svg: '<path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>',
  },
  {
    href: 'https://www.tiktok.com/@imporgasjjsas',
    label: 'TikTok',
    svg: '<path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/>',
  },
]

export default function Footer() {
  return (
    <footer className="bg-[#0a0e2e] text-[#9CA3AF]">
      {/* Main footer */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-8">

          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <Link to="/" className="inline-block mb-5">
              <img src="/logo_imporgas.svg" alt="ImporGas JJ S.A.S" style={{ height: '48px', width: 'auto', filter: 'brightness(0) invert(1)' }} />
            </Link>
            <p className="text-sm leading-relaxed mb-2 font-semibold text-white">ImporGas JJ S.A.S</p>
            <p className="text-xs text-gray-500 mb-1">NIT: 900739269-1</p>
            <p className="text-sm leading-relaxed mb-6">
              Comercialización y servicio técnico de equipos de funcionamiento a gas.
            </p>
            <div className="flex gap-3 flex-wrap">
              {socialLinks.map(({ href, label, svg }) => (
                <a key={label} href={href} target="_blank" rel="noopener noreferrer"
                  className="w-10 h-10 bg-white/5 hover:bg-[#F58634] rounded-lg flex items-center justify-center transition-all duration-200 hover:-translate-y-1"
                  aria-label={label}>
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24" dangerouslySetInnerHTML={{ __html: svg }} />
                </a>
              ))}
            </div>
          </div>

          {/* Products */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Productos</h3>
            <ul className="space-y-3">
              {[
                { label: 'Calentadores', href: '/productos?category=calentadores' },
                { label: 'Estufas y Hornos', href: '/productos?category=estufas' },
                { label: 'Lavadoras y Secadoras', href: '/productos?category=lavadoras' },
                { label: 'Neveras', href: '/productos?category=neveras' },
                { label: 'Ver todo', href: '/productos' },
              ].map(link => (
                <li key={link.label}>
                  <Link to={link.href} className="hover:text-[#F58634] transition-colors inline-flex items-center gap-1 group text-sm">
                    <ArrowRight className="w-3 h-3 opacity-0 -ml-4 group-hover:opacity-100 group-hover:ml-0 transition-all" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Help */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Ayuda</h3>
            <ul className="space-y-3">
              {[
                { label: 'Seguimiento de Pedidos', href: '/seguimiento' },
                { label: 'Nosotros', href: '/nosotros' },
                { label: 'Contacto', href: '/contacto' },
                { label: 'Preguntas Frecuentes', href: '#' },
                { label: 'Política de Devoluciones', href: '#' },
              ].map(link => (
                <li key={link.label}>
                  <Link to={link.href} className="hover:text-[#F58634] transition-colors inline-flex items-center gap-1 group text-sm">
                    <ArrowRight className="w-3 h-3 opacity-0 -ml-4 group-hover:opacity-100 group-hover:ml-0 transition-all" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Contacto</h3>
            <ul className="space-y-4">
              <li>
                <a href="tel:+573165266734" className="flex items-center gap-3 group">
                  <div className="w-10 h-10 bg-white/5 group-hover:bg-[#F58634] rounded-lg flex items-center justify-center transition-colors flex-shrink-0">
                    <Phone className="w-5 h-5 text-[#F58634] group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <p className="text-white font-medium">316 526 6734</p>
                    <p className="text-xs">Lun - Sab: 8am - 6pm</p>
                  </div>
                </a>
              </li>
              <li>
                <a href="mailto:info@imporgasjj.com" className="flex items-center gap-3 group">
                  <div className="w-10 h-10 bg-white/5 group-hover:bg-[#F58634] rounded-lg flex items-center justify-center transition-colors flex-shrink-0">
                    <Mail className="w-5 h-5 text-[#F58634] group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <p className="text-white font-medium">gerenciaimporgasjj213@gmail.com</p>
                    <p className="text-xs">Respuesta en 24h</p>
                  </div>
                </a>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <MapPin className="w-5 h-5 text-[#F58634]" />
                </div>
                <div>
                  <p className="text-white font-medium">Colombia</p>
                  <p className="text-xs leading-relaxed">Servicio a nivel nacional</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-500">
            <p>© {new Date().getFullYear()} ImporGas JJ S.A.S — NIT 900739269-1. Todos los derechos reservados.</p>
            <div className="flex gap-4">
              <a href="#" className="hover:text-[#F58634] transition-colors">Términos y Condiciones</a>
              <Link to="/politica-tratamiento-datos" className="hover:text-[#F58634] transition-colors">Política de Tratamiento de Datos</Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
