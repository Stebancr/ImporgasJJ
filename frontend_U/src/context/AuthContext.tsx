import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { authService } from '../services/auth'
import type { User } from '../types'

interface AuthState { user: User | null; isAuthenticated: boolean; isLoading: boolean; token: string | null }
interface AuthContextType extends AuthState {
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, isAuthenticated: false, isLoading: true, token: null })

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    let active = true
    if (token) {
      authService.getCurrentUser().then(user => {
        if (active) setState({ user, isAuthenticated: true, isLoading: false, token: localStorage.getItem('authToken') })
      }).catch(() => {
        if (active) { authService.logout(); setState({ user: null, isAuthenticated: false, isLoading: false, token: null }) }
      })
    } else setState({ user: null, isAuthenticated: false, isLoading: false, token: null })
    const handleForceLogout = () => setState({ user: null, isAuthenticated: false, isLoading: false, token: null })
    window.addEventListener('auth:logout', handleForceLogout)
    return () => { active = false; window.removeEventListener('auth:logout', handleForceLogout) }
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    const { token, user } = await authService.login({ email: identifier, password })
    setState({ user, isAuthenticated: true, isLoading: false, token })
  }, [])
  const logout = useCallback(async () => {
    authService.logout()
    setState({ user: null, isAuthenticated: false, isLoading: false, token: null })
  }, [])
  const updateUser = useCallback((user: User) => {
    localStorage.setItem('user', JSON.stringify(user))
    setState((previous) => ({ ...previous, user }))
  }, [])

  return <AuthContext.Provider value={{ ...state, login, logout, updateUser }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
