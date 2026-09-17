import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'

const sections = [
  ['Tratamiento de datos personales', 'Los datos facilitados al crear la cuenta y realizar compras se utilizan para gestionar la relación con el cliente. Consulta la política de tratamiento de datos para conocer el detalle.'],
  ['Uso de la plataforma', 'El sitio permite consultar productos y, con una cuenta activa, preparar pedidos y realizar compras según las opciones disponibles.'],
  ['Creación de cuenta', 'El usuario debe suministrar información correcta y mantener sus credenciales bajo su control.'],
  ['Responsabilidades del usuario', 'Antes de confirmar una compra, revisa los productos, cantidades, datos de contacto y dirección de entrega.'],
  ['Productos y servicios', 'La información de productos, disponibilidad y servicios se presenta en las páginas correspondientes y puede actualizarse.'],
  ['Proceso de compra', 'El resumen del checkout muestra los productos, el envío y el total antes de confirmar. El pedido se registra según el método de pago seleccionado.'],
  ['Pagos', 'Cuando se selecciona Wompi, el pago se procesa en su flujo seguro. El estado del pedido se confirma mediante la respuesta verificada del proveedor.'],
  ['Protección y uso de la información', 'La información de la cuenta y los pedidos se usa para prestar el servicio solicitado. Consulta la política de datos para conocer los canales de atención.'],
  ['Comunicaciones', 'Los datos de contacto se utilizan para responder consultas y gestionar solicitudes relacionadas con la cuenta, pedidos o servicios.'],
  ['Modificaciones', 'Si se publica una nueva versión de estos términos, se solicitará una nueva aceptación antes de realizar otra compra.'],
  ['Contacto', 'Para consultas sobre estos términos, utiliza los datos de contacto publicados en la política de tratamiento de datos.'],
]

export default function TermsPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { isAuthenticated, user, updateUser } = useAuth()
  const [version, setVersion] = useState('')
  const [accepted, setAccepted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ version: string }>('/user/terms').then((data) => setVersion(data.version))
      .catch(() => setError('No fue posible cargar la versión de los términos.'))
  }, [])

  const needsAcceptance = isAuthenticated && !!user && !!version &&
    (!user.terms_accepted_at || user.terms_version !== version)
  const requested = params.get('redirect') || '/checkout'
  const redirect = requested.startsWith('/') && !requested.startsWith('//') ? requested : '/checkout'

  const handleAccept = async () => {
    if (!accepted || !version || !user || submitting) {
      setError('Debes leer y aceptar los términos y la política de datos.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const result = await api.post<{ terms_version: string; terms_accepted_at: string }>('/user/terms/accept', {
        terms_accepted: true, terms_version: version,
      })
      updateUser({ ...user, terms_version: result.terms_version, terms_accepted_at: result.terms_accepted_at, current_terms_version: version })
      navigate(redirect, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No fue posible guardar tu aceptación.')
    } finally {
      setSubmitting(false)
    }
  }

  return <div className="min-h-screen overflow-x-hidden bg-slate-50">
    <header className="bg-[#001575] px-4 py-12 text-white sm:py-16">
      <div className="mx-auto max-w-4xl">
        <Link to={isAuthenticated ? '/' : '/login?mode=register'} className="mb-7 inline-flex items-center gap-2 text-sm text-white/85 hover:text-white"><ArrowLeft className="h-4 w-4" />Volver</Link>
        <div className="flex items-start gap-4"><FileText className="h-10 w-10 shrink-0 text-[#F58634]" /><div>
          <h1 className="text-3xl font-bold leading-tight sm:text-4xl">Términos y Condiciones</h1>
          <p className="mt-3 text-blue-100">Versión {version || 'cargando…'} · Borrador pendiente de revisión y aprobación por ImporGas JJ.</p>
        </div></div>
      </div>
    </header>
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="space-y-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <p className="leading-7 text-slate-700">Este texto es un borrador informativo. La empresa debe revisar y aprobar su contenido antes de publicarlo como versión definitiva. La <Link to="/politica-tratamiento-datos" className="font-semibold text-[#001575] underline">Política de Tratamiento de Datos</Link> existente contiene información adicional.</p>
        {sections.map(([title, body]) => <section key={title}><h2 className="mb-2 text-xl font-bold text-[#001575]">{title}</h2><p className="break-words leading-7 text-slate-700">{body}</p></section>)}
        {needsAcceptance && <div className="border-t border-slate-200 pt-7">
          <label className="flex cursor-pointer items-start gap-3 text-slate-800">
            <input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-[#001575]" />
            <span>He leído y acepto estos Términos y Condiciones y la Política de Tratamiento de Datos.</span>
          </label>
          {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
          <button type="button" onClick={handleAccept} disabled={!accepted || submitting} className="mt-5 w-full rounded-xl bg-[#001575] px-6 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">{submitting ? 'Guardando…' : 'Aceptar y continuar'}</button>
        </div>}
        {error && !needsAcceptance && <p role="alert" className="text-sm text-red-700">{error}</p>}
      </div>
    </main>
  </div>
}
