import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { User, LoginCredentials, RegisterData, AuthState } from '@/admin/types'
import { authService } from '@/admin/services/admin_index'
import { refreshAdminToken, tokenExpiresIn } from '@/admin/services/admin_token'
import { revokeBrowserSession, isSameBrowserSession } from '../../services/sessionSecurity'
import { useQueryClient } from '@tanstack/react-query'

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient()
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  })

  useEffect(() => {
    let active = true
    const reset = () => {
      authService.clearAuth()
      void cache.cancelQueries()
      cache.clear()
      if (active) setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
    }
    const validate = async () => {
      let token = authService.getStoredToken()
      if (!token) { reset(); return }
      try {
        if (tokenExpiresIn(token) <= 60_000) token = await refreshAdminToken()
        if (!token) { reset(); return }
        const user = await authService.getProfile()
        if (!active || !isSameBrowserSession(token, authService.getStoredToken())) return
        token = authService.getStoredToken()
        if (!token) { reset(); return }
        if (!user.is_active || user.role !== 'admin') { reset(); return }
        authService.setAuth(user, token)
        setState({ user, token, isAuthenticated: true, isLoading: false })
      } catch { if (active && (!authService.getStoredToken() || (token && isSameBrowserSession(token, authService.getStoredToken())))) reset() }
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key === 'token' || event.key === null) {
        setState(previous => ({ ...previous, isLoading: true }))
        void validate()
      }
    }
    void validate()
    window.addEventListener('admin:logout', reset)
    window.addEventListener('storage', onStorage)
    return () => {
      active = false
      window.removeEventListener('admin:logout', reset)
      window.removeEventListener('storage', onStorage)
    }
  }, [cache])

  useEffect(() => {
    if (!state.token) return
    let timer: ReturnType<typeof setTimeout>
    let stopped = false
    let checking = false
    const check = async () => {
      if (stopped || checking) return
      checking = true
      try {
      clearTimeout(timer)
      const current = authService.getStoredToken()
      if (current && tokenExpiresIn(current) > 60_000) {
        try { await authService.getProfile() } catch { revokeBrowserSession({ key: 'token', value: current }); return }
        if (stopped) return
        timer = setTimeout(check, Math.min(tokenExpiresIn(current) - 60_000, 15_000))
        return
      }
      if (await refreshAdminToken()) return
      if (!stopped && current) revokeBrowserSession({ key: 'token', value: current })
      } finally { checking = false }
    }
    const onRefreshed = (event: Event) => {
      setState(previous => ({ ...previous, token: (event as CustomEvent<string>).detail }))
    }
    void check()
    const onFocus = () => { void check() }
    window.addEventListener('focus', onFocus)
    window.addEventListener('admin:token-refreshed', onRefreshed)
    return () => {
      stopped = true
      clearTimeout(timer)
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('admin:token-refreshed', onRefreshed)
    }
  }, [state.token])

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
    localStorage.setItem('adminUser', JSON.stringify(user))
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
