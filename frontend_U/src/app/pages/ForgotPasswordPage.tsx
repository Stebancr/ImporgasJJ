import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../services/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const locked = useRef(false)
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (locked.current) return
    locked.current = true; setBusy(true); setError('')
    try {
      await api.post('/user/password/reset/request', { email: email.trim() })
      setSent(true)
    } catch (cause) {
      const status = (cause as { status?: number }).status
      setError(status === 429 ? 'Espera unos minutos antes de volver a intentarlo.' :
        status === 400 ? 'Ingresa un correo válido.' : 'No fue posible enviar la solicitud. Inténtalo nuevamente.')
    } finally { locked.current = false; setBusy(false) }
  }
  return <main className="min-h-screen bg-gray-50 px-4 py-12"><section className="mx-auto max-w-md space-y-5 rounded-2xl border bg-white p-6 shadow-sm sm:p-8">
    <Link to="/"><img src="/logo_imporgas.png" alt="ImporGas JJ" className="mb-6 h-14 max-w-full object-contain" /></Link>
    <h1 className="text-2xl font-bold text-gray-900">Recuperar contraseña</h1>
    <p className="text-sm text-gray-600">Ingresa el correo asociado con tu cuenta. Si encontramos una cuenta válida, te enviaremos un enlace para crear una nueva contraseña.</p>
    {sent ? <p role="status" className="rounded-lg bg-green-50 p-4 text-green-800">Si existe una cuenta asociada a este correo, recibirás un enlace para restablecer tu contraseña.</p> :
      <form onSubmit={submit} className="space-y-5">
        <label className="block font-medium">Correo electrónico<input name="email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} className="mt-2 w-full rounded-xl border px-4 py-3 focus-visible:outline-[#001575]" /></label>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-xl bg-[#001575] px-4 py-3 font-semibold text-white hover:bg-[#00104f] focus-visible:outline-offset-4 disabled:opacity-50">{busy ? 'Enviando solicitud…' : 'Enviar enlace de recuperación'}</button>
      </form>}
    <Link to="/login" className="inline-block text-sm font-semibold text-[#001575] underline">Regresar al inicio de sesión</Link>
  </section></main>
}
