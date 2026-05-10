import { Link } from 'react-router-dom'
import { Flame, Phone, Mail, MapPin, Facebook, Instagram, Twitter, Youtube, ArrowRight } from 'lucide-react'

function Footer() {
  return (
    <footer className="bg-[#1A1D21] text-[#9CA3AF]">
      {/* Main Footer */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 lg:gap-8">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <Link to="/" className="flex items-center gap-2.5 mb-5">
              <div className="w-10 h-10 bg-gradient-to-br from-[#FF6B35] to-[#E55A2B] rounded-xl flex items-center justify-center">
                <Flame className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">GasStore</span>
            </Link>
            <p className="text-sm leading-relaxed mb-6">
              Tu tienda de confianza para calentadores, herramientas, reguladores de gas y aires acondicionados. Mas de 10 años de experiencia.
            </p>
            <div className="flex gap-3">
              {[
                { icon: Facebook, href: '#' },
                { icon: Instagram, href: '#' },
                { icon: Twitter, href: '#' },
                { icon: Youtube, href: '#' },
              ].map((social, idx) => (
                <a
                  key={idx}
                  href={social.href}
                  className="w-10 h-10 bg-white/5 hover:bg-[#0066FF] rounded-lg flex items-center justify-center transition-all duration-200 hover:-translate-y-1"
                >
                  <social.icon className="w-5 h-5" />
                </a>
              ))}
            </div>
          </div>

          {/* Links */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Productos</h3>
            <ul className="space-y-3">
              {[
                { label: 'Calentadores', href: '/productos?category=calentadores' },
                { label: 'Aires Acondicionados', href: '/productos?category=aires' },
                { label: 'Reguladores', href: '/productos?category=reguladores' },
                { label: 'Herramientas', href: '/productos?category=herramientas' },
                { label: 'Ver Todo', href: '/productos' },
              ].map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.href}
                    className="hover:text-[#FF6B35] transition-colors inline-flex items-center gap-1 group"
                  >
                    <ArrowRight className="w-3 h-3 opacity-0 -ml-4 group-hover:opacity-100 group-hover:ml-0 transition-all" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Customer Service */}
          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">Ayuda</h3>
            <ul className="space-y-3">
              {[
                { label: 'Seguimiento de Pedidos', href: '/seguimiento' },
                { label: 'Contacto', href: '/contacto' },
                { label: 'Preguntas Frecuentes', href: '#' },
                { label: 'Politica de Devoluciones', href: '#' },
                { label: 'Terminos y Condiciones', href: '#' },
              ].map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.href}
                    className="hover:text-[#FF6B35] transition-colors inline-flex items-center gap-1 group"
                  >
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
                <a href="tel:+573001234567" className="flex items-center gap-3 group">
                  <div className="w-10 h-10 bg-white/5 group-hover:bg-[#0066FF] rounded-lg flex items-center justify-center transition-colors">
                    <Phone className="w-5 h-5 text-[#FF6B35] group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <p className="text-white font-medium">+57 300 123 4567</p>
                    <p className="text-xs">Lun - Sab: 8am - 6pm</p>
                  </div>
                </a>
              </li>
              <li>
                <a href="mailto:info@gasstore.com" className="flex items-center gap-3 group">
                  <div className="w-10 h-10 bg-white/5 group-hover:bg-[#0066FF] rounded-lg flex items-center justify-center transition-colors">
                    <Mail className="w-5 h-5 text-[#FF6B35] group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <p className="text-white font-medium">info@gasstore.com</p>
                    <p className="text-xs">Respuesta en 24h</p>
                  </div>
                </a>
              </li>
              <li>
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-5 h-5 text-[#FF6B35]" />
                  </div>
                  <div>
                    <p className="text-white font-medium">Calle 123 #45-67</p>
                    <p className="text-xs">Bogota, Colombia</p>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-center md:text-left">
              &copy; {new Date().getFullYear()} GasStore. Todos los derechos reservados.
            </p>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3 px-4 py-2 bg-white/5 rounded-lg">
                <span className="text-xs text-[#6B7280]">Pagos seguros con</span>
                <div className="flex items-center gap-2">
                  <div className="w-10 h-6 bg-white/10 rounded flex items-center justify-center text-[10px] font-bold text-white">VISA</div>
                  <div className="w-10 h-6 bg-white/10 rounded flex items-center justify-center text-[10px] font-bold text-white">MC</div>
                  <div className="w-10 h-6 bg-white/10 rounded flex items-center justify-center text-[10px] font-bold text-[#FF6B35]">PSE</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
