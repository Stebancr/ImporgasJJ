import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import api from '../../services/api'

export default function ResetPasswordPage() {
  const params = useParams()
  const location = useLocation()
  const secret = new URLSearchParams(location.hash.slice(1))
  const uid = params.uid || secret.get('uid') || ''
  const token = params.token || secret.get('token') || ''
  const [status, setStatus] = useState<'loading' | 'valid' | 'invalid' | 'error'>('loading')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [complete, setComplete] = useState(false)
  const [retry, setRetry] = useState(0)
  const locked = useRef(false)
  useEffect(() => {
    const abort = new AbortController()
    setStatus('loading')
    setComplete(false); setPassword(''); setConfirmation(''); setError('')
    if (!uid || !token) { setStatus('invalid'); return }
    api.post('/user/password/reset/validate', { uid, token }, abort.signal)
      .then(() => { if (!abort.signal.aborted) setStatus('valid') })
      .catch(cause => { if (!abort.signal.aborted) setStatus(cause.status === 400 ? 'invalid' : 'error') })
    return () => abort.abort()
  }, [uid, token, retry])
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (locked.current) return
    setError('')
    if (password !== confirmation) { setError('Las contraseñas no coinciden.'); return }
    locked.current = true; setBusy(true)
    try {
      await api.post('/user/password/reset/confirm', { uid, token, new_password: password, confirm_password: confirmation })
      setPassword(''); setConfirmation(''); setComplete(true)
    } catch (cause) {
      const problem = cause as { status?: number; fields?: Record<string, unknown> }
      const validation = problem.fields?.new_password || problem.fields?.confirm_password || problem.fields?.error
      const detail = Array.isArray(validation) ? validation.filter(value => typeof value === 'string').join(' ') :
        typeof validation === 'string' ? validation : ''
      setError(problem.status === 429 ? 'Espera unos minutos antes de volver a intentarlo.' :
        problem.status === 400 ? detail || 'Verifica los datos o solicita un nuevo enlace.' :
          'No fue posible guardar la contraseña. Inténtalo nuevamente.')
    } finally { locked.current = false; setBusy(false) }
  }
  return <main className="min-h-screen bg-gray-50 px-4 py-12"><section className="mx-auto max-w-md space-y-5 rounded-2xl border bg-white p-6 shadow-sm sm:p-8">
    <Link to="/"><img src="/logo_imporgas.png" alt="ImporGas JJ" className="mb-6 h-14 max-w-full object-contain" /></Link>
    <h1 className="text-2xl font-bold">Restablecer contraseña</h1>
    {complete ? <div role="status" className="space-y-4"><p>Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.</p><Link to="/login" className="inline-block rounded-xl bg-[#001575] px-5 py-3 font-semibold text-white">Ir a iniciar sesión</Link></div> :
      status === 'loading' ? <p role="status">Validando enlace…</p> : status === 'invalid' ? <div role="alert"><p>Enlace inválido o vencido.</p><Link to="/recuperar-contrasena" className="text-[#001575] underline">Solicitar otro enlace</Link></div> :
      status === 'error' ? <div role="alert"><p>No fue posible validar el enlace.</p><button onClick={() => setRetry(x => x + 1)} className="text-[#001575] underline">Reintentar</button></div> :
      <form onSubmit={submit} className="space-y-5">
        <p id="password-rules" className="text-sm text-gray-600">Usa al menos 8 caracteres. Evita contraseñas comunes, solo numéricas o similares a tu nombre o correo.</p>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
        <label className="block font-medium">Nueva contraseña<input type={visible ? 'text' : 'password'} autoComplete="new-password" aria-describedby="password-rules" required minLength={8} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} className="mt-2 w-full rounded-xl border px-4 py-3" /></label>
        <label className="block font-medium">Confirmar nueva contraseña<input type={visible ? 'text' : 'password'} autoComplete="new-password" required minLength={8} maxLength={128} value={confirmation} onChange={e => setConfirmation(e.target.value)} className="mt-2 w-full rounded-xl border px-4 py-3" /></label>
        <button type="button" aria-pressed={visible} onClick={() => setVisible(x => !x)} className="text-sm text-[#001575] underline">{visible ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}</button>
        <button disabled={busy} className="w-full rounded-xl bg-[#001575] px-5 py-3 font-semibold text-white hover:bg-[#00104f] disabled:opacity-50">{busy ? 'Guardando…' : 'Guardar contraseña'}</button>
      </form>}
  </section></main>
}
