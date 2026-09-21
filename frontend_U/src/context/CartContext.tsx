import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import type { CartItem, Product } from '../types'
import api from '../services/api'
import productsService from '../services/products'
import { clearPendingCartIntent, readPendingCartIntent, savePendingCartIntent } from './pendingCartIntent'

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
// React StrictMode and the auth-provider remount can run the pending-intent
// effect more than once. Keep one process-wide promise so only one POST is sent.
let pendingCartCompletion: Promise<void> | null = null

function readStoredCart(userId: string | null): CartItem[] {
  if (!userId) return []
  try {
    const parsed = JSON.parse(localStorage.getItem(cartKey(userId)) || '[]') as CartItem[]
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) =>
      item?.product?.id && Number.isInteger(item.quantity) && item.quantity >= 1 &&
      item.product.isAvailable
    )
  } catch {
    localStorage.removeItem(cartKey(userId))
    return []
  }
}

function ActiveCartProvider({ children, userId }: { children: ReactNode; userId: string | null }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [items, setItems] = useState<CartItem[]>(() => readStoredCart(userId))
  const [showAuthPrompt, setShowAuthPrompt] = useState(false)
  const [pendingError, setPendingError] = useState('')
  const [addedNotice, setAddedNotice] = useState(false)
  const loaded = useRef(false)
  const ready = useRef<Promise<void>>(Promise.resolve())
  const processingPending = useRef(false)
  const authRedirectInProgress = useRef(false)

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
    const safeQuantity = Math.floor(Number(quantity))
    if (!product.isAvailable || safeQuantity < 1 || safeQuantity > 999) return false
    if (!userId) {
      if (!savePendingCartIntent(product.id, safeQuantity)) return false
      setShowAuthPrompt(true)
      return false
    }
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

  const completePendingCartIntent = useCallback(async () => {
    const intent = readPendingCartIntent()
    if (!userId || !intent) return
    if (pendingCartCompletion) return pendingCartCompletion
    if (processingPending.current) return
    processingPending.current = true
    setPendingError('')
    pendingCartCompletion = (async () => {
      await ready.current
      try {
        const product = await productsService.getById(String(intent.productId))
        if (!await addToCart(product, intent.quantity)) {
          setPendingError('No se pudo agregar el producto. Comprueba su disponibilidad e inténtalo de nuevo.')
          return
        }
        clearPendingCartIntent()
        setAddedNotice(true)
        navigate('/carrito', { replace: true })
      } catch (error) {
        setPendingError(error instanceof Error ? error.message : 'No se pudo recuperar el producto. Inténtalo de nuevo.')
      } finally {
        processingPending.current = false
        pendingCartCompletion = null
      }
    })()
    return pendingCartCompletion
  }, [addToCart, navigate, userId])

  useEffect(() => {
    if (userId && readPendingCartIntent()) void completePendingCartIntent()
  }, [userId, completePendingCartIntent])

  useEffect(() => {
    if (userId || showAuthPrompt) return
    if (location.pathname === '/login' || location.pathname === '/terminos-y-condiciones' ||
        location.pathname === '/politica-tratamiento-datos') {
      authRedirectInProgress.current = false
      return
    }
    if (authRedirectInProgress.current) return
    clearPendingCartIntent()
  }, [userId, showAuthPrompt, location.pathname])

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
    {pendingError && <div role="alert" className="fixed bottom-4 left-4 right-4 z-[100] mx-auto max-w-md rounded-xl border border-red-200 bg-white px-5 py-4 text-red-800 shadow-xl sm:left-auto sm:right-6">
      <p className="break-words">{pendingError}</p>
      <button type="button" onClick={() => void completePendingCartIntent()} className="mt-3 min-h-11 rounded-lg bg-[#001575] px-4 font-semibold text-white">Intentar de nuevo</button>
      <button type="button" onClick={() => { clearPendingCartIntent(); setPendingError('') }} className="ml-3 min-h-11 px-2 font-semibold">Cancelar</button>
    </div>}
    {showAuthPrompt && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-4" role="alertdialog" aria-modal="true" aria-labelledby="cart-auth-title">
      <div className="max-h-[calc(100dvh-2rem)] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <h2 id="cart-auth-title" className="text-xl font-bold text-[#001575]">Inicia sesión para comprar</h2>
        <p className="mt-3 text-slate-700">Para agregar productos al carrito debes iniciar sesión o crear una cuenta.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link onClick={() => { authRedirectInProgress.current = true; setShowAuthPrompt(false) }} to={`/login?redirect=${redirect}`} className="rounded-lg bg-[#001575] px-4 py-3 text-center font-semibold text-white">Iniciar sesión</Link>
          <Link onClick={() => { authRedirectInProgress.current = true; setShowAuthPrompt(false) }} to={`/login?mode=register&redirect=${redirect}`} className="rounded-lg border border-[#001575] px-4 py-3 text-center font-semibold text-[#001575]">Registrarse</Link>
          <button type="button" onClick={() => { clearPendingCartIntent(); setShowAuthPrompt(false) }} className="rounded-lg px-4 py-3 text-slate-600">Cancelar</button>
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
