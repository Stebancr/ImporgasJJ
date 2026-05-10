import { MapPin, Clock, Phone, Navigation, Calendar } from 'lucide-react'

function GoogleMap() {
  return (
    <div className="grid lg:grid-cols-3 gap-6 lg:gap-8">
      {/* Map */}
      <div className="lg:col-span-2">
        <div className="bg-white rounded-2xl border border-[#E5E7EB] overflow-hidden shadow-sm">
          <iframe
            src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3976.8877567785387!2d-74.07283482426025!3d4.6097100428613025!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8e3f99a7d4a3b9d7%3A0x5f5f5f5f5f5f5f5f!2sBogot%C3%A1%2C%20Colombia!5e0!3m2!1ses!2sco!4v1699999999999!5m2!1ses!2sco"
            width="100%"
            height="400"
            style={{ border: 0 }}
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title="Ubicacion GasStore"
            className="w-full"
          />
          <div className="p-4 flex items-center justify-between bg-[#F9FAFB]">
            <div className="flex items-center gap-2 text-sm text-[#6B7280]">
              <MapPin className="w-4 h-4 text-[#0066FF]" />
              Bogota, Colombia
            </div>
            <a 
              href="https://maps.google.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm font-medium text-[#0066FF] hover:text-[#0052CC] transition-colors"
            >
              <Navigation className="w-4 h-4" />
              Abrir en Google Maps
            </a>
          </div>
        </div>
      </div>

      {/* Store Info */}
      <div className="space-y-4 lg:space-y-6">
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-12 h-12 bg-gradient-to-br from-[#0066FF] to-[#0052CC] rounded-xl flex items-center justify-center">
              <MapPin className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-[#1A1D21] text-lg">Tienda Principal</h3>
              <p className="text-sm text-[#6B7280]">Sede Bogota</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
              <div className="w-10 h-10 bg-[#E6F0FF] rounded-lg flex items-center justify-center flex-shrink-0">
                <MapPin className="w-5 h-5 text-[#0066FF]" />
              </div>
              <div>
                <p className="font-medium text-[#1A1D21] text-sm">Direccion</p>
                <p className="text-sm text-[#6B7280]">Calle 123 #45-67, Bogota</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
              <div className="w-10 h-10 bg-[#D1FAE5] rounded-lg flex items-center justify-center flex-shrink-0">
                <Clock className="w-5 h-5 text-[#059669]" />
              </div>
              <div>
                <p className="font-medium text-[#1A1D21] text-sm">Horario</p>
                <p className="text-sm text-[#6B7280]">Lun - Vie: 8AM - 6PM</p>
                <p className="text-sm text-[#6B7280]">Sab: 9AM - 2PM</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
              <div className="w-10 h-10 bg-[#FFF0EB] rounded-lg flex items-center justify-center flex-shrink-0">
                <Phone className="w-5 h-5 text-[#FF6B35]" />
              </div>
              <div>
                <p className="font-medium text-[#1A1D21] text-sm">Telefonos</p>
                <p className="text-sm text-[#6B7280]">+57 300 123 4567</p>
                <p className="text-sm text-[#6B7280]">+57 1 234 5678</p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden bg-gradient-to-br from-[#0066FF] to-[#0052CC] rounded-2xl p-6 text-white">
          {/* Pattern */}
          <div className="absolute inset-0 opacity-10" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='1' fill-rule='evenodd'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E")`,
          }} />
          
          <div className="relative">
            <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center mb-4">
              <Calendar className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-xl mb-2">Necesitas Ayuda?</h3>
            <p className="text-white/80 text-sm mb-5 leading-relaxed">
              Agenda una cita con nuestros asesores para una atencion personalizada.
            </p>
            <button className="w-full bg-white text-[#0066FF] py-3 rounded-xl font-semibold hover:bg-white/90 hover:shadow-lg transition-all">
              Agendar Cita
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GoogleMap
