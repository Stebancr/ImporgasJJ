import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Save, ArrowLeft } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'

export default function EditProfilePage() {
  const { user, logout, updateUser } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    nombre_completo: '',
    correo: '',
    telefono: '',
  })
  const [password, setPassword] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (user?.usuario_rel) {
      setForm({
        nombre_completo: user.usuario_rel.nombre_completo || '',
        correo: user.usuario_rel.correo || '',
        telefono: user.usuario_rel.telefono || '',
      })
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await api.put('/user/perfil', form)
      if (user) updateUser({ ...user, name: form.nombre_completo, email: form.correo, phone: form.telefono,
        usuario_rel: { nombre_completo: form.nombre_completo, correo: form.correo, telefono: form.telefono } })
      setMessage('Perfil actualizado correctamente.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No fue posible actualizar el perfil.')
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (password.new_password !== password.confirm_password) {
      setError('Las contraseñas nuevas no coinciden.')
      return
    }
    setSaving(true)
    try {
      await api.post('/user/password/change', password)
      logout()
      navigate('/login', { replace: true, state: { message: 'Contraseña actualizada. Inicia sesión de nuevo.' } })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No fue posible cambiar la contraseña.')
    } finally {
      setSaving(false)
    }
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
          {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {message && <p role="status" className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
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
               aria-label="Tu nombre completo" />
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
               aria-label="tu@email.com" />
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
               aria-label="3001234567" />
            </div>


            <div className="pt-4">
              <button
                type="submit"
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#001575] text-white rounded-xl font-semibold hover:bg-[#00104f] transition-colors disabled:opacity-50"
              >
                <Save className="w-5 h-5" />
                Guardar cambios
              </button>
            </div>
          </form>

          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Cambiar contraseña</h3>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              {([
                ['current_password', 'Contraseña actual'],
                ['new_password', 'Nueva contraseña'],
                ['confirm_password', 'Confirmar nueva contraseña'],
              ] as const).map(([key, label]) => (
                <label key={key} className="block text-sm font-medium text-gray-700">{label}
                  <input type="password" required autoComplete={key === 'current_password' ? 'current-password' : 'new-password'}
                    value={password[key]} onChange={(e) => setPassword((previous) => ({ ...previous, [key]: e.target.value }))}
                    className="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3 focus:border-[#001575] focus:outline-none focus:ring-2 focus:ring-[#001575]" />
                </label>
              ))}
              <button type="submit" disabled={saving} className="w-full rounded-xl bg-[#001575] px-6 py-3 font-semibold text-white disabled:opacity-50">Cambiar contraseña</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
