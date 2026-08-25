import { create } from 'zustand'
import type { AuthUser } from '../types'
import { authApi } from '../api/visits'
import * as SecureStore from 'expo-secure-store'

const USER_KEY = 'intagas_user'

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (usuario: string, password: string) => Promise<void>
  logout: () => Promise<void>
  initializeAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  initializeAuth: async () => {
    try {
      const tokens = await authApi.getStoredTokens()
      if (!tokens) {
        set({ isLoading: false, isAuthenticated: false })
        return
      }
      // Try to get stored user data first (fast)
      const storedUser = await SecureStore.getItemAsync(USER_KEY)
      if (storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser)
          set({ user: parsedUser, isAuthenticated: true, isLoading: false })
        } catch (e) {
          // Invalid JSON in storage, clear and return
          await SecureStore.deleteItemAsync(USER_KEY)
          set({ isLoading: false, isAuthenticated: false })
          return
        }
      }
      // Then refresh profile in background
      try {
        const perfil = await authApi.refreshProfile()
        const user = await SecureStore.getItemAsync(USER_KEY)
        if (user) {
          const parsed: AuthUser = JSON.parse(user)
          const updated: AuthUser = {
            ...parsed,
            nombre_completo: perfil.nombre_completo,
            correo: perfil.correo,
            telefono: perfil.telefono,
          }
          await SecureStore.setItemAsync(USER_KEY, JSON.stringify(updated))
          set({ user: updated, isAuthenticated: true, isLoading: false })
        }
      } catch (profileError) {
        // If profile refresh fails, keep cached user but still authenticated
        console.warn('Profile refresh failed:', profileError)
      }
    } catch (error) {
      console.error('Auth initialization error:', error)
      // Clear all auth data on critical error
      await SecureStore.deleteItemAsync(USER_KEY)
      await authApi.logout()
      set({ isLoading: false, isAuthenticated: false, user: null })
    }
  },

  login: async (usuario, password) => {
    const { user } = await authApi.login(usuario, password)
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user))
    set({ user, isAuthenticated: true, isLoading: false })
  },

  logout: async () => {
    await authApi.logout()
    await SecureStore.deleteItemAsync(USER_KEY)
    set({ user: null, isAuthenticated: false })
  },
}))
