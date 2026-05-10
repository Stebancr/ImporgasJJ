import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { User, LoginCredentials, RegisterData, AuthState } from '@/types'
import { authService } from '@/services'

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  })

  useEffect(() => {
    const user = authService.getStoredUser()
    const token = authService.getStoredToken()

    if (user && token) {
      setState({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      })
    } else {
      setState((prev) => ({ ...prev, isLoading: false }))
    }
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    const { user, token } = await authService.login(credentials)
    authService.setAuth(user, token)
    setState({
      user,
      token,
      isAuthenticated: true,
      isLoading: false,
    })
  }, [])

  const register = useCallback(async (data: RegisterData) => {
    const { user, token } = await authService.register(data)
    authService.setAuth(user, token)
    setState({
      user,
      token,
      isAuthenticated: true,
      isLoading: false,
    })
  }, [])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } catch {
      // Ignore errors on logout
    }
    authService.clearAuth()
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    })
  }, [])

  const updateUser = useCallback((user: User) => {
    setState((prev) => ({ ...prev, user }))
    localStorage.setItem('user', JSON.stringify(user))
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
