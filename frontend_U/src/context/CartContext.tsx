import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import type { CartItem, Product } from '../types'
import api from '../services/api'
import productsService from '../services/products'

interface ServerCart { items: { product_id: number; quantity: number }[] }

interface CartContextType {
  items: CartItem[]
  totalItems: number
  addToCart: (product: Product, quantity?: number) => Promise<boolean>
  removeFromCart: (productId: string) => Promise<void>
  updateQuantity: (productId: string, quantity: number) => Promise<void>
  clearCart: () => Promise<void>
}

const CartContext = createContext<CartContextType | undefined>(undefined)
const LEGACY_CART_KEY = 'imporgas-cart-v1'
const cartKey = (userId: string) => `imporgas-cart-v2-user-${userId}`

function readStoredCart(userId: string | null): CartItem[] {
  if (!userId) return []
  try {
    const parsed = JSON.parse(localStorage.getItem(cartKey(userId)) || '[]') as CartItem[]
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) =>
      item?.product?.id && Number.isInteger(item.quantity) && item.quantity >= 1 &&
      Number.isFinite(item.product.stock) && item.product.stock >= item.quantity
    )
  } catch {
    localStorage.removeItem(cartKey(userId))
    return []
  }
}

function ActiveCartProvider({ children, userId }: { children: ReactNode; userId: string | null }) {
  const location = useLocation()
  const [items, setItems] = useState<CartItem[]>(() => readStoredCart(userId))
  const [showAuthPrompt, setShowAuthPrompt] = useState(false)
  const loaded = useRef(false)
  const ready = useRef<Promise<void>>(Promise.resolve())

  useEffect(() => {
    if (!userId || loaded.current) return
    loaded.current = true
    ready.current = (async () => {
      let cart = await api.get<ServerCart>('/cart')
      const saved = readStoredCart(userId)
      // Import an existing signed-in cart once, only when the server cart is empty.
      if (cart.items.length === 0 && saved.length > 0) {
        for (const item of saved) {
          try {
            cart = await api.post<ServerCart>('/cart', {
              product_id: Number(item.product.id), quantity: item.quantity,
            })
          } catch {
            // A stale product or stock level must not block the remaining items.
          }
        }
      }
      const mapped = await Promise.all(cart.items.map(async (item) => {
        const product = await productsService.getById(String(item.product_id))
        return { product, quantity: item.quantity }
      }))
      setItems(mapped)
    })().catch(() => { window.alert('No se pudo cargar el carrito. Intenta recargar la página.') })
  }, [userId])

  useEffect(() => {
    if (userId) localStorage.setItem(cartKey(userId), JSON.stringify(items))
  }, [items, userId])

  const addToCart = useCallback(async (product: Product, quantity = 1): Promise<boolean> => {
    if (!userId) {
      setShowAuthPrompt(true)
      return false
    }
    const safeQuantity = Math.floor(Number(quantity))
    if (!product.isAvailable || product.stock < 1 || safeQuantity < 1) return false
    await ready.current
    try {
      const cart = await api.post<ServerCart>('/cart', { product_id: Number(product.id), quantity: safeQuantity })
      const updated = cart.items.find((item) => item.product_id === Number(product.id))
      if (!updated) return false
      setItems((prev) => {
        const others = prev.filter((item) => item.product.id !== product.id)
        return [...others, { product, quantity: updated.quantity }]
      })
      return true
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'No se pudo agregar el producto.')
      return false
    }
  }, [userId])

  const removeFromCart = useCallback(async (productId: string) => {
    if (!userId) return
    await ready.current
    try {
      await api.delete(`/cart/${productId}`)
      setItems((prev) => prev.filter((item) => item.product.id !== productId))
    } catch (error) { window.alert(error instanceof Error ? error.message : 'No se pudo eliminar el producto.') }
  }, [userId])

  const updateQuantity = useCallback(async (productId: string, quantity: number) => {
    if (!userId) return
    const safeQuantity = Math.floor(Number(quantity))
    if (safeQuantity < 1) return
    await ready.current
    try {
      await api.patch<ServerCart>(`/cart/${productId}`, { quantity: safeQuantity })
      setItems((prev) => prev.map((item) => item.product.id === productId ? { ...item, quantity: safeQuantity } : item))
    } catch (error) { window.alert(error instanceof Error ? error.message : 'No se pudo cambiar la cantidad.') }
  }, [userId])

  const clearCart = useCallback(async () => {
    if (!userId) return
    await ready.current
    try {
      await api.delete('/cart')
      setItems([])
    } catch (error) { window.alert(error instanceof Error ? error.message : 'No se pudo limpiar el carrito.') }
  }, [userId])

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0)
  const redirect = encodeURIComponent(location.pathname + location.search)

  return <CartContext.Provider value={{ items, totalItems, addToCart, removeFromCart, updateQuantity, clearCart }}>
    {children}
    {showAuthPrompt && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-4" role="alertdialog" aria-modal="true" aria-labelledby="cart-auth-title">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 id="cart-auth-title" className="text-xl font-bold text-[#001575]">Inicia sesión para comprar</h2>
        <p className="mt-3 text-slate-700">Para agregar productos al carrito debes iniciar sesión o crear una cuenta.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link onClick={() => setShowAuthPrompt(false)} to={`/login?redirect=${redirect}`} className="rounded-lg bg-[#001575] px-4 py-3 text-center font-semibold text-white">Iniciar sesión</Link>
          <Link onClick={() => setShowAuthPrompt(false)} to={`/login?mode=register&redirect=${redirect}`} className="rounded-lg border border-[#001575] px-4 py-3 text-center font-semibold text-[#001575]">Registrarse</Link>
          <button type="button" onClick={() => setShowAuthPrompt(false)} className="rounded-lg px-4 py-3 text-slate-600">Cancelar</button>
        </div>
      </div>
    </div>}
  </CartContext.Provider>
}

export function CartProvider({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated, user } = useAuth()
  useEffect(() => {
    localStorage.removeItem(LEGACY_CART_KEY)
    sessionStorage.removeItem('pendingCartItem')
  }, [])
  const userId = !isLoading && isAuthenticated && user ? user.id : null
  return <ActiveCartProvider key={userId || 'guest'} userId={userId}>{children}</ActiveCartProvider>
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used within a CartProvider')
  return context
}
