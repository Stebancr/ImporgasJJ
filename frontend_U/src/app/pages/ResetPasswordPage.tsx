import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../../services/api'

export default function ResetPasswordPage() {
  const { uid, token } = useParams()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [complete, setComplete] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    if (password !== confirmation) { setError('Las contraseñas no coinciden.'); return }
    setBusy(true)
    try {
      await api.post('/user/password/reset/confirm', {
        uid, token, new_password: password, confirm_password: confirmation,
      })
      setComplete(true)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'El enlace no es válido o ha expirado.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="min-h-screen bg-gray-50 px-4 py-10 sm:py-16">
    <div className="mx-auto w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm sm:p-8">
      <Link to="/" className="mb-8 inline-block"><img src="/logo_imporgas.svg" alt="ImporGas JJ" className="h-14 max-w-full object-contain" /></Link>
      <h1 className="mb-3 text-2xl font-bold text-gray-900">Restablecer contraseña</h1>
      {complete ? <div role="status" className="space-y-4"><p>Contraseña actualizada correctamente.</p><Link to="/login" className="inline-block rounded-xl bg-[#001575] px-5 py-3 font-semibold text-white">Iniciar sesión</Link></div> :
        <form onSubmit={submit} className="space-y-5">
          <p className="text-sm text-gray-600">Ingresa tu nueva contraseña para continuar.</p>
          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          <label className="block text-sm font-medium text-gray-700">Nueva contraseña
            <input type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-xl border px-4 py-3" />
          </label>
          <label className="block text-sm font-medium text-gray-700">Confirmar nueva contraseña
            <input type="password" autoComplete="new-password" required minLength={8} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} className="mt-2 w-full rounded-xl border px-4 py-3" />
          </label>
          <button disabled={busy} className="w-full rounded-xl bg-[#001575] px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? 'Guardando...' : 'Guardar contraseña'}</button>
        </form>}
    </div>
  </main>
}
