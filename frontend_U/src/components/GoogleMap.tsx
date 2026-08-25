import { useState } from 'react'
import { MapPin, Clock, Phone, Navigation, Calendar } from 'lucide-react'
import { ApiLocation } from '../services/locations'

interface GoogleMapProps {
  locations?: ApiLocation[]
}

const buildMapSrc = (loc: ApiLocation) =>
  `https://www.google.com/maps?q=${encodeURIComponent(`${loc.address}, ${loc.city}, Colombia`)}&output=embed`

const buildMapsLink = (loc: ApiLocation) =>
  `https://maps.google.com?q=${encodeURIComponent(`${loc.address}, ${loc.city}, Colombia`)}`

const FALLBACK_SRC = `https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3976.8877567785387!2d-74.07283482426025!3d4.6097100428613025!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8e3f99a7d4a3b9d7%3A0x5f5f5f5f5f5f5f5f!2sBogot%C3%A1%2C%20Colombia!5e0!3m2!1ses!2sco!4v1699999999999!5m2!1ses!2sco`

function GoogleMap({ locations = [] }: GoogleMapProps) {
  const [selected, setSelected] = useState<ApiLocation | null>(null)

  const active = selected ?? locations[0] ?? null

  const mapSrc = active ? buildMapSrc(active) : FALLBACK_SRC
  const mapsLink = active ? buildMapsLink(active) : 'https://maps.google.com'

  return (
    <div className="grid lg:grid-cols-3 gap-6 lg:gap-8">
      {/* Map */}
      <div className="lg:col-span-2">
        <div className="bg-white rounded-2xl border border-[#E5E7EB] overflow-hidden shadow-sm">
          <iframe
            key={mapSrc}
            src={mapSrc}
            width="100%"
            height="400"
            style={{ border: 0 }}
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title="Ubicacion ImporGas JJ"
            className="w-full"
          />
          <div className="p-4 flex items-center justify-between bg-[#F9FAFB]">
            <div className="flex items-center gap-2 text-sm text-[#6B7280]">
              <MapPin className="w-4 h-4 text-[#001575]" />
              {active ? `${active.name} - ${active.city}, Colombia` : 'Colombia'}
            </div>
            <a
              href={mapsLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm font-medium text-[#001575] hover:text-[#00104f] transition-colors"
            >
              <Navigation className="w-4 h-4" />
              Abrir en Google Maps
            </a>
          </div>
        </div>

        {locations.length > 1 && (
          <div className="mt-4 grid sm:grid-cols-2 gap-3">
            {locations.map((loc) => (
              <button
                key={loc.id}
                type="button"
                onClick={() => setSelected(loc)}
                className={`flex items-start gap-3 p-3 rounded-xl border transition-all text-left w-full ${
                  active?.id === loc.id
                    ? 'bg-[#e8ecff] border-[#001575] shadow-sm'
                    : 'bg-white border-[#E5E7EB] hover:border-[#001575]/40 hover:shadow-sm'
                }`}
              >
                <div className="w-8 h-8 bg-[#e8ecff] rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <MapPin className="w-4 h-4 text-[#001575]" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-[#1A1D21] text-sm truncate">{loc.name}</p>
                  <p className="text-xs text-[#6B7280] truncate">{loc.address}</p>
                  <p className="text-xs text-[#6B7280]">{loc.city}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Store Info */}
      <div className="space-y-4 lg:space-y-6">
        {locations.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm text-center text-[#6B7280] text-sm">
            No hay sedes registradas
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 bg-gradient-to-br from-[#001575] to-[#00104f] rounded-xl flex items-center justify-center">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-[#1A1D21] text-lg">{active?.name}</h3>
                <p className="text-sm text-[#6B7280]">{active?.city}, Colombia</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
                <div className="w-10 h-10 bg-[#e8ecff] rounded-lg flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-[#001575]" />
                </div>
                <div>
                  <p className="font-medium text-[#1A1D21] text-sm">Direccion</p>
                  <p className="text-sm text-[#6B7280]">{active?.address}</p>
                  <p className="text-sm text-[#6B7280]">{active?.city}, Colombia</p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
                <div className="w-10 h-10 bg-[#D1FAE5] rounded-lg flex items-center justify-center flex-shrink-0">
                  <Clock className="w-5 h-5 text-[#059669]" />
                </div>
                <div>
                  <p className="font-medium text-[#1A1D21] text-sm">Horario</p>
                  {active?.hours_weekday && (
                    <p className="text-sm text-[#6B7280]">Lun - Vie: {active.hours_weekday}</p>
                  )}
                  {active?.hours_saturday && (
                    <p className="text-sm text-[#6B7280]">Sab: {active.hours_saturday}</p>
                  )}
                  {active?.hours_sunday && (
                    <p className="text-sm text-[#6B7280]">Dom: {active.hours_sunday}</p>
                  )}
                  {!active?.hours_weekday && !active?.hours_saturday && !active?.hours_sunday && (
                    <p className="text-sm text-[#6B7280]">Sin horario registrado</p>
                  )}
                </div>
              </div>

              {active?.phone && (
                <div className="flex items-start gap-4 p-3 bg-[#F9FAFB] rounded-xl">
                  <div className="w-10 h-10 bg-[#fff3e8] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Phone className="w-5 h-5 text-[#F58634]" />
                  </div>
                  <div>
                    <p className="font-medium text-[#1A1D21] text-sm">Telefono</p>
                    <p className="text-sm text-[#6B7280]">{active.phone}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="relative overflow-hidden bg-gradient-to-br from-[#001575] to-[#00104f] rounded-2xl p-6 text-white">
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
            <a href="/contacto" className="block w-full bg-white text-[#001575] py-3 rounded-xl font-semibold hover:bg-white/90 hover:shadow-lg transition-all text-center">
              Contactar
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GoogleMap