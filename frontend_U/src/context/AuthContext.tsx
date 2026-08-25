import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { authService } from '../services/auth'

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  token: string | null
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    token: null,
  })

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    setState({ isAuthenticated: !!token, isLoading: false, token })

    const handleForceLogout = () => {
      setState({ isAuthenticated: false, isLoading: false, token: null })
    }
    window.addEventListener('auth:logout', handleForceLogout)
    return () => window.removeEventListener('auth:logout', handleForceLogout)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { token } = await authService.login({ email, password })
    setState({ isAuthenticated: true, isLoading: false, token })
  }, [])

  const logout = useCallback(() => {
    authService.logout()
    setState({ isAuthenticated: false, isLoading: false, token: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
