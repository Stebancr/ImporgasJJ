import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Save, ArrowLeft } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export default function EditProfilePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    nombre_completo: '',
    correo: '',
    telefono: '',
    sede: '',
  })

  useEffect(() => {
    if (user?.usuario_rel) {
      setForm({
        nombre_completo: user.usuario_rel.nombre_completo || '',
        correo: user.usuario_rel.correo || '',
        telefono: user.usuario_rel.telefono || '',
        sede: user.usuario_rel.sede || '',
      })
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implementar actualización de perfil cuando esté el endpoint
    alert('Función de edición de perfil en desarrollo')
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <button
          onClick={() => navigate('/perfil')}
          className="flex items-center gap-2 text-gray-600 hover:text-[#001575] mb-6 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Volver al perfil
        </button>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3 mb-6">
            <User className="w-7 h-7 text-[#001575]" />
            Editar Información Personal
          </h1>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nombre completo
              </label>
              <input
                type="text"
                value={form.nombre_completo}
                onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#001575] focus:border-transparent"
                placeholder="Tu nombre completo"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Correo electrónico
              </label>
              <input
                type="email"
                value={form.correo}
                onChange={(e) => setForm({ ...form, correo: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#001575] focus:border-transparent"
                placeholder="tu@email.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Teléfono
              </label>
              <input
                type="tel"
                value={form.telefono}
                onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#001575] focus:border-transparent"
                placeholder="3001234567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sede
              </label>
              <input
                type="text"
                value={form.sede}
                onChange={(e) => setForm({ ...form, sede: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#001575] focus:border-transparent"
                placeholder="Sede de trabajo"
              />
            </div>

            <div className="pt-4">
              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors"
              >
                <Save className="w-5 h-5" />
                Guardar cambios
              </button>
            </div>
          </form>

          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Cambiar contraseña</h3>
            <p className="text-gray-600 text-sm mb-4">
              Para cambiar tu contraseña, contacta al administrador del sistema.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
