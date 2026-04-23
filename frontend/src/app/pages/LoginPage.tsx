import './styles/LoginPage.css'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Flame, Eye, EyeOff, Mail, Lock, User, Phone, ArrowRight, Shield, Truck, Headphones } from 'lucide-react'

type AuthMode = 'login' | 'register' | 'forgot'

function LoginPage() {
  const [mode, setMode] = useState<AuthMode>('login')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    confirmPassword: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    await new Promise((resolve) => setTimeout(resolve, 1500))
    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex bg-[#FAFBFC]">
      {/* Left Side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-8 lg:p-12">
        <div className="w-full max-w-md">
          {/* Logo */}
          <Link to="/" className="inline-flex items-center gap-2.5 mb-10 group">
            <div className="w-11 h-11 bg-gradient-to-br from-[#FF6B35] to-[#E55A2B] rounded-xl flex items-center justify-center shadow-lg shadow-[#FF6B35]/25 group-hover:shadow-xl group-hover:shadow-[#FF6B35]/30 transition-all">
              <Flame className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-[#1A1D21]">GasStore</span>
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
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-[#4B5563] mb-2">
                  Nombre Completo
                </label>
                <div className="relative">
                  <input
                    type="text"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] focus:bg-white transition-all"
                    placeholder="Juan Perez"
                  />
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]">
                    <User className="w-5 h-5" />
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-[#4B5563] mb-2">
                Correo Electronico
              </label>
              <div className="relative">
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  required
                  className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] transition-all"
                  placeholder="tu@email.com"
                />
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-[#4B5563] mb-2">
                  Telefono
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] transition-all"
                    placeholder="+57 300 123 4567"
                  />
                  <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>
            )}

            {mode !== 'forgot' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-[#4B5563]">
                    Contrasena
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => setMode('forgot')}
                      className="text-sm text-[#0066FF] hover:text-[#0052CC] font-medium"
                    >
                      Olvidaste tu contrasena?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-12 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] transition-all"
                    placeholder="********"
                  />
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#4B5563] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )}

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-[#4B5563] mb-2">
                  Confirmar Contrasena
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="confirmPassword"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#0066FF] transition-all"
                    placeholder="********"
                  />
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#9CA3AF]" />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white py-4 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#0066FF]/25 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-0"
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
                  className="text-[#0066FF] font-semibold hover:text-[#0052CC]"
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
                  className="text-[#0066FF] font-semibold hover:text-[#0052CC]"
                >
                  Inicia Sesion
                </button>
              </p>
            )}
            {mode === 'forgot' && (
              <button
                onClick={() => setMode('login')}
                className="text-[#0066FF] font-semibold hover:text-[#0052CC]"
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
                <button className="flex items-center justify-center gap-2 px-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl hover:border-[#0066FF] hover:bg-[#E6F0FF] transition-all">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span className="font-medium text-[#4B5563]">Google</span>
                </button>
                <button className="flex items-center justify-center gap-2 px-4 py-3.5 bg-white border-2 border-[#E5E7EB] rounded-xl hover:border-[#0066FF] hover:bg-[#E6F0FF] transition-all">
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
        <div className="absolute inset-0 bg-gradient-to-br from-[#0066FF] via-[#0052CC] to-[#003D99]">
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
                <div className="w-20 h-20 bg-gradient-to-br from-[#FF6B35] to-[#E55A2B] rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-xl">
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
