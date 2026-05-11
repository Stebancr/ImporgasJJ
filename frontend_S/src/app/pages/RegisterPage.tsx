import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authService, usersService } from '@/services'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Flame, Loader2 } from 'lucide-react'

interface SelectOption {
  id: number
  nombre: string
}

interface FormState {
  usuario: string
  password: string
  confirmPassword: string
  tipo_usuario: number
  cedula: string
  nombre_completo: string
  correo: string
  telefono: string
  sede: string
  cargo: string
  nivel: string
  regional: string
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [cargos, setCargos] = useState<SelectOption[]>([])
  const [niveles, setNiveles] = useState<SelectOption[]>([])
  const [regionales, setRegionales] = useState<SelectOption[]>([])
  const [formData, setFormData] = useState<FormState>({
    usuario: '',
    password: '',
    confirmPassword: '',
    tipo_usuario: 0,
    cedula: '',
    nombre_completo: '',
    correo: '',
    telefono: '',
    sede: '',
    cargo: '',
    nivel: '',
    regional: '',
  })

  useEffect(() => {
    usersService.getCargoNivelRegional().then((data) => {
      setCargos(data.cargos)
      setNiveles(data.niveles)
      setRegionales(data.regionales)
    }).catch(() => {
      // Options not critical — form still works without them
    })
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!formData.usuario.trim()) { setError('El nombre de usuario es requerido'); return }
    if (!formData.cedula.trim()) { setError('La cedula es requerida'); return }
    if (!formData.nombre_completo.trim()) { setError('El nombre completo es requerido'); return }
    if (formData.password.length < 8) { setError('La contrasena debe tener al menos 8 caracteres'); return }
    if (formData.password !== formData.confirmPassword) { setError('Las contrasenas no coinciden'); return }

    setIsLoading(true)
    try {
      await authService.publicRegister({
        usuario: formData.usuario.trim(),
        password: formData.password,
        tipo_usuario: formData.tipo_usuario,
        cedula: formData.cedula.trim(),
        nombre_completo: formData.nombre_completo.trim(),
        correo: formData.correo.trim() || null,
        telefono: formData.telefono.trim() || null,
        sede: formData.sede.trim() || null,
        cargo: formData.cargo ? parseInt(formData.cargo) : null,
        nivel: formData.nivel ? parseInt(formData.nivel) : null,
        regional: formData.regional ? parseInt(formData.regional) : null,
      })
      setSuccess('Usuario creado correctamente')
      setFormData({
        usuario: '', password: '', confirmPassword: '', tipo_usuario: 0,
        cedula: '', nombre_completo: '', correo: '', telefono: '', sede: '',
        cargo: '', nivel: '', regional: '',
      })
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { error?: string } } }
      setError(anyErr?.response?.data?.error ?? 'Error al crear el usuario')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-lg">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-primary rounded-lg">
              <Flame className="h-8 w-8 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold text-foreground">ImporgasJJ</span>
          </div>
          <p className="text-muted-foreground text-sm">Sistema de Administracion de Inventario</p>
        </div>

        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Registrar usuario</CardTitle>
            <CardDescription>Crea una cuenta para un nuevo colaborador</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{error}</div>
              )}
              {success && (
                <div className="p-3 text-sm text-green-700 bg-green-100 rounded-md">{success}</div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="usuario">Usuario *</Label>
                  <Input id="usuario" name="usuario" placeholder="nombre.usuario" value={formData.usuario} onChange={handleChange} required disabled={isLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cedula">Cedula *</Label>
                  <Input id="cedula" name="cedula" placeholder="12345678" value={formData.cedula} onChange={handleChange} required disabled={isLoading} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="nombre_completo">Nombre completo *</Label>
                <Input id="nombre_completo" name="nombre_completo" placeholder="Juan Perez" value={formData.nombre_completo} onChange={handleChange} required disabled={isLoading} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="correo">Correo electronico</Label>
                  <Input id="correo" name="correo" type="email" placeholder="juan@empresa.com" value={formData.correo} onChange={handleChange} disabled={isLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telefono">Telefono</Label>
                  <Input id="telefono" name="telefono" placeholder="+57 300 123 4567" value={formData.telefono} onChange={handleChange} disabled={isLoading} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="sede">Sede (opcional)</Label>
                <Input id="sede" name="sede" placeholder="Bogota" value={formData.sede} onChange={handleChange} disabled={isLoading} />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cargo">Cargo</Label>
                  <select id="cargo" name="cargo" value={formData.cargo} onChange={handleChange} disabled={isLoading} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50">
                    <option value="">Seleccionar</option>
                    {cargos.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nivel">Nivel</Label>
                  <select id="nivel" name="nivel" value={formData.nivel} onChange={handleChange} disabled={isLoading} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50">
                    <option value="">Seleccionar</option>
                    {niveles.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="regional">Regional</Label>
                  <select id="regional" name="regional" value={formData.regional} onChange={handleChange} disabled={isLoading} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50">
                    <option value="">Seleccionar</option>
                    {regionales.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="tipo_usuario">Tipo de usuario</Label>
                <select id="tipo_usuario" name="tipo_usuario" value={formData.tipo_usuario} onChange={handleChange} disabled={isLoading} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50">
                  <option value={0}>Colaborador (0)</option>
                  <option value={1}>Administrador (1)</option>
                  <option value={2}>Lectura Admin (2)</option>
                  <option value={3}>Usuario Especial (3)</option>
                  <option value={4}>Super Admin (4)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Contrasena *</Label>
                  <Input id="password" name="password" type="password" placeholder="••••••••" value={formData.password} onChange={handleChange} required disabled={isLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirmar contrasena *</Label>
                  <Input id="confirmPassword" name="confirmPassword" type="password" placeholder="••••••••" value={formData.confirmPassword} onChange={handleChange} required disabled={isLoading} />
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Registrando...</>
                ) : (
                  'Registrar usuario'
                )}
              </Button>
              <p className="text-sm text-muted-foreground text-center">
                <Link to="/dashboard" className="text-primary hover:underline font-medium">
                  Volver al panel
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}

