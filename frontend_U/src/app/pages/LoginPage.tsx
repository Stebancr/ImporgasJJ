import './styles/LoginPage.css'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Flame, Eye, EyeOff, Mail, Lock, User, Phone, ArrowRight, Shield, Truck, Headphones, CreditCard } from 'lucide-react'
import { authService } from '../../services/auth'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'

type AuthMode = 'login' | 'register' | 'forgot'

function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const [mode, setMode] = useState<AuthMode>(searchParams.get('mode') === 'register' ? 'register' : 'login')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [termsVersion, setTermsVersion] = useState('')
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    cc: '',
    confirmPassword: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  useEffect(() => {
    api.get<{ version: string }>('/user/terms').then((data) => setTermsVersion(data.version))
      .catch(() => setError('No fue posible cargar los términos. Intenta actualizar la página.'))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isLoading) return
    setError('')
    setIsLoading(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
        const requested = searchParams.get('redirect') || '/'
        const redirect = requested.startsWith('/') && !requested.startsWith('//') ? requested : '/'
        navigate(redirect)
      } else if (mode === 'register') {
        if (!termsAccepted || !termsVersion) {
          setError('Debes leer y aceptar los Términos y Condiciones y la Política de Tratamiento de Datos.')
          return
        }
        if (form.password !== form.confirmPassword) {
          setError('Las contrasenas no coinciden')
          setIsLoading(false)
          return
        }
        await authService.register({
          name: form.name,
          email: form.email,
          password: form.password,
          cc: form.cc,
          phone: form.phone,
          termsVersion,
          termsAccepted,
        })
        await login(form.email, form.password)
        const requested = searchParams.get('redirect') || '/'
        const redirect = requested.startsWith('/') && !requested.startsWith('//') ? requested : '/'
        navigate(redirect)
      }
    } catch (err: unknown) {
      const fetchErr = err as { message?: string }
      setError(fetchErr.message || 'Error al procesar la solicitud')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-[#FAFBFC]">
      {/* Left Side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12">
        <div className="w-full max-w-md">
          {/* Logo */}
          <Link to="/" className="inline-flex items-center mb-10 group" aria-label="Ir al inicio de ImporGas JJ">
            <img src="/logo_imporgas.svg" alt="ImporGas JJ S.A.S" className="h-16 w-auto max-w-[12rem] object-contain" />
          </Link>

          {/* Title */}
          <div className="mb-8">
            <h1 className="text-3xl lg:text-4xl font-bold text-[#1A1D21] mb-3">
              {mode === 'login' && 'Bienvenido de vuelta'}
              {mode === 'register' && 'Crear cuenta'}
              {mode === 'forgot' && 'Recuperar contrasena'}
            </h1>
            <p className="text-[#6B7280] text-lg">
              {mode === 'login' && 'Ingresa tus credenciales para continuar'}
              {mode === 'register' && 'Completa tus datos para registrarte'}
              {mode === 'forgot' && 'Te enviaremos un enlace para restablecer tu contrasena'}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl">
                {error}
              </div>
            )}
            {mode === 'register' && (
              <div>
                <label htmlFor="customer-name" className="block text-sm font-medium text-[#4B5563] mb-2">
                  Nombre Completo
                </label>
                <div className="relative">
                  <input
                    id="customer-name"
                    type="text"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] focus:bg-white transition-all"
                    placeholder="Juan Perez"
                  />
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]">
                    <User className="w-5 h-5" />
                  </div>
                </div>
              </div>
            )}

            {mode === 'register' && (
              <div>
                <label htmlFor="customer-id" className="block text-sm font-medium text-[#4B5563] mb-2">
                  Numero de cedula
                </label>
                <div className="relative">
                  <input
                    id="customer-id"
                    type="text"
                    name="cc"
                    value={form.cc}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-all"
                    placeholder="12345678"
                  />
                  <CreditCard className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>
            )}

            <div>
              <label htmlFor="customer-email" className="block text-sm font-medium text-[#4B5563] mb-2">
                Correo Electronico
              </label>
              <div className="relative">
                <input
                  id="customer-email"
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  required
                  className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-all"
                  placeholder="tu@email.com"
                />
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label htmlFor="customer-phone" className="block text-sm font-medium text-[#4B5563] mb-2">
                  Telefono
                </label>
                <div className="relative">
                  <input
                    id="customer-phone"
                    type="tel"
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-all"
                    placeholder="+57 300 123 4567"
                  />
                  <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>
            )}

            {mode !== 'forgot' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="customer-password" className="block text-sm font-medium text-[#4B5563]">
                    Contrasena
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => setMode('forgot')}
                      className="text-sm text-[#001575] hover:text-[#00104f] font-medium"
                    >
                      Olvidaste tu contrasena?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    id="customer-password"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-12 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-all"
                    placeholder="********"
                  />
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#4B5563] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )}

            {mode === 'register' && (
              <div>
                <label htmlFor="customer-password-confirmation" className="block text-sm font-medium text-[#4B5563] mb-2">
                  Confirmar Contrasena
                </label>
                <div className="relative">
                  <input
                    id="customer-password-confirmation"
                    type={showPassword ? 'text' : 'password'}
                    name="confirmPassword"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#001575] transition-all"
                    placeholder="********"
                  />
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>
            )}

            {mode === 'register' && <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-[#E5E7EB] bg-white p-4 text-sm leading-6 text-[#374151]">
              <input type="checkbox" checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-[#001575]" />
              <span>He leído y acepto los <Link to="/terminos-y-condiciones" target="_blank" rel="noopener noreferrer" className="font-semibold text-[#001575] underline">Términos y Condiciones</Link> y la <Link to="/politica-tratamiento-datos" target="_blank" rel="noopener noreferrer" className="font-semibold text-[#001575] underline">Política de Tratamiento de Datos</Link>.</span>
            </label>}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#001575] to-[#00104f] text-white py-4 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#001575]/25 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' && 'Iniciar Sesion'}
                  {mode === 'register' && 'Crear Cuenta'}
                  {mode === 'forgot' && 'Enviar Enlace'}
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          {/* Mode Switcher */}
          <div className="mt-6 text-center">
            {mode === 'login' && (
              <p className="text-[#6B7280]">
                No tienes cuenta?{' '}
                <button
                  onClick={() => setMode('register')}
                  className="text-[#001575] font-semibold hover:text-[#00104f]"
                >
                  Registrate
                </button>
              </p>
            )}
            {mode === 'register' && (
              <p className="text-[#6B7280]">
                Ya tienes cuenta?{' '}
                <button
                  onClick={() => setMode('login')}
                  className="text-[#001575] font-semibold hover:text-[#00104f]"
                >
                  Inicia Sesion
                </button>
              </p>
            )}
            {mode === 'forgot' && (
              <button
                onClick={() => setMode('login')}
                className="text-[#001575] font-semibold hover:text-[#00104f]"
              >
                Volver al inicio de sesion
              </button>
            )}
          </div>

          {/* Divider */}
          {mode !== 'forgot' && (
            <>
              <div className="relative my-8">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#E5E7EB]" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-[#FAFBFC] text-[#6B7280]">O continua con</span>
                </div>
              </div>

              {/* Social Login */}
              <div className="grid grid-cols-2 gap-4">
                <button className="flex items-center justify-center gap-2 px-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl hover:border-[#001575] hover:bg-[#e8ecff] transition-all">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span className="font-medium text-[#4B5563]">Google</span>
                </button>
                <button className="flex items-center justify-center gap-2 px-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl hover:border-[#001575] hover:bg-[#e8ecff] transition-all">
                  <svg className="w-5 h-5 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                  </svg>
                  <span className="font-medium text-[#4B5563]">Facebook</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Right Side - Branding */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#001575] via-[#00104f] to-[#00104f]">
          <div className="absolute inset-0 opacity-10" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }} />
        </div>
        
        <div className="relative flex items-center justify-center p-12 w-full">
          <div className="max-w-lg text-white text-center">
            {/* Hero Image */}
            <div className="relative mb-10">
              <div className="absolute -inset-4 bg-white/10 rounded-3xl blur-2xl" />
              <div className="relative bg-white/10 backdrop-blur rounded-3xl p-8 border border-white/10">
                <div className="w-20 h-20 bg-gradient-to-br from-[#F58634] to-[#d4711e] rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-xl">
                  <Flame className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-4">Tu tienda de confianza</h2>
                <p className="text-white/80 text-lg leading-relaxed">
                  Encuentra los mejores calentadores, aires acondicionados, reguladores y herramientas con garantia y servicio de instalacion profesional.
                </p>
              </div>
            </div>

            {/* Features */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { icon: Shield, label: 'Garantia 5 anos' },
                { icon: Truck, label: 'Envio gratis' },
                { icon: Headphones, label: 'Soporte 24/7' },
              ].map((feature, idx) => (
                <div key={idx} className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/10">
                  <feature.icon className="w-6 h-6 mx-auto mb-2" />
                  <p className="text-sm text-white/80">{feature.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
