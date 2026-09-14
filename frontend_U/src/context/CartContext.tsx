import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { CartItem, Product } from '../types'

interface CartContextType {
  items: CartItem[]
  totalItems: number
  addToCart: (product: Product, quantity?: number) => void
  removeFromCart: (productId: string) => void
  updateQuantity: (productId: string, quantity: number) => void
  clearCart: () => void
}

const CartContext = createContext<CartContextType | undefined>(undefined)
const CART_STORAGE_KEY = 'imporgas-cart-v1'

function readStoredCart(): CartItem[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || '[]') as CartItem[]
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) =>
      item?.product?.id && Number.isInteger(item.quantity) && item.quantity >= 1 &&
      Number.isFinite(item.product.stock) && item.product.stock >= item.quantity
    )
  } catch {
    localStorage.removeItem(CART_STORAGE_KEY)
    return []
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(readStoredCart)

  useEffect(() => {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const addToCart = useCallback((product: Product, quantity = 1) => {
    const safeQuantity = Math.floor(Number(quantity))
    if (!product.isAvailable || product.stock < 1 || safeQuantity < 1) return
    setItems((prev) => {
      const existing = prev.find((item) => item.product.id === product.id)
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, product, quantity: Math.min(item.quantity + safeQuantity, product.stock) }
            : item
        )
      }
      return [...prev, { product, quantity: Math.min(safeQuantity, product.stock) }]
    })
  }, [])

  const removeFromCart = useCallback((productId: string) => {
    setItems((prev) => prev.filter((item) => item.product.id !== productId))
  }, [])

  const updateQuantity = useCallback((productId: string, quantity: number) => {
    const safeQuantity = Math.floor(Number(quantity))
    if (safeQuantity < 1) return
    setItems((prev) =>
      prev.map((item) =>
        item.product.id === productId
          ? { ...item, quantity: Math.max(1, Math.min(safeQuantity, item.product.stock)) }
          : item
      )
    )
  }, [])

  const clearCart = useCallback(() => setItems([]), [])

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <CartContext.Provider value={{ items, totalItems, addToCart, removeFromCart, updateQuantity, clearCart }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used within a CartProvider')
  return context
}
