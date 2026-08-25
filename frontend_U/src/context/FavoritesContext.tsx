import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import favoritesService, { Favorite } from '../services/favorites'
import { useAuth } from './AuthContext'

interface FavoritesContextType {
  favorites: Favorite[]
  loading: boolean
  addToFavorites: (productId: number) => Promise<void>
  removeFromFavorites: (favoriteId: number) => Promise<void>
  removeByProduct: (productId: number) => Promise<void>
  isFavorite: (productId: number) => boolean
  refresh: () => Promise<void>
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined)

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [loading, setLoading] = useState(false)

  const loadFavorites = async () => {
    if (!isAuthenticated) {
      setFavorites([])
      return
    }

    setLoading(true)
    try {
      const data = await favoritesService.getAll()
      setFavorites(data)
    } catch (error) {
      console.error('Error loading favorites:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFavorites()
  }, [isAuthenticated])

  const addToFavorites = async (productId: number) => {
    try {
      const newFavorite = await favoritesService.add(productId)
      setFavorites((prev) => [...prev, newFavorite])
    } catch (error) {
      console.error('Error adding to favorites:', error)
      throw error
    }
  }

  const removeFromFavorites = async (favoriteId: number) => {
    try {
      await favoritesService.remove(favoriteId)
      setFavorites((prev) => prev.filter((fav) => fav.id !== favoriteId))
    } catch (error) {
      console.error('Error removing from favorites:', error)
      throw error
    }
  }

  const removeByProduct = async (productId: number) => {
    try {
      await favoritesService.removeByProduct(productId)
      setFavorites((prev) => prev.filter((fav) => parseInt(fav.product.id) !== productId))
    } catch (error) {
      console.error('Error removing from favorites:', error)
      throw error
    }
  }

  const isFavorite = (productId: number): boolean => {
    return favorites.some((fav) => parseInt(fav.product.id) === productId)
  }

  const refresh = async () => {
    await loadFavorites()
  }

  return (
    <FavoritesContext.Provider
      value={{
        favorites,
        loading,
        addToFavorites,
        removeFromFavorites,
        removeByProduct,
        isFavorite,
        refresh,
      }}
    >
      {children}
    </FavoritesContext.Provider>
  )
}

export function useFavorites() {
  const context = useContext(FavoritesContext)
  if (!context) {
    throw new Error('useFavorites must be used within a FavoritesProvider')
  }
  return context
}
